#pragma once
#include <QMainWindow>
#include <QStackedWidget>
#include <QHBoxLayout>
#include <QThread>
#include <QProcess>
#include "Theme.h"
#include "InstallState.h"
#include "Sidebar.h"
#include "BookendScreens.h"
#include "WelcomeScreen.h"
#include "LocaleScreen.h"
#include "WifiScreen.h"
#include "DiskScreen.h"
#include "UserDEHardwareScreens.h"
#include "PackagesSystemScreens.h"
#include "InstallScreen.h"

// ── Net check ─────────────────────────────────────────────────────────────────

class NetCheckWorker : public QThread {
    Q_OBJECT
signals:
    void hasInternet(bool online);

public:
    explicit NetCheckWorker(QObject* parent = nullptr) : QThread(parent) {}

protected:
    void run() override {
        QProcess p;
        p.start("ping", {"-c","1","-W","2","8.8.8.8"});
        p.waitForFinished(5000);
        emit hasInternet(p.exitCode() == 0);
    }
};

// ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow : public QMainWindow {
    Q_OBJECT

    // Screen indices in the stacked widget
    enum Screen {
        SCR_UEFI     = 0,
        SCR_WELCOME  = 1,
        SCR_LOCALE   = 2,
        SCR_WIFI     = 3,
        SCR_DISK     = 4,
        SCR_USER     = 5,
        SCR_DE       = 6,
        SCR_HARDWARE = 7,
        SCR_PACKAGES = 8,
        SCR_SYSTEM   = 9,
        SCR_INSTALL  = 10,
        SCR_DONE     = 11,
    };

public:
    explicit MainWindow(QWidget* parent = nullptr) : QMainWindow(parent) {
        setWindowTitle("Archey");
        setStyleSheet(Theme::stylesheet());
        buildUI();

        // Check internet in background
        auto* net = new NetCheckWorker(this);
        connect(net, &NetCheckWorker::hasInternet, this, [this](bool ok){ m_alreadyOnline = ok; });
        connect(net, &NetCheckWorker::finished, net, &QObject::deleteLater);
        net->start();

        // Start at UEFI check or welcome
        if (QDir("/sys/firmware/efi").exists())
            goTo(SCR_WELCOME);
        else
            goTo(SCR_UEFI);
    }

private:
    void buildUI() {
        auto* central = new QWidget(this);
        setCentralWidget(central);
        auto* row = new QHBoxLayout(central);
        row->setContentsMargins(0,0,0,0);
        row->setSpacing(0);

        m_sidebar = new Sidebar();
        row->addWidget(m_sidebar);

        m_stack = new QStackedWidget();
        m_stack->setStyleSheet("background: transparent;");
        row->addWidget(m_stack, 1);

        // 0 — UEFI block
        auto* uefi = new UEFIBlockScreen();
        connect(uefi, &UEFIBlockScreen::proceed, this, [this](){ goTo(SCR_WELCOME); });
        m_stack->addWidget(uefi);                          // 0

        // 1 — Welcome
        auto* welcome = new WelcomeScreen();
        connect(welcome, &WelcomeScreen::proceed, this, [this](){ goTo(SCR_LOCALE); });
        m_stack->addWidget(welcome);                       // 1

        // 2 — Locale
        m_locale = new LocaleScreen();
        connect(m_locale, &LocaleScreen::confirmed, this, [this](QString lo, QString tz, QString kb){
            m_state.locale = lo; m_state.timezone = tz; m_state.keymap = kb;
            if (m_alreadyOnline) { presyncDb(); goTo(SCR_DISK); }
            else goTo(SCR_WIFI);
        });
        connect(m_locale, &LocaleScreen::back, this, [this](){ goTo(SCR_WELCOME); });
        m_stack->addWidget(m_locale);                      // 2

        // 3 — Wi-Fi
        m_wifi = new WifiScreen();
        connect(m_wifi, &WifiScreen::connected, this, [this](){ presyncDb(); goTo(SCR_DISK); });
        m_stack->addWidget(m_wifi);                        // 3

        // 4 — Disk
        m_disk = new DiskScreen();
        connect(m_disk, &DiskScreen::confirmed, this, [this](QVariantMap d, QVariantMap e, double gb, QString mode){
            m_state.disk = d; m_state.efiPartition = e;
            m_state.archSizeGb = gb; m_state.installMode = mode;
            goTo(SCR_USER);
        });
        connect(m_disk, &DiskScreen::back, this, [this](){ goTo(SCR_WIFI); });
        m_stack->addWidget(m_disk);                        // 4

        // 5 — User
        m_user = new UserScreen();
        connect(m_user, &UserScreen::confirmed, this, [this](QString h, QString u, QString p){
            m_state.hostname = h; m_state.username = u; m_state.password = p;
            goTo(SCR_DE);
        });
        connect(m_user, &UserScreen::back, this, [this](){ goTo(SCR_DISK); });
        m_stack->addWidget(m_user);                        // 5

        // 6 — Desktop
        m_de = new DEScreen();
        connect(m_de, &DEScreen::confirmed, this, [this](QVariantMap de){
            m_state.de = de; goTo(SCR_HARDWARE);
        });
        connect(m_de, &DEScreen::back, this, [this](){ goTo(SCR_USER); });
        m_stack->addWidget(m_de);                          // 6

        // 7 — Hardware
        m_hardware = new HardwareScreen();
        connect(m_hardware, &HardwareScreen::confirmed, this, [this](QStringList cpu, QStringList gpu){
            m_state.cpuPackages = cpu; m_state.gpuPackages = gpu; goTo(SCR_PACKAGES);
        });
        connect(m_hardware, &HardwareScreen::back, this, [this](){ goTo(SCR_DE); });
        m_stack->addWidget(m_hardware);                    // 7

        // 8 — Packages
        m_packages = new PackagesScreen();
        connect(m_packages, &PackagesScreen::confirmed, this, [this](QStringList pkgs){
            m_state.userPackages = pkgs; goTo(SCR_SYSTEM);
        });
        connect(m_packages, &PackagesScreen::back, this, [this](){ goTo(SCR_HARDWARE); });
        m_stack->addWidget(m_packages);                    // 8

        // 9 — System
        m_system = new SystemScreen();
        connect(m_system, &SystemScreen::confirmed, this, [this](QStringList pkgs, QStringList svcs){
            m_state.systemPackages = pkgs;
            m_state.systemServices = svcs;
            goTo(SCR_INSTALL);
            m_install->start(m_state);
        });
        connect(m_system, &SystemScreen::back, this, [this](){ goTo(SCR_PACKAGES); });
        m_stack->addWidget(m_system);                      // 9

        // 10 — Install
        m_install = new InstallScreen();
        connect(m_install, &InstallScreen::finished, this, [this](){ goTo(SCR_DONE); });
        m_stack->addWidget(m_install);                     // 10

        // 11 — Done
        m_stack->addWidget(new DoneScreen());              // 11
    }

    void goTo(int index) {
        m_stack->setCurrentIndex(index);
        m_sidebar->setStep(qMax(0, index - 1));
    }

    void presyncDb() {
        QProcess::startDetached("sh", {"-c",
            "pacman-key --init"
            " && pacman-key --populate archlinux"
            " && reflector --latest 20 --sort rate --save /etc/pacman.d/mirrorlist"
            " && pacman -Sy --noconfirm"
        });
    }

    InstallState    m_state;
    bool            m_alreadyOnline = false;
    Sidebar        *m_sidebar;
    QStackedWidget *m_stack;
    LocaleScreen   *m_locale;
    WifiScreen     *m_wifi;
    DiskScreen     *m_disk;
    UserScreen     *m_user;
    DEScreen       *m_de;
    HardwareScreen *m_hardware;
    PackagesScreen *m_packages;
    SystemScreen   *m_system;
    InstallScreen  *m_install;
};
