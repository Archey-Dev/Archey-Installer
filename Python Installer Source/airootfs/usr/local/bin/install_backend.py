#!/usr/bin/env python3
"""
Install backend for ArchInstall.
Handles partitioning, formatting, pacstrap, and system config.
Runs entirely in a background thread, emits progress signals to the UI.
"""

import subprocess
import os
import sys
import time
from PyQt6.QtCore import QThread, pyqtSignal


# ── Packages ──────────────────────────────────────────────────────────────────

BASE_PACKAGES = [
    "base", "base-devel", "linux-firmware",
    "mkinitcpio", "networkmanager", "iwd",
    "sudo", "nano", "vim", "git", "curl", "wget",
    "grub", "efibootmgr", "os-prober",
    "bash-completion", "man-db", "man-pages",
]

KERNEL_PACKAGES = {
    "linux": ["linux", "linux-headers"],
    "linux-zen": ["linux-zen", "linux-zen-headers"],
    "linux-hardened": ["linux-hardened", "linux-hardened-headers"],
    "linux-lts": ["linux-lts", "linux-lts-headers"],
}

CPU_PACKAGES = {
    "intel": ["intel-ucode"],
    "amd":   ["amd-ucode"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

# Note: state.keymap added by installer.py
def detect_cpu() -> str:
    """Returns 'intel', 'amd', or 'unknown'."""
    try:
        with open("/proc/cpuinfo") as f:
            info = f.read().lower()
        if "intel" in info:
            return "intel"
        if "amd" in info:
            return "amd"
    except Exception:
        pass
    return "unknown"


def part_name(disk: str, num: int) -> str:
    """
    Returns partition path e.g. /dev/sda1 or /dev/nvme0n1p1.
    NVMe drives use 'p' before the partition number.
    """
    if "nvme" in disk or "mmcblk" in disk:
        return f"{disk}p{num}"
    return f"{disk}{num}"


# ── Install worker ────────────────────────────────────────────────────────────

class InstallWorker(QThread):
    # (step_message, percent_0_to_100)
    progress  = pyqtSignal(str, int)
    log_line  = pyqtSignal(str)
    succeeded = pyqtSignal()
    failed    = pyqtSignal(str)

    def __init__(self, state):
        super().__init__()
        self.state = state

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self):
        try:
            s = self.state
            disk_path = f"/dev/{s.disk['name']}"
            mode      = s.install_mode

            # ── Step 1: Partition the disk ─────────────────────────────────
            self._progress("Partitioning disk…", 5)
            efi_part, root_part = self._partition(disk_path, mode, s)

            # ── Step 2: Format ─────────────────────────────────────────────
            self._progress("Formatting partitions…", 15)
            self._format(efi_part, root_part, mode)

            # ── Step 3: Mount ──────────────────────────────────────────────
            self._progress("Mounting partitions…", 20)
            self._mount(efi_part, root_part)

            # ── Step 4: pacstrap ───────────────────────────────────────────
            self._progress("Installing base system (this may take a while)…", 25)
            self._pacstrap(s)

            # ── Step 5: fstab ──────────────────────────────────────────────
            self._progress("Generating fstab…", 60)
            self._genfstab()

            # ── Step 6: chroot config ──────────────────────────────────────
            self._progress("Configuring system…", 65)
            self._configure(s, efi_part, root_part)

            # ── Step 7: Bootloader ─────────────────────────────────────────
            self._progress("Installing bootloader…", 85)
            self._install_grub(s)

            # ── Step 8: Desktop environment ────────────────────────────────
            if s.de and s.de.get("packages"):
                self._progress(f"Installing {s.de['name']}…", 88)
                self._install_de(s)

            # ── Step 9: Cleanup ────────────────────────────────────────────
            self._progress("Cleaning up…", 97)
            self._cleanup()

            self._progress("Installation complete!", 100)
            self.succeeded.emit()

        except Exception as e:
            self.failed.emit(str(e))

    # ── Partitioning ──────────────────────────────────────────────────────────

    def _partition(self, disk_path: str, mode: str, s) -> tuple[str, str]:
        """
        Returns (efi_partition_path, root_partition_path).
        """

        if mode == "wipe":
            return self._partition_wipe(disk_path)

        elif mode == "freespace":
            return self._partition_freespace(disk_path, s)

        elif mode == "dualboot":
            return self._partition_dualboot(disk_path, s)

        else:
            raise ValueError(f"Unknown install mode: {mode}")

    def _partition_wipe(self, disk_path: str) -> tuple[str, str]:
        """Wipe disk and create fresh GPT layout: EFI + root."""
        self._log(f"Wiping {disk_path} and creating new GPT layout")

        # Wipe existing signatures
        self._run(["wipefs", "-a", disk_path])
        self._run(["sgdisk", "--zap-all", disk_path])

        # Create GPT, EFI partition (512MB), rest for root
        self._run([
            "sgdisk",
            "-n", "1:0:+512M", "-t", "1:ef00", "-c", "1:EFI",
            "-n", "2:0:0",     "-t", "2:8300", "-c", "2:root",
            disk_path
        ])

        time.sleep(1)  # let kernel re-read partition table
        self._run(["partprobe", disk_path])

        efi_part  = part_name(disk_path, 1)
        root_part = part_name(disk_path, 2)
        self._log(f"Created EFI: {efi_part}  Root: {root_part}")
        return efi_part, root_part

    def _partition_freespace(self, disk_path: str, s) -> tuple[str, str]:
        """Create a root partition in unallocated free space. Reuse existing EFI."""
        self._log("Creating root partition in free space")

        if not s.efi_partition:
            raise RuntimeError("No EFI partition found. Cannot install in free space mode without one.")

        efi_part = f"/dev/{s.efi_partition['name']}"

        # Use parted to find the free space and create a partition there
        # Get the end of the last partition in MB
        result = self._run_output([
            "parted", "-s", disk_path, "unit", "MB", "print", "free"
        ])
        # Find the last free space block
        free_start = None
        for line in result.splitlines():
            if "Free Space" in line:
                parts = line.split()
                free_start = parts[0]  # start of free space

        if not free_start:
            raise RuntimeError("Could not find free space on disk.")

        size_mb = int(s.arch_size_gb * 1024)
        end = f"{int(free_start.replace('MB','').strip()) + size_mb}MB"

        self._run([
            "parted", "-s", disk_path,
            "mkpart", "primary", "ext4",
            free_start, end
        ])

        time.sleep(1)
        self._run(["partprobe", disk_path])

        # Root partition is the last one
        result2 = self._run_output(["lsblk", "-ln", "-o", "NAME", disk_path])
        children = [l.strip() for l in result2.splitlines() if l.strip() and l.strip() != disk_path.replace("/dev/","")]
        root_part = f"/dev/{children[-1]}"

        self._log(f"Root partition: {root_part}  EFI: {efi_part}")
        return efi_part, root_part

    def _partition_dualboot(self, disk_path: str, s) -> tuple[str, str]:
        """Shrink the Windows NTFS partition and create a root partition in freed space."""
        if not s.efi_partition:
            raise RuntimeError("No EFI partition found for dualboot.")
        if not s.windows_partition:
            raise RuntimeError("No Windows partition found for dualboot.")

        efi_part = f"/dev/{s.efi_partition['name']}"
        win_part = f"/dev/{s.windows_partition['name']}"
        win_size_gb = s.windows_partition["size"] / 1024**3
        shrink_to_gb = win_size_gb - s.arch_size_gb

        if shrink_to_gb < 20:
            raise RuntimeError(
                f"Shrinking Windows to {shrink_to_gb:.1f} GB is too small. "
                "Please allocate less space for Arch."
            )

        self._log(f"Shrinking Windows partition {win_part} to {shrink_to_gb:.1f} GB")

        # ntfsresize to shrink the filesystem first
        shrink_bytes = int(shrink_to_gb * 1024**3)
        self._run([
            "ntfsresize", "--force", "--size",
            str(shrink_bytes), win_part
        ])

        # Then resize the actual partition with parted
        # Find which partition number the windows partition is
        win_num = ''.join(filter(str.isdigit, s.windows_partition["name"]))
        shrink_mb = int(shrink_to_gb * 1024)

        self._run([
            "parted", "-s", disk_path,
            "resizepart", win_num, f"{shrink_mb}MB"
        ])

        time.sleep(1)
        self._run(["partprobe", disk_path])

        # Create root partition in the now-free space
        self._run([
            "parted", "-s", disk_path,
            "mkpart", "primary", "ext4",
            f"{shrink_mb}MB", f"{shrink_mb + int(s.arch_size_gb * 1024)}MB"
        ])

        time.sleep(1)
        self._run(["partprobe", disk_path])

        # Root is the last partition
        result = self._run_output(["lsblk", "-ln", "-o", "NAME", disk_path])
        children = [l.strip() for l in result.splitlines() if l.strip() and l.strip() != disk_path.replace("/dev/","")]
        root_part = f"/dev/{children[-1]}"

        self._log(f"Dualboot partitions ready — EFI: {efi_part}  Root: {root_part}")
        return efi_part, root_part

    # ── Format ────────────────────────────────────────────────────────────────

    def _format(self, efi_part: str, root_part: str, mode: str):
        self._log(f"Formatting root {root_part} as ext4")
        self._run(["mkfs.ext4", "-F", root_part])

        # Only format EFI if we created it fresh (wipe mode)
        if mode == "wipe":
            self._log(f"Formatting EFI {efi_part} as FAT32")
            self._run(["mkfs.fat", "-F32", efi_part])
        else:
            self._log(f"Reusing existing EFI partition {efi_part} (not reformatting)")

    # ── Mount ─────────────────────────────────────────────────────────────────

    def _mount(self, efi_part: str, root_part: str):
        self._log("Mounting partitions")
        os.makedirs("/mnt", exist_ok=True)
        self._run(["mount", root_part, "/mnt"])
        os.makedirs("/mnt/boot/efi", exist_ok=True)
        self._run(["mount", efi_part, "/mnt/boot/efi"])

    # ── pacstrap ──────────────────────────────────────────────────────────────

    def _pacstrap(self, s):
        pkgs = BASE_PACKAGES.copy()

        # Selected kernel package set (fallback to regular linux)
        kernel_choice = getattr(s, "kernel_choice", "linux")
        pkgs += KERNEL_PACKAGES.get(kernel_choice, KERNEL_PACKAGES["linux"])

        # CPU and GPU packages from hardware screen selection
        pkgs += getattr(s, "cpu_packages", [])
        pkgs += getattr(s, "gpu_packages", [])

        # Add user-selected packages (search picks + advanced extras + system setup)
        de_pkgs   = set(s.de.get("packages", [])) if s.de else set()
        all_extra = (
            getattr(s, "user_packages",     []) +
            getattr(s, "advanced_packages", []) +
            getattr(s, "system_packages",   [])
        )
        seen_extra = set(pkgs)
        for p in all_extra:
            if p not in seen_extra and p not in de_pkgs:
                pkgs.append(p)
                seen_extra.add(p)
        self._log(f"Total packages: {len(pkgs)}")

        self._log(f"Running pacstrap with {len(pkgs)} packages")

        # Ensure live ISO pacman has multilib enabled (needed for lib32 packages)
        try:
            with open("/etc/pacman.conf") as f:
                conf = f.read()
            if "#[multilib]" in conf:
                conf = conf.replace("#[multilib]\n#Include", "[multilib]\nInclude")
                with open("/etc/pacman.conf", "w") as f:
                    f.write(conf)
                self._run(["pacman", "-Sy", "--noconfirm"])
                self._log("Multilib enabled on live ISO")
        except Exception as e:
            self._log(f"Warning: could not enable multilib: {e}")

        self._run(["pacstrap", "/mnt"] + pkgs)

    # ── fstab ─────────────────────────────────────────────────────────────────

    def _genfstab(self):
        self._log("Generating /etc/fstab")
        result = self._run_output(["genfstab", "-U", "/mnt"])
        fstab_path = "/mnt/etc/fstab"
        with open(fstab_path, "w") as f:
            f.write(result)
        self._log("fstab written")

    # ── chroot configuration ──────────────────────────────────────────────────

    def _configure(self, s, efi_part: str, root_part: str):
        """Write a setup script into the chroot and run it."""

        cpu = detect_cpu()
        ucode = f"{cpu}-ucode" if cpu in ("intel", "amd") else ""

        script = f"""#!/bin/bash
set -e

# Timezone
ln -sf /usr/share/zoneinfo/{s.timezone} /etc/localtime
hwclock --systohc

# Locale
echo "{s.locale} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG={s.locale}" > /etc/locale.conf

# Enable multilib repo (needed for lib32 packages like lib32-mesa, lib32-nvidia-utils)
sed -i '/^#\\[multilib\\]/{{N;s/#\\[multilib\\]\\n#Include/[multilib]\\nInclude/}}' /etc/pacman.conf || true

# Hostname
echo "{s.hostname}" > /etc/hostname
cat > /etc/hosts << 'EOF'
127.0.0.1   localhost
::1         localhost
127.0.1.1   {s.hostname}.localdomain {s.hostname}
EOF

# Keymap / vconsole (TTY)
echo "KEYMAP={s.keymap}" > /etc/vconsole.conf

# X11 keyboard config — localectl can't run in chroot, write the file directly
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/00-keyboard.conf << 'KBEOF'
Section "InputClass"
    Identifier "system-keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "{s.keymap}"
EndSection
KBEOF

# Initramfs — non-fatal, warnings are OK
mkinitcpio -P || echo "mkinitcpio finished with warnings, continuing"

# Root password (locked — user will use sudo)
passwd -l root

# Create user
useradd -m -G wheel,audio,video,storage,optical -s /bin/bash "{s.username}"
echo "{s.username}:{s.password}" | chpasswd

# Sudo for wheel group
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
chmod 440 /etc/sudoers.d/wheel

# Enable NetworkManager — critical for post-install networking
systemctl enable NetworkManager.service || echo "WARNING: NetworkManager enable failed"
systemctl enable systemd-resolved.service 2>/dev/null || true

# Enable iwd for wifi
systemctl enable iwd.service 2>/dev/null || true

# Enable user-chosen system services
for svc in {' '.join(getattr(s, 'system_services', []))}; do
    systemctl enable "$svc" 2>/dev/null || echo "Note: $svc not enabled"
done

# Display manager will be enabled after DE packages are installed
"""

        script_path = "/mnt/root/arch_setup.sh"
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)

        self._log("Running chroot configuration script")
        self._run(["arch-chroot", "/mnt", "/root/arch_setup.sh"])
        os.remove(script_path)

    # ── GRUB ──────────────────────────────────────────────────────────────────

    def _install_grub(self, s):
        import shutil
        self._log("Installing GRUB bootloader")

        # ── 1. Install grub-install to EFI ────────────────────────────────
        self._run([
            "arch-chroot", "/mnt",
            "grub-install",
            "--target=x86_64-efi",
            "--efi-directory=/boot/efi",
            "--bootloader-id=Archey",
            "--recheck",
            "--removable",   # writes fallback EFI path so firmware always finds it
        ])

        # ── 2. Copy theme files first (before grub-mkconfig!) ─────────────
        theme_src = "/usr/local/share/archey-grub"
        theme_dst = "/mnt/boot/grub/themes/archey"

        if os.path.isdir(theme_src):
            self._log("Copying Archey GRUB theme...")
            if os.path.exists(theme_dst):
                shutil.rmtree(theme_dst)
            os.makedirs(theme_dst, exist_ok=True)

            # Auto-detect nesting: if source only contains a single subdir
            # and no theme.txt, the real files are one level deeper
            src_items = os.listdir(theme_src)
            actual_src = theme_src
            if "theme.txt" not in src_items:
                subdirs = [i for i in src_items
                           if os.path.isdir(os.path.join(theme_src, i))]
                if len(subdirs) == 1:
                    actual_src = os.path.join(theme_src, subdirs[0])
                    self._log(f"Detected nested theme folder, using {actual_src}")

            # Copy contents of actual_src flat into theme_dst
            for item in os.listdir(actual_src):
                if item in ("install_theme.sh",):
                    continue   # skip stray scripts
                src_item = os.path.join(actual_src, item)
                dst_item = os.path.join(theme_dst, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)

            # ── 3. Install grub-mkfont if missing, then generate PF2 fonts ─
            # grub-mkfont lives in the 'grub' package which we already installed
            # Run font generation directly from the live ISO (not chroot)
            # since the fonts we need are on the ISO's filesystem
            self._log("Generating GRUB PF2 fonts...")

            # Find a monospace font available on the ISO
            fc = subprocess.run(
                ["fc-match", "DejaVu Sans Mono:style=Book", "--format=%{file}"],
                capture_output=True, text=True
            )
            fc_bold = subprocess.run(
                ["fc-match", "DejaVu Sans Mono:style=Bold", "--format=%{file}"],
                capture_output=True, text=True
            )
            freg  = fc.stdout.strip()
            fbold = fc_bold.stdout.strip()

            if not freg or not os.path.exists(freg):
                self._log("Warning: could not find font file, skipping PF2 generation")
            else:
                fonts = [
                    (11, freg,  "Archey 11",         "archey-11.pf2"),
                    (12, freg,  "Archey 12",         "archey-12.pf2"),
                    (13, freg,  "Archey 13",         "archey-13.pf2"),
                    (14, freg,  "Archey 14",         "archey-14.pf2"),
                    (16, freg,  "Archey Regular 16", "archey-reg-16.pf2"),
                    (16, fbold, "Archey Bold 16",    "archey-bold-16.pf2"),
                    (24, fbold, "Archey Bold 24",    "archey-bold-24.pf2"),
                ]
                for size, src, name, out in fonts:
                    if not src or not os.path.exists(src):
                        src = freg   # fall back to regular
                    out_path = os.path.join(theme_dst, out)
                    self._run([
                        "grub-mkfont", "-s", str(size),
                        "-n", name,
                        "-o", out_path,
                        src
                    ], check=False)
                self._log("Fonts generated")
        else:
            self._log(f"Warning: theme source not found at {theme_src} — using default GRUB theme")

        # ── 4. Configure /etc/default/grub with theme + gfx BEFORE mkconfig ─
        grub_cfg = "/mnt/etc/default/grub"

        # Read current config
        with open(grub_cfg) as f:
            cfg_text = f.read()

        # Strip any existing conflicting lines
        lines = [l for l in cfg_text.splitlines()
                 if not any(l.startswith(k) for k in (
                     "GRUB_THEME=", "GRUB_BACKGROUND=",
                     "GRUB_GFXMODE=", "GRUB_GFXPAYLOAD_LINUX=",
                     "GRUB_DISABLE_OS_PROBER=",
                 ))]

        lines += [
            "",
            'GRUB_THEME="/boot/grub/themes/archey/theme.txt"',
            'GRUB_GFXMODE="auto"',
            'GRUB_GFXPAYLOAD_LINUX="keep"',
            'GRUB_DISABLE_OS_PROBER=false',
        ]

        with open(grub_cfg, "w") as f:
            f.write("\n".join(lines) + "\n")
        self._log("GRUB config updated")

        # ── 5. os-prober for dualboot ──────────────────────────────────────
        if s.install_mode == "dualboot":
            self._run(["arch-chroot", "/mnt", "os-prober"], check=False)

        # ── 6. Generate final grub.cfg (theme is now set) ─────────────────
        self._run([
            "arch-chroot", "/mnt",
            "grub-mkconfig", "-o", "/boot/grub/grub.cfg"
        ])

        # ── 7. Prioritize Archey/Arch boot entry in UEFI boot order ───────
        self._prioritize_boot_entry()

        self._log("GRUB installed and configured with Archey theme")

    def _prioritize_boot_entry(self):
        """Move Archey/Arch EFI boot entry to the front of BootOrder (non-fatal)."""
        try:
            out = self._run_output(["arch-chroot", "/mnt", "efibootmgr"])
        except Exception as e:
            self._log(f"Warning: could not read EFI boot entries: {e}")
            return

        lines = out.splitlines()
        boot_order = None
        entries = {}

        for line in lines:
            line = line.strip()
            if line.startswith("BootOrder:"):
                boot_order = [x.strip().upper() for x in line.split(":", 1)[1].split(",") if x.strip()]
                continue

            if line.startswith("Boot") and "*" in line and len(line) >= 8:
                # Example: Boot0001* Archey
                boot_id = line[4:8].upper()
                label = line.split("*", 1)[1].strip().lower()
                entries[boot_id] = label

        if not boot_order:
            self._log("Warning: EFI BootOrder not found; skipping boot prioritization")
            return

        preferred = None
        for bid, label in entries.items():
            if "archey" in label or "arch linux" in label or "arch" == label:
                preferred = bid
                break

        if not preferred:
            self._log("Warning: no Archey/Arch EFI entry found to prioritize")
            return

        new_order = [preferred] + [b for b in boot_order if b != preferred]
        order_str = ",".join(new_order)

        res = self._run([
            "arch-chroot", "/mnt", "efibootmgr", "-o", order_str
        ], check=False)

        if res.returncode == 0:
            self._log(f"Set EFI BootOrder with {preferred} first: {order_str}")
        else:
            self._log("Warning: failed to update EFI BootOrder (continuing)")

    # ── Desktop environment ───────────────────────────────────────────────────

    def _install_de(self, s):
        de = s.de
        self._log(f"Installing {de['name']} packages: {de['packages']}")
        self._run([
            "arch-chroot", "/mnt",
            "pacman", "-S", "--noconfirm"
        ] + de["packages"])

        # Enable display manager now that packages are installed
        if de.get("dm"):
            self._log(f"Enabling display manager: {de['dm']}")
            result = self._run(
                ["arch-chroot", "/mnt", "systemctl", "enable", de["dm"]],
                check=False
            )
            if result.returncode != 0:
                self._log(f"Warning: could not enable {de['dm']} — may need to enable manually")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _cleanup(self):
        self._log("Unmounting partitions")
        self._run(["umount", "-R", "/mnt"], check=False)

    # ── Subprocess helpers ────────────────────────────────────────────────────

    def _run(self, cmd: list, check: bool = True):
        self._log(f"$ {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                self._log(line)
        if check and result.returncode != 0:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}):\n"
                f"  {' '.join(cmd)}\n"
                f"{result.stdout[-500:] if result.stdout else ''}"
            )
        return result

    def _run_output(self, cmd: list) -> str:
        self._log(f"$ {' '.join(cmd)}")
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n{result.stderr}"
            )
        return result.stdout

    def _log(self, msg: str):
        self.log_line.emit(msg)

    def _progress(self, msg: str, pct: int):
        self.progress.emit(msg, pct)
        self._log(f"[{pct}%] {msg}")
