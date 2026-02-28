#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QListWidget>
#include <QLineEdit>
#include <QProgressBar>
#include <QThread>
#include <QProcess>
#include <QFile>
#include <QSplitter>
#include <QFrame>
#include <QCheckBox>
#include <QScrollArea>
#include <QButtonGroup>
#include <QRadioButton>
#include "Theme.h"

// ── SyncWorker ────────────────────────────────────────────────────────────────

class SyncWorker : public QThread {
    Q_OBJECT
signals:
    void done();
    void error(QString msg);
    void status(QString msg);

protected:
    void run() override {
        emit status("Checking mirrorlist...");
        QFile ml("/etc/pacman.d/mirrorlist");
        bool hasServers = false;
        if (ml.open(QIODevice::ReadOnly)) {
            for (const QByteArray& line : ml.readAll().split('\n'))
                if (line.trimmed().startsWith("Server")) { hasServers = true; break; }
            ml.close();
        }
        if (!hasServers) {
            if (ml.open(QIODevice::WriteOnly)) {
                ml.write("Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch\n"
                         "Server = https://mirror.rackspace.com/archlinux/$repo/os/$arch\n"
                         "Server = https://mirrors.kernel.org/archlinux/$repo/os/$arch\n"
                         "Server = https://mirrors.mit.edu/archlinux/$repo/os/$arch\n");
                ml.close();
            }
        }

        emit status("Finding fastest mirrors...");
        QProcess reflector;
        reflector.start("reflector", {"--latest","10","--sort","rate",
                                       "--connection-timeout","3","--download-timeout","3",
                                       "--save","/etc/pacman.d/mirrorlist"});
        reflector.waitForFinished(45000);

        emit status("Checking keyring...");
        QProcess kl;
        kl.start("pacman-key", {"--list-keys"});
        kl.waitForFinished(10000);
        if (kl.exitCode() != 0) {
            emit status("Initialising keyring (this may take a minute)...");
            QProcess ki; ki.start("pacman-key", {"--init"});          ki.waitForFinished(120000);
            QProcess kp; kp.start("pacman-key", {"--populate","archlinux"}); kp.waitForFinished(120000);
        }

        emit status("Syncing package databases...");
        QProcess sy;
        sy.start("pacman", {"-Sy","--noconfirm"});
        sy.waitForFinished(180000);
        if (sy.exitCode() == 0)
            emit done();
        else
            emit error(sy.readAllStandardOutput() + sy.readAllStandardError());
    }
};

// ── SearchWorker ──────────────────────────────────────────────────────────────

class SearchWorker : public QThread {
    Q_OBJECT
signals:
    void results(QStringList pkgs);

public:
    explicit SearchWorker(const QString& q, QObject* parent = nullptr)
        : QThread(parent), m_query(q) {}

protected:
    void run() override {
        QProcess p;
        p.start("pacman", {"-Ss", m_query});
        p.waitForFinished(30000);
        QString out = p.readAllStandardOutput();
        QStringList pkgs;
        for (const QString& line : out.split('\n')) {
            if (line.startsWith("  ")) continue;
            QString trimmed = line.trimmed();
            if (trimmed.isEmpty()) continue;
            QStringList parts = trimmed.split('/');
            if (parts.size() >= 2) {
                QString name = parts[1].split(' ').first();
                if (!name.isEmpty()) pkgs.append(name);
            }
        }
        emit results(pkgs);
    }

private:
    QString m_query;
};

// ── PackagesScreen ────────────────────────────────────────────────────────────

class PackagesScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QStringList packages);
    void back();

public:
    explicit PackagesScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Packages"); t->setObjectName("title");
        auto* s = new QLabel("Search and select additional packages to install.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        m_statusLbl = new QLabel("Syncing package database...");
        m_statusLbl->setObjectName("warn");
        root->addWidget(m_statusLbl);

        m_searchEdit = new QLineEdit();
        m_searchEdit->setPlaceholderText("Search packages (e.g. firefox) — double-click to add");
        m_searchEdit->setEnabled(false);
        root->addWidget(m_searchEdit);
        connect(m_searchEdit, &QLineEdit::textChanged, this, &PackagesScreen::onSearch);

        auto* splitter = new QSplitter(Qt::Horizontal);
        splitter->setStyleSheet("QSplitter::handle { background: #2e2b3d; width: 2px; }");

        m_resultsList = new QListWidget();
        auto* resultsWrap = new QWidget();
        auto* rv = new QVBoxLayout(resultsWrap); rv->setContentsMargins(0,0,0,0);
        auto* rl = new QLabel("RESULTS"); rl->setObjectName("sec");
        rv->addWidget(rl); rv->addWidget(m_resultsList);
        splitter->addWidget(resultsWrap);

        m_selectedList = new QListWidget();
        auto* selWrap = new QWidget();
        auto* sv = new QVBoxLayout(selWrap); sv->setContentsMargins(0,0,0,0);
        auto* sl = new QLabel("SELECTED"); sl->setObjectName("sec");
        sv->addWidget(sl); sv->addWidget(m_selectedList);
        splitter->addWidget(selWrap);
        splitter->setSizes({500,300});
        root->addWidget(splitter, 1);

        connect(m_resultsList, &QListWidget::itemDoubleClicked, this, &PackagesScreen::addPackage);

        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back");      backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        auto* remBtn  = new QPushButton("Remove selected"); remBtn->setObjectName("secondary"); remBtn->setStyleSheet(Theme::secondaryBtn());
        auto* nextBtn = new QPushButton("Continue →");  nextBtn->setObjectName("primary"); nextBtn->setStyleSheet(Theme::primaryBtn());
        backBtn->setMinimumHeight(44); remBtn->setMinimumHeight(44); nextBtn->setMinimumHeight(44);
        connect(backBtn, &QPushButton::clicked, this, &PackagesScreen::back);
        connect(remBtn,  &QPushButton::clicked, this, &PackagesScreen::removePackage);
        connect(nextBtn, &QPushButton::clicked, this, [this](){ emit confirmed(m_selected); });
        btnRow->addWidget(backBtn); btnRow->addWidget(remBtn); btnRow->addStretch(); btnRow->addWidget(nextBtn);
        root->addLayout(btnRow);

        startSync();
    }

private slots:
    void startSync() {
        auto* worker = new SyncWorker();
        connect(worker, &SyncWorker::status, this, [this](const QString& s){ m_statusLbl->setText(s); });
        connect(worker, &SyncWorker::done, this, [this](){
            m_statusLbl->setText("Database synced — double-click a result to add");
            m_statusLbl->setObjectName("info");
            m_statusLbl->style()->unpolish(m_statusLbl); m_statusLbl->style()->polish(m_statusLbl);
            m_searchEdit->setEnabled(true);
        });
        connect(worker, &SyncWorker::error, this, [this](const QString& e){
            m_statusLbl->setText("Sync failed: " + e.left(80) + " — search may be limited");
            m_statusLbl->setObjectName("warn");
            m_searchEdit->setEnabled(true);
        });
        connect(worker, &SyncWorker::finished, worker, &QObject::deleteLater);
        worker->start();
    }

    void onSearch(const QString& q) {
        if (q.length() < 2) { m_resultsList->clear(); return; }
        auto* worker = new SearchWorker(q);
        connect(worker, &SearchWorker::results, this, [this](const QStringList& pkgs){
            m_resultsList->clear();
            for (const auto& p : pkgs) m_resultsList->addItem(p);
        });
        connect(worker, &SearchWorker::finished, worker, &QObject::deleteLater);
        worker->start();
    }

    void addPackage(QListWidgetItem* item) {
        if (!item) return;
        QString pkg = item->text();
        if (!m_selected.contains(pkg)) {
            m_selected.append(pkg);
            m_selectedList->addItem(pkg);
        }
    }

    void removePackage() {
        for (auto* it : m_selectedList->selectedItems()) {
            m_selected.removeAll(it->text());
            delete it;
        }
    }

private:
    QLabel       *m_statusLbl;
    QLineEdit    *m_searchEdit;
    QListWidget  *m_resultsList, *m_selectedList;
    QStringList   m_selected;
};

// ── SystemScreen ──────────────────────────────────────────────────────────────

class SystemScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QStringList packages, QStringList services);
    void back();

public:
    // Structs at class scope
    struct AudioOpt { QString label; QStringList pkgs, svcs; };
    struct SvcOpt   { QString label; QStringList pkgs, svcs; };

    explicit SystemScreen(QWidget* parent = nullptr) : QWidget(parent) {
        // Direct brace-init into members
        m_audioOpts = {
            {"PipeWire (recommended)", {"pipewire","pipewire-alsa","pipewire-pulse","wireplumber"}, {"pipewire","wireplumber"}},
            {"PulseAudio",             {"pulseaudio","pulseaudio-alsa"},                            {"pulseaudio"}},
            {"None",                   {},                                                          {}},
        };
        m_svcOpts = {
            {"Bluetooth",         {"bluez","bluez-utils"}, {"bluetooth"}},
            {"Printing (CUPS)",   {"cups","cups-pdf"},      {"cups"}},
            {"Firewall (UFW)",    {"ufw"},                  {"ufw"}},
            {"SSH Server",        {"openssh"},              {"sshd"}},
            {"Cron (cronie)",     {"cronie"},               {"cronie"}},
        };

        auto* scroll = new QScrollArea(this);
        scroll->setWidgetResizable(true);
        auto* inner  = new QWidget();
        scroll->setWidget(inner);
        auto* outerLayout = new QVBoxLayout(this);
        outerLayout->setContentsMargins(0,0,0,0);
        outerLayout->addWidget(scroll);

        auto* root = new QVBoxLayout(inner);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("System Setup"); t->setObjectName("title");
        auto* s = new QLabel("Choose system services to enable.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        auto* audioLbl = new QLabel("AUDIO"); audioLbl->setObjectName("sec");
        root->addWidget(audioLbl);
        auto* audioGroup = new QButtonGroup(this);
        for (int i = 0; i < m_audioOpts.size(); ++i) {
            auto* rb = new QRadioButton(m_audioOpts[i].label);
            if (i == 0) rb->setChecked(true);
            audioGroup->addButton(rb, i);
            root->addWidget(rb);
        }
        connect(audioGroup, &QButtonGroup::idToggled, this, [this](int id, bool on){ if(on) m_audioSel=id; });

        auto* svcLbl = new QLabel("OPTIONAL SERVICES"); svcLbl->setObjectName("sec");
        root->addWidget(svcLbl);
        m_svcChecks.clear();
        for (const auto& opt : m_svcOpts) {
            auto* cb = new QCheckBox(opt.label);
            root->addWidget(cb);
            m_svcChecks.append(cb);
        }

        root->addStretch();

        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back"); backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        auto* nextBtn = new QPushButton("Continue →"); nextBtn->setObjectName("primary"); nextBtn->setStyleSheet(Theme::primaryBtn());
        connect(backBtn, &QPushButton::clicked, this, &SystemScreen::back);
        connect(nextBtn, &QPushButton::clicked, this, &SystemScreen::onConfirm);
        btnRow->addWidget(backBtn); btnRow->addStretch(); btnRow->addWidget(nextBtn);
        root->addLayout(btnRow);
    }

private slots:
    void onConfirm() {
        QStringList pkgs, svcs;
        if (m_audioSel >= 0 && m_audioSel < m_audioOpts.size()) {
            pkgs += m_audioOpts[m_audioSel].pkgs;
            svcs += m_audioOpts[m_audioSel].svcs;
        }
        for (int i = 0; i < m_svcChecks.size(); ++i) {
            if (m_svcChecks[i]->isChecked()) {
                pkgs += m_svcOpts[i].pkgs;
                svcs += m_svcOpts[i].svcs;
            }
        }
        emit confirmed(pkgs, svcs);
    }

private:
    QList<AudioOpt>   m_audioOpts;
    QList<SvcOpt>     m_svcOpts;
    int               m_audioSel = 0;
    QList<QCheckBox*> m_svcChecks;
};
