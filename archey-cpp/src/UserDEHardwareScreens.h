#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QLineEdit>
#include <QButtonGroup>
#include <QRadioButton>
#include <QFrame>
#include <QScrollArea>
#include <QProcess>
#include <QRegularExpression>
#include "Theme.h"

// ── UserScreen ────────────────────────────────────────────────────────────────

class UserScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QString hostname, QString username, QString password);
    void back();

public:
    explicit UserScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("User Setup"); t->setObjectName("title");
        auto* s = new QLabel("Create your user account.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        auto addField = [&](const QString& label, QLineEdit*& field, bool pw = false) {
            auto* lbl = new QLabel(label); lbl->setObjectName("sec");
            root->addWidget(lbl);
            field = new QLineEdit();
            if (pw) field->setEchoMode(QLineEdit::Password);
            root->addWidget(field);
            connect(field, &QLineEdit::textChanged, this, &UserScreen::validate);
        };

        addField("HOSTNAME", m_hostname);
        m_hostname->setPlaceholderText("e.g. archlinux");
        addField("USERNAME", m_username);
        m_username->setPlaceholderText("e.g. alice");
        addField("PASSWORD", m_password, true);
        m_password->setPlaceholderText("Enter password");
        addField("CONFIRM PASSWORD", m_confirm, true);
        m_confirm->setPlaceholderText("Repeat password");

        m_validLbl = new QLabel(""); m_validLbl->setObjectName("hint");
        root->addWidget(m_validLbl);
        root->addStretch();

        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back"); backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        m_confirmBtn  = new QPushButton("Continue →"); m_confirmBtn->setObjectName("primary"); m_confirmBtn->setStyleSheet(Theme::primaryBtn());
        m_confirmBtn->setEnabled(false);
        connect(backBtn, &QPushButton::clicked, this, &UserScreen::back);
        connect(m_confirmBtn, &QPushButton::clicked, this, &UserScreen::onConfirm);
        btnRow->addWidget(backBtn); btnRow->addStretch(); btnRow->addWidget(m_confirmBtn);
        root->addLayout(btnRow);
    }

private slots:
    void validate() {
        QString h = m_hostname->text().trimmed();
        QString u = m_username->text().trimmed();
        QString p = m_password->text();
        QString c = m_confirm->text();
        QStringList errs;
        if (h.isEmpty()) errs << "Hostname required.";
        else if (h.contains(QRegularExpression("[^a-zA-Z0-9\\-]"))) errs << "Hostname: letters, digits, hyphens only.";
        if (u.isEmpty()) errs << "Username required.";
        else if (u.contains(QRegularExpression("[^a-z0-9_\\-]"))) errs << "Username: lowercase, digits, _ or - only.";
        if (p.length() < 6) errs << "Password must be at least 6 characters.";
        else if (p != c) errs << "Passwords do not match.";
        bool ok = errs.isEmpty();
        m_validLbl->setText(ok ? "" : errs.join("  "));
        m_validLbl->setObjectName(ok ? "ok" : "warn");
        m_validLbl->style()->unpolish(m_validLbl);
        m_validLbl->style()->polish(m_validLbl);
        m_confirmBtn->setEnabled(ok);
    }
    void onConfirm() {
        emit confirmed(m_hostname->text().trimmed(),
                       m_username->text().trimmed(),
                       m_password->text());
    }

private:
    QLineEdit   *m_hostname, *m_username, *m_password, *m_confirm;
    QLabel      *m_validLbl;
    QPushButton *m_confirmBtn;
};

// ── DEScreen ──────────────────────────────────────────────────────────────────

class DEScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QVariantMap de);
    void back();

public:
    // Struct at class scope — NOT inside any function
    struct DE { QString name, dm, desc; QStringList pkgs; };

    explicit DEScreen(QWidget* parent = nullptr) : QWidget(parent) {
        // Direct brace-init into member — no local variable involved
        m_des = {
            {"GNOME",      "gdm",     "Modern, full-featured. Best for beginners.", {"gnome","gnome-extra","gdm"}},
            {"KDE Plasma", "sddm",    "Highly customizable. Windows-like feel.",    {"plasma","kde-applications","sddm"}},
            {"XFCE",       "lightdm", "Lightweight, fast, traditional.",            {"xfce4","xfce4-goodies","lightdm","lightdm-gtk-greeter"}},
            {"Cinnamon",   "lightdm", "Elegant, familiar layout.",                  {"cinnamon","cinnamon-translations","lightdm","lightdm-gtk-greeter"}},
            {"MATE",       "lightdm", "Classic GNOME 2 style.",                     {"mate","mate-extra","lightdm","lightdm-gtk-greeter"}},
            {"i3",         "",        "Tiling window manager. Power users.",        {"i3-wm","i3status","i3lock","dmenu","xterm"}},
            {"None",       "",        "CLI only — install a DE manually later.",    {}},
        };

        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Desktop Environment"); t->setObjectName("title");
        auto* s = new QLabel("Choose your graphical environment.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        auto* scroll = new QScrollArea(); scroll->setWidgetResizable(true);
        auto* inner  = new QWidget();
        auto* iv     = new QVBoxLayout(inner); iv->setSpacing(8);
        scroll->setWidget(inner);
        scroll->setMaximumHeight(420);
        root->addWidget(scroll, 1);

        auto* group = new QButtonGroup(this);
        for (int i = 0; i < m_des.size(); ++i) {
            auto* card = new QFrame();
            card->setStyleSheet(QString("QFrame{background:%1;border:1px solid %2;border-radius:10px;padding:4px;}").arg(Theme::BG2, Theme::BORDER));
            auto* ch   = new QHBoxLayout(card); ch->setContentsMargins(12,10,12,10);
            auto* rb   = new QRadioButton(m_des[i].name);
            group->addButton(rb, i);
            if (i == 0) rb->setChecked(true);
            auto* desc = new QLabel(m_des[i].desc);
            desc->setObjectName("hint"); desc->setWordWrap(true);
            ch->addWidget(rb, 1); ch->addWidget(desc, 2);
            iv->addWidget(card);
        }
        iv->addStretch();

        connect(group, &QButtonGroup::idToggled, this, [this](int id, bool on){ if(on) m_selectedDe = id; });

        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back"); backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        auto* nextBtn = new QPushButton("Continue →"); nextBtn->setObjectName("primary"); nextBtn->setStyleSheet(Theme::primaryBtn());
        connect(backBtn, &QPushButton::clicked, this, &DEScreen::back);
        connect(nextBtn, &QPushButton::clicked, this, &DEScreen::onConfirm);
        btnRow->addWidget(backBtn); btnRow->addStretch(); btnRow->addWidget(nextBtn);
        root->addLayout(btnRow);
    }

private slots:
    void onConfirm() {
        QVariantMap de;
        if (m_selectedDe >= 0 && m_selectedDe < m_des.size()) {
            de["name"]     = m_des[m_selectedDe].name;
            de["dm"]       = m_des[m_selectedDe].dm;
            de["packages"] = m_des[m_selectedDe].pkgs;
        }
        emit confirmed(de);
    }

private:
    QList<DE> m_des;
    int       m_selectedDe = 0;
};

// ── HardwareScreen ────────────────────────────────────────────────────────────

class HardwareScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QStringList cpuPkgs, QStringList gpuPkgs);
    void back();

public:
    // Structs at class scope
    struct CPUOpt { QString label, id; QStringList pkgs; };
    struct GPUOpt { QString label;     QStringList pkgs; };

    explicit HardwareScreen(QWidget* parent = nullptr) : QWidget(parent) {
        // Direct brace-init into members
        m_cpuOpts = {
            {"Intel (intel-ucode)", "intel", {"intel-ucode"}},
            {"AMD (amd-ucode)",     "amd",   {"amd-ucode"}},
            {"None / VM",           "none",  {}},
        };
        m_gpuOpts = {
            {"NVIDIA (proprietary)",        {"nvidia","nvidia-utils","nvidia-settings","lib32-nvidia-utils"}},
            {"AMD (mesa + vulkan-radeon)",  {"xf86-video-amdgpu","mesa","vulkan-radeon","lib32-vulkan-radeon"}},
            {"Intel (mesa + vulkan-intel)", {"xf86-video-intel","mesa","vulkan-intel"}},
            {"Generic / VM (vesa + mesa)",  {"xf86-video-vesa","mesa"}},
        };

        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Hardware Drivers"); t->setObjectName("title");
        auto* s = new QLabel("Select drivers for your CPU and GPU. Auto-detected options are highlighted.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        // CPU
        auto* cpuLbl = new QLabel("CPU MICROCODE"); cpuLbl->setObjectName("sec");
        root->addWidget(cpuLbl);
        m_cpuDetectedLbl = new QLabel("Detecting...");
        m_cpuDetectedLbl->setObjectName("hint");
        root->addWidget(m_cpuDetectedLbl);

        auto* cpuGroup = new QButtonGroup(this);
        for (int i = 0; i < m_cpuOpts.size(); ++i) {
            auto* rb = new QRadioButton(m_cpuOpts[i].label);
            cpuGroup->addButton(rb, i);
            root->addWidget(rb);
        }
        connect(cpuGroup, &QButtonGroup::idToggled, this, [this](int id, bool on){ if(on) m_cpuSel=id; });

        // GPU
        auto* gpuLbl = new QLabel("GPU DRIVER"); gpuLbl->setObjectName("sec");
        root->addWidget(gpuLbl);
        m_gpuDetectedLbl = new QLabel("Detecting...");
        m_gpuDetectedLbl->setObjectName("hint");
        root->addWidget(m_gpuDetectedLbl);

        auto* gpuGroup = new QButtonGroup(this);
        for (int i = 0; i < m_gpuOpts.size(); ++i) {
            auto* rb = new QRadioButton(m_gpuOpts[i].label);
            gpuGroup->addButton(rb, i);
            root->addWidget(rb);
        }
        connect(gpuGroup, &QButtonGroup::idToggled, this, [this](int id, bool on){ if(on) m_gpuSel=id; });

        root->addStretch();

        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back"); backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        auto* nextBtn = new QPushButton("Continue →"); nextBtn->setObjectName("primary"); nextBtn->setStyleSheet(Theme::primaryBtn());
        connect(backBtn, &QPushButton::clicked, this, &HardwareScreen::back);
        connect(nextBtn, &QPushButton::clicked, this, [this](){
            emit confirmed(
                m_cpuSel >= 0 ? m_cpuOpts[m_cpuSel].pkgs : QStringList{},
                m_gpuSel >= 0 ? m_gpuOpts[m_gpuSel].pkgs : QStringList{}
            );
        });
        btnRow->addWidget(backBtn); btnRow->addStretch(); btnRow->addWidget(nextBtn);
        root->addLayout(btnRow);

        autoDetect(cpuGroup, gpuGroup);
    }

private:
    QList<CPUOpt> m_cpuOpts;
    QList<GPUOpt> m_gpuOpts;
    int           m_cpuSel = 2, m_gpuSel = 3;
    QLabel       *m_cpuDetectedLbl, *m_gpuDetectedLbl;

    void autoDetect(QButtonGroup* cpuGrp, QButtonGroup* gpuGrp) {
        QProcess cp;
        cp.start("sh", {"-c","grep -m1 'model name' /proc/cpuinfo"});
        cp.waitForFinished(2000);
        QString cpuInfo = cp.readAllStandardOutput().toLower();
        if (cpuInfo.contains("intel")) {
            cpuGrp->button(0)->setChecked(true); m_cpuSel = 0;
            m_cpuDetectedLbl->setText("✓ Intel CPU detected"); m_cpuDetectedLbl->setObjectName("info");
        } else if (cpuInfo.contains("amd")) {
            cpuGrp->button(1)->setChecked(true); m_cpuSel = 1;
            m_cpuDetectedLbl->setText("✓ AMD CPU detected"); m_cpuDetectedLbl->setObjectName("info");
        } else {
            cpuGrp->button(2)->setChecked(true);
            m_cpuDetectedLbl->setText("Could not auto-detect CPU");
        }

        QProcess gp;
        gp.start("sh", {"-c","lspci 2>/dev/null | grep -i 'vga\\|3d\\|display'"});
        gp.waitForFinished(3000);
        QString gpuInfo = gp.readAllStandardOutput().toLower();
        if (gpuInfo.contains("nvidia")) {
            gpuGrp->button(0)->setChecked(true); m_gpuSel = 0;
            m_gpuDetectedLbl->setText("✓ NVIDIA GPU detected"); m_gpuDetectedLbl->setObjectName("info");
        } else if (gpuInfo.contains("amd") || gpuInfo.contains("radeon")) {
            gpuGrp->button(1)->setChecked(true); m_gpuSel = 1;
            m_gpuDetectedLbl->setText("✓ AMD GPU detected"); m_gpuDetectedLbl->setObjectName("info");
        } else if (gpuInfo.contains("intel")) {
            gpuGrp->button(2)->setChecked(true); m_gpuSel = 2;
            m_gpuDetectedLbl->setText("✓ Intel GPU detected"); m_gpuDetectedLbl->setObjectName("info");
        } else {
            gpuGrp->button(3)->setChecked(true);
            m_gpuDetectedLbl->setText("Could not auto-detect GPU — defaulting to generic");
            m_gpuDetectedLbl->setObjectName("warn");
        }
    }
};
