#pragma once
#include <QThread>
#include <QProcess>
#include <QFile>
#include <QDir>
#include <QStringList>
#include <QVariantMap>
#include <QRegularExpression>
#include <QSet>
#include <stdexcept>
#include "InstallState.h"

class InstallWorker : public QThread {
    Q_OBJECT
signals:
    void progress(QString msg, int pct);
    void logLine(QString line);
    void succeeded();
    void failed(QString msg);

public:
    explicit InstallWorker(const InstallState& state) : m_state(state) {}

    void run() override {
        try {
            QString disk = "/dev/" + m_state.disk["name"].toString();
            QString mode = m_state.installMode;

            _progress("Partitioning disk...", 5);
            auto [efi, root] = doPartition(disk, mode);

            _progress("Formatting partitions...", 15);
            doFormat(efi, root, mode);

            _progress("Mounting partitions...", 20);
            doMount(efi, root);

            _progress("Installing base system (this may take a while)...", 25);
            doPacstrap();

            _progress("Generating fstab...", 60);
            doFstab();

            _progress("Configuring system...", 65);
            doConfigure();

            _progress("Installing bootloader...", 85);
            doGrub();

            if (!m_state.de.isEmpty() && !m_state.de["packages"].toStringList().isEmpty()) {
                _progress("Installing desktop environment...", 88);
                doDE();
            }

            _progress("Cleaning up...", 97);
            doCleanup();

            _progress("Installation complete!", 100);
            emit succeeded();

        } catch (const std::exception& e) {
            emit failed(QString::fromUtf8(e.what()));
        } catch (...) {
            emit failed("Unknown error during installation.");
        }
    }

private:
    InstallState m_state;

    std::pair<QString,QString> doPartition(const QString& disk, const QString& mode) {
        if (mode == "wipe") return partitionWipe(disk);
        if (mode == "freespace") return partitionFreeSpace(disk);
        if (mode == "dualboot") return partitionDualBoot(disk);
        throw std::runtime_error("Unknown install mode: " + mode.toStdString());
    }

    std::pair<QString,QString> partitionWipe(const QString& disk) {
        _log("Wiping " + disk + " and creating fresh GPT");
        _run("wipefs", {"-a", disk});
        _run("sgdisk", {"--zap-all", disk});
        _run("sgdisk", {"-n","1:0:+512M","-t","1:ef00","-c","1:EFI",
            "-n","2:0:0",    "-t","2:8300","-c","2:root", disk});
        QThread::sleep(1);
        _run("partprobe", {disk});
        QString efi  = partName(disk, 1);
        QString root = partName(disk, 2);
        _log("Created EFI: " + efi + "  Root: " + root);
        return {efi, root};
    }

    std::pair<QString,QString> partitionFreeSpace(const QString& disk) {
        if (m_state.efiPartition.isEmpty())
            throw std::runtime_error("No EFI partition found for freespace mode.");

        QString efi = "/dev/" + m_state.efiPartition["name"].toString();
        _log("Creating root partition in free space (EFI: " + efi + ")");

        QProcess p;
        p.start("parted", {"-s", disk, "unit", "MB", "print", "free"});
        p.waitForFinished(10000);

        if (p.exitCode() != 0)
            throw std::runtime_error(("parted failed:\n" + QString(p.readAll())).toStdString());

        QString out = p.readAllStandardOutput();

        struct Region { double startMb; double endMb; double sizeMb; };
        QList<Region> freeRegions;

        QRegularExpression re(R"(^\s*([0-9.]+)MB\s+([0-9.]+)MB\s+([0-9.]+)MB\s+Free Space\s*$)");
        for (const QString& line : out.split('\n')) {
            auto m = re.match(line);
            if (!m.hasMatch()) continue;

            double startMb = m.captured(1).toDouble();
            double endMb   = m.captured(2).toDouble();
            double sizeMb  = m.captured(3).toDouble();
            freeRegions.append({startMb, endMb, sizeMb});
        }

        if (freeRegions.isEmpty())
            throw std::runtime_error("Could not find any free space on disk.");

        const double needMb = m_state.archSizeGb * 1024.0;
        Region best{-1, -1, -1};
        for (const auto& r : freeRegions) {
            if (r.sizeMb >= needMb && r.sizeMb > best.sizeMb) best = r;
        }

        if (best.sizeMb < 0) {
            throw std::runtime_error(
                QString("No free region large enough (need %1 MB).")
                    .arg(needMb, 0, 'f', 0)
                    .toStdString()
            );
        }

        int startMb = static_cast<int>(best.startMb);
        int endMb   = static_cast<int>(startMb + needMb);

        _log(QString("Using free region: %1MB -> %2MB (size %3MB)")
        .arg(best.startMb, 0, 'f', 1)
        .arg(best.endMb, 0, 'f', 1)
        .arg(best.sizeMb, 0, 'f', 1));

        _run("parted", {"-s", disk, "mkpart", "primary", "ext4",
            QString::number(startMb) + "MB",
             QString::number(endMb) + "MB"});
        QThread::sleep(1);
        _run("partprobe", {disk});

        QProcess lp;
        lp.start("lsblk", {"-ln","-o","NAME", disk});
        lp.waitForFinished(5000);
        QStringList lines = QString(lp.readAllStandardOutput()).split('\n', Qt::SkipEmptyParts);
        if (lines.isEmpty())
            throw std::runtime_error("Could not determine newly created root partition.");

        QString root = "/dev/" + lines.last().trimmed();
        return {efi, root};
    }

    std::pair<QString,QString> partitionDualBoot(const QString& disk) {
        if (m_state.efiPartition.isEmpty())
            throw std::runtime_error("No EFI partition found for dualboot.");
        if (m_state.windowsPartition.isEmpty())
            throw std::runtime_error("No Windows partition found for dualboot.");

        QString efi  = "/dev/" + m_state.efiPartition["name"].toString();
        QString win  = "/dev/" + m_state.windowsPartition["name"].toString();

        double winGb = m_state.windowsPartition["size"].toDouble() / (1024.0*1024*1024);
        double shrinkTo = winGb - m_state.archSizeGb;
        if (shrinkTo < 20)
            throw std::runtime_error(QString("Shrinking Windows to %1 GB is too small.")
            .arg(shrinkTo, 0, 'f', 1).toStdString());

        _log(QString("Shrinking Windows partition %1 to %2 GB")
        .arg(win).arg(shrinkTo, 0, 'f', 1));

        qint64 shrinkBytes = static_cast<qint64>(shrinkTo * 1024 * 1024 * 1024);
        _run("ntfsresize", {"--force","--size", QString::number(shrinkBytes), win});

        QString winNum = extractPartitionNumber(win);
        if (winNum.isEmpty())
            throw std::runtime_error(("Could not parse partition number from " + win).toStdString());

        _run("parted", {"-s", disk, "resizepart", winNum,
            QString::number(static_cast<int>(shrinkTo * 1024)) + "MB"});
        QThread::sleep(1);
        _run("partprobe", {disk});

        int shrinkMb = static_cast<int>(shrinkTo * 1024);
        int endMb    = shrinkMb + static_cast<int>(m_state.archSizeGb * 1024);

        _run("parted", {"-s", disk, "mkpart", "primary", "ext4",
            QString::number(shrinkMb) + "MB", QString::number(endMb) + "MB"});
        QThread::sleep(1);
        _run("partprobe", {disk});

        QProcess lp;
        lp.start("lsblk", {"-ln","-o","NAME",disk});
        lp.waitForFinished(5000);
        QStringList lines = QString(lp.readAllStandardOutput()).split('\n', Qt::SkipEmptyParts);
        if (lines.isEmpty())
            throw std::runtime_error("Could not determine newly created root partition.");

        return {efi, "/dev/" + lines.last().trimmed()};
    }

    void doFormat(const QString& efi, const QString& root, const QString& mode) {
        _log("Formatting root " + root + " as ext4");
        _run("mkfs.ext4", {"-F", root});
        if (mode == "wipe") {
            _log("Formatting EFI " + efi + " as FAT32");
            _run("mkfs.fat", {"-F32", efi});
        }
    }

    void doMount(const QString& efi, const QString& root) {
        QDir("/").mkpath("/mnt");
        _run("mount", {root, "/mnt"});
        QDir("/").mkpath("/mnt/boot/efi");
        _run("mount", {efi, "/mnt/boot/efi"});
    }

    void doPacstrap() {
        static const QStringList BASE = {
            "base","base-devel","linux","linux-firmware",
            "linux-headers","mkinitcpio","networkmanager","iwd",
            "sudo","nano","vim","git","curl","wget",
            "grub","efibootmgr","os-prober",
            "bash-completion","man-db","man-pages",
        };

        QStringList pkgs = BASE;
        pkgs += m_state.cpuPackages;
        pkgs += m_state.gpuPackages;

        QSet<QString> seen(pkgs.begin(), pkgs.end());
        QStringList dePkgs = m_state.de["packages"].toStringList();
        for (const QString& p : m_state.userPackages + m_state.systemPackages) {
            if (!seen.contains(p) && !dePkgs.contains(p)) {
                pkgs.append(p);
                seen.insert(p);
            }
        }

        enableMultilib();

        _log(QString("Running pacstrap with %1 packages").arg(pkgs.size()));
        QStringList args = {"/mnt"};
        args += pkgs;
        _run("pacstrap", args);
    }

    void enableMultilib() {
        QFile f("/etc/pacman.conf");
        if (!f.open(QIODevice::ReadOnly)) return;
        QString conf = f.readAll();
        f.close();

        if (!conf.contains("#[multilib]")) return;
        conf.replace("#[multilib]\n#Include", "[multilib]\nInclude");

        if (f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            f.write(conf.toUtf8());
            f.close();
        }
        _run("pacman", {"-Sy","--noconfirm"});
        _log("Multilib enabled on live ISO");
    }

    void doFstab() {
        QProcess p;
        p.start("genfstab", {"-U", "/mnt"});
        p.waitForFinished(10000);

        if (p.exitCode() != 0)
            throw std::runtime_error(("genfstab failed:\n" + QString(p.readAll())).toStdString());

        QString fstab = QString::fromUtf8(p.readAllStandardOutput()).trimmed();
        if (fstab.isEmpty())
            throw std::runtime_error("genfstab produced empty output.");

        QFile f("/mnt/etc/fstab");
        if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate))
            throw std::runtime_error("Could not open /mnt/etc/fstab for writing.");

        f.write((fstab + "\n").toUtf8());
        f.close();

        _log("fstab generated");
    }

    void doConfigure() {
        QString svcs = m_state.systemServices.join(' ');
        QString script = QString(R"(#!/bin/bash
set -e
ln -sf /usr/share/zoneinfo/%1 /etc/localtime
hwclock --systohc
echo "%2 UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=%2" > /etc/locale.conf
sed -i '/^#\[multilib\]/{N;s/#\[multilib\]\n#Include/[multilib]\nInclude/}' /etc/pacman.conf || true
echo "%3" > /etc/hostname
cat > /etc/hosts << 'EOF'
127.0.0.1   localhost
::1         localhost
127.0.1.1   %3.localdomain %3
EOF
echo "KEYMAP=%4" > /etc/vconsole.conf
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/00-keyboard.conf << 'KBEOF'
Section "InputClass"
    Identifier "system-keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "%4"
EndSection
KBEOF
mkinitcpio -P || echo "mkinitcpio finished with warnings"
passwd -l root
useradd -m -G wheel,audio,video,storage,optical -s /bin/bash "%5"
echo "%5:%6" | chpasswd
echo "%%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
chmod 440 /etc/sudoers.d/wheel
systemctl enable NetworkManager.service || echo "WARNING: NM enable failed"
systemctl enable systemd-resolved.service 2>/dev/null || true
systemctl enable iwd.service 2>/dev/null || true
for svc in %7; do
    systemctl enable "$svc" 2>/dev/null || echo "Note: $svc not enabled"
    done
        )")
        .arg(m_state.timezone)
        .arg(m_state.locale)
        .arg(m_state.hostname)
        .arg(m_state.keymap)
        .arg(m_state.username)
        .arg(m_state.password)
        .arg(svcs);

        QString scriptPath = "/mnt/root/arch_setup.sh";
        QFile sf(scriptPath);
        if (sf.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            sf.write(script.toUtf8());
            sf.setPermissions(QFile::ReadOwner|QFile::WriteOwner|QFile::ExeOwner);
            sf.close();
        } else {
            throw std::runtime_error("Failed to write chroot setup script.");
        }

        _log("Running chroot configuration script");
        _run("arch-chroot", {"/mnt", "/root/arch_setup.sh"});
        QFile::remove(scriptPath);
    }

    void doGrub() {
        _run("arch-chroot", {"/mnt","grub-install",
            "--target=x86_64-efi",
            "--efi-directory=/boot/efi",
            "--bootloader-id=Archey",
            "--recheck",
            "--removable"});

        QString themeSrc = "/usr/local/share/archey-grub";
        QString themeDst = "/mnt/boot/grub/themes/archey";
        if (QDir(themeSrc).exists()) {
            _log("Copying Archey GRUB theme...");
            QDir().mkpath(themeDst);
            copyDir(themeSrc, themeDst);
        }

        QFile grubCfg("/mnt/etc/default/grub");
        if (grubCfg.open(QIODevice::ReadOnly)) {
            QString cfg = grubCfg.readAll();
            grubCfg.close();

            QStringList lines;
            for (const QString& l : cfg.split('\n')) {
                if (!l.startsWith("GRUB_THEME=") &&
                    !l.startsWith("GRUB_GFXMODE=") &&
                    !l.startsWith("GRUB_GFXPAYLOAD_LINUX=") &&
                    !l.startsWith("GRUB_DISABLE_OS_PROBER=")) {
                    lines.append(l);
                    }
            }

            lines << ""
            << "GRUB_THEME=\"/boot/grub/themes/archey/theme.txt\""
            << "GRUB_GFXMODE=\"auto\""
            << "GRUB_GFXPAYLOAD_LINUX=\"keep\""
            << "GRUB_DISABLE_OS_PROBER=false";

            if (grubCfg.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
                grubCfg.write(lines.join('\n').toUtf8());
                grubCfg.close();
            }
        }

        if (m_state.installMode == "dualboot")
            _run("arch-chroot", {"/mnt","os-prober"}, false);

        _run("arch-chroot", {"/mnt","grub-mkconfig","-o","/boot/grub/grub.cfg"});
        _log("GRUB installed");
    }

    void doDE() {
        QStringList pkgs = m_state.de["packages"].toStringList();
        _log("Installing " + m_state.de["name"].toString());

        QStringList args = {"/mnt","pacman","-S","--noconfirm"};
        args += pkgs;
        _run("arch-chroot", args);

        QString dm = m_state.de["dm"].toString();
        if (!dm.isEmpty())
            _run("arch-chroot", {"/mnt","systemctl","enable", dm}, false);
    }

    void doCleanup() {
        _run("sync", {}, false);
        _run("umount", {"-R","/mnt"}, false);
    }

    static QString partName(const QString& disk, int num) {
        if (disk.contains("nvme") || disk.contains("mmcblk"))
            return disk + "p" + QString::number(num);
        return disk + QString::number(num);
    }

    static QString extractPartitionNumber(const QString& devPath) {
        auto m1 = QRegularExpression(R"(p(\d+)$)").match(devPath);
        if (m1.hasMatch()) return m1.captured(1);

        auto m2 = QRegularExpression(R"((\d+)$)").match(devPath);
        if (m2.hasMatch()) return m2.captured(1);

        return {};
    }

    void _run(const QString& prog, const QStringList& args, bool check = true) {
        QString cmd = prog + " " + args.join(' ');
        _log("$ " + cmd);

        QProcess p;
        p.setProcessChannelMode(QProcess::MergedChannels);
        p.start(prog, args);
        p.waitForFinished(-1);

        QString out = p.readAll();
        for (const QString& line : out.split('\n')) {
            if (!line.trimmed().isEmpty()) _log(line.trimmed());
        }

        if (check && (p.exitStatus() != QProcess::NormalExit || p.exitCode() != 0)) {
            throw std::runtime_error(QString("Command failed (exit %1):\n  %2\n%3")
                .arg(p.exitCode())
                .arg(cmd)
                .arg(out.right(700))
                .toStdString());
        }
    }

    void _log(const QString& msg) { emit logLine(msg); }

    void _progress(const QString& msg, int pct) {
        emit progress(msg, pct);
        _log(QString("[%1%] %2").arg(pct).arg(msg));
    }

    void copyDir(const QString& src, const QString& dst) {
        QDir srcDir(src);
        for (const QString& f : srcDir.entryList(QDir::Files))
            QFile::copy(src + "/" + f, dst + "/" + f);

        for (const QString& d : srcDir.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
            QDir().mkpath(dst + "/" + d);
            copyDir(src + "/" + d, dst + "/" + d);
        }
    }
};
