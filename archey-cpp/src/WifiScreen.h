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
#include <QTimer>
#include <QRegularExpression>
#include "Theme.h"

// ── helpers ───────────────────────────────────────────────────────────────────

static QString runCmd(const QString& prog, const QStringList& args, int timeoutMs = 15000) {
    QProcess p;
    p.start(prog, args);
    p.waitForFinished(timeoutMs);
    return p.readAllStandardOutput() + p.readAllStandardError();
}

static QString stripAnsi(const QString& s) {
    return QString(s).remove(QRegularExpression("\x1b\\[[0-9;]*[a-zA-Z]"));
}

static QString findDevice() {
    QString out = runCmd("iwctl", {"device","list"});
    for (const QString& line : out.split('\n')) {
        QString clean = stripAnsi(line).trimmed();
        if (clean.isEmpty()) continue;
        if (clean.startsWith('-') || clean.startsWith("─") || clean.startsWith("━")) continue;
        if (clean.contains("Name") && clean.contains("Powered")) continue;
        QStringList parts = clean.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts);
        if (!parts.isEmpty() && (parts[0].startsWith("wl") || parts[0].startsWith("ww")))
            return parts[0];
    }
    return {};
}

static QString signalBars(const QString& sig) {
    bool ok;
    int v = sig.toInt(&ok);
    if (ok) {
        if (v >= -50) return "▂▄▆█";
        if (v >= -60) return "▂▄▆░";
        if (v >= -70) return "▂▄░░";
        if (v >= -80) return "▂░░░";
        return "░░░░";
    }
    int stars = sig.count('*');
    QStringList bars{"░░░░","▂░░░","▂▄░░","▂▄▆░","▂▄▆█"};
    return bars[qBound(0, stars, 4)];
}

// ── ScanWorker ────────────────────────────────────────────────────────────────

struct Network {
    QString ssid, security, signal, device;
    bool connected = false;
    bool operator==(const Network& o) const { return ssid == o.ssid && device == o.device; }
};

class ScanWorker : public QThread {
    Q_OBJECT
signals:
    void deviceFound(QString device);
    void resultsReady(QList<Network> nets);
    void errorOccurred(QString msg);

protected:
    void run() override {
        runCmd("rfkill", {"unblock","wifi"});
        QString dev = findDevice();
        if (dev.isEmpty()) {
            QThread::sleep(1);
            dev = findDevice();
        }
        if (dev.isEmpty()) {
            emit errorOccurred("No wireless device found. Make sure iwd is running.");
            return;
        }
        emit deviceFound(dev);
        runCmd("iwctl", {"station", dev, "scan"});
        QThread::sleep(3);

        QString out = runCmd("iwctl", {"station", dev, "get-networks"});
        QList<Network> nets;
        QSet<QString> seen;
        bool inTable = false;

        for (const QString& rawLine : out.split('\n')) {
            QString s = rawLine.trimmed();
            if (s.isEmpty()) continue;
            if (s.contains("Available networks")) continue;
            if (s.contains("Network name") || s.contains("─") || s.contains("━")) { inTable = true; continue; }
            if (!inTable) continue;

            QString clean = stripAnsi(rawLine);
            bool connected = clean.contains('>');
            clean.remove('>');
            QStringList parts = clean.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts);
            if (parts.size() < 2) continue;

            QString signal   = parts.last();
            QString security = parts.size() >= 2 ? parts[parts.size()-2].toLower() : "open";
            QString ssid     = parts.mid(0, parts.size()-2).join(' ');
            if (ssid.isEmpty() || seen.contains(ssid)) continue;
            seen.insert(ssid);
            nets.append({ssid, security, signal, dev, connected});
        }
        emit resultsReady(nets);
    }
};

// ── ConnectWorker ─────────────────────────────────────────────────────────────

class ConnectWorker : public QThread {
    Q_OBJECT
signals:
    void success(QString ssid);
    void failure(QString msg);

public:
    ConnectWorker(const QString& dev, const QString& ssid, const QString& pw)
        : m_dev(dev), m_ssid(ssid), m_pw(pw) {}

protected:
    void run() override {
        QProcess p;
        QStringList args;
        if (!m_pw.isEmpty())
            args << "--passphrase" << m_pw;
        args << "station" << m_dev << "connect" << m_ssid;
        p.start("iwctl", args);
        p.waitForFinished(30000);

        if (p.exitCode() == 0) {
            QThread::sleep(2);
            emit success(m_ssid);
        } else {
            QString out = p.readAllStandardOutput() + p.readAllStandardError();
            emit failure(out.trimmed().isEmpty() ? "Connection failed — check your password." : out.trimmed());
        }
    }

private:
    QString m_dev, m_ssid, m_pw;
};

// ── Screen ────────────────────────────────────────────────────────────────────

class WifiScreen : public QWidget {
    Q_OBJECT
signals:
    void connected();

public:
    explicit WifiScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Wi-Fi"); t->setObjectName("title");
        auto* s = new QLabel("Connect to a wireless network to download packages during installation.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        m_deviceLbl = new QLabel("Detecting wireless device...");
        m_deviceLbl->setObjectName("hint");
        root->addWidget(m_deviceLbl);

        m_progress = new QProgressBar();
        m_progress->setRange(0,0);
        m_progress->setFixedHeight(4);
        m_progress->setTextVisible(false);
        root->addWidget(m_progress);

        auto* netLbl = new QLabel("AVAILABLE NETWORKS"); netLbl->setObjectName("sec");
        root->addWidget(netLbl);

        m_netList = new QListWidget();
        m_netList->setMaximumHeight(400);
        root->addWidget(m_netList, 1);
        connect(m_netList, &QListWidget::itemSelectionChanged, this, &WifiScreen::onSelect);

        m_status = new QLabel("Scanning...");
        m_status->setObjectName("sub");
        m_status->setAlignment(Qt::AlignCenter);
        root->addWidget(m_status);

        m_pwInput = new QLineEdit();
        m_pwInput->setPlaceholderText("Password");
        m_pwInput->setEchoMode(QLineEdit::Password);
        m_pwInput->setVisible(false);
        connect(m_pwInput, &QLineEdit::returnPressed, this, &WifiScreen::onConnect);
        root->addWidget(m_pwInput);

        auto* btnRow = new QHBoxLayout();
        m_scanBtn = new QPushButton("↻  Scan again"); m_scanBtn->setObjectName("secondary"); m_scanBtn->setStyleSheet(Theme::secondaryBtn());
        m_scanBtn->setEnabled(false);
        connect(m_scanBtn, &QPushButton::clicked, this, &WifiScreen::scan);

        auto* skipBtn = new QPushButton("Skip (ethernet)"); skipBtn->setObjectName("secondary"); skipBtn->setStyleSheet(Theme::secondaryBtn());
        connect(skipBtn, &QPushButton::clicked, this, &WifiScreen::connected);

        m_connBtn = new QPushButton("Connect →"); m_connBtn->setObjectName("primary"); m_connBtn->setStyleSheet(Theme::primaryBtn());
        m_connBtn->setEnabled(false);
        connect(m_connBtn, &QPushButton::clicked, this, &WifiScreen::onConnect);

        btnRow->addWidget(m_scanBtn);
        btnRow->addStretch();
        btnRow->addWidget(skipBtn);
        btnRow->addWidget(m_connBtn);
        root->addLayout(btnRow);

        QTimer::singleShot(300, this, [this](){
            QProcess::startDetached("systemctl", {"start","iwd"});
            QThread::msleep(500);
            scan();
        });
    }

private slots:
    void scan() {
        m_netList->clear();
        m_pwInput->setVisible(false);
        m_connBtn->setEnabled(false);
        m_scanBtn->setEnabled(false);
        m_status->setText("Scanning for networks...");
        m_status->setStyleSheet("");
        m_progress->setVisible(true);

        auto* worker = new ScanWorker();
        connect(worker, &ScanWorker::deviceFound, this, [this](const QString& d){
            m_device = d;
            m_deviceLbl->setText("Device: " + d);
        });
        connect(worker, &ScanWorker::resultsReady, this, &WifiScreen::onScanDone);
        connect(worker, &ScanWorker::errorOccurred, this, &WifiScreen::onScanError);
        connect(worker, &ScanWorker::finished, worker, &QObject::deleteLater);
        worker->start();
    }

    void onScanDone(QList<Network> nets) {
        m_progress->setVisible(false);
        m_scanBtn->setEnabled(true);
        m_networks = nets;

        if (nets.isEmpty()) {
            m_status->setText("No networks found. Try scanning again.");
            return;
        }
        m_status->setText(QString("%1 network(s) found").arg(nets.size()));

        for (const auto& net : nets) {
            QString bars = signalBars(net.signal);
            QString lock = (net.security != "open" && !net.security.isEmpty()) ? "[+]" : "[ ]";
            QString tag  = net.connected ? "  ← connected" : "";
            auto* item   = new QListWidgetItem(QString("%1  %2  %3%4").arg(bars, lock, net.ssid, tag));
            item->setData(Qt::UserRole, nets.indexOf(net));
            m_netList->addItem(item);
        }
    }

    void onScanError(const QString& msg) {
        m_progress->setVisible(false);
        m_scanBtn->setEnabled(true);
        m_status->setText("Error: " + msg);
        m_status->setStyleSheet(QString("color:%1;").arg(Theme::YELLOW));
    }

    void onSelect() {
        auto items = m_netList->selectedItems();
        if (items.isEmpty()) { m_connBtn->setEnabled(false); m_pwInput->setVisible(false); return; }
        int idx = items[0]->data(Qt::UserRole).toInt();
        if (idx < 0 || idx >= m_networks.size()) return;
        const auto& net = m_networks[idx];
        bool needsPw = net.security != "open" && !net.security.isEmpty();
        m_pwInput->setVisible(needsPw);
        m_pwInput->clear();
        if (net.connected) {
            m_connBtn->setText("Already connected");
            m_connBtn->setEnabled(false);
        } else {
            m_connBtn->setText("Connect →");
            m_connBtn->setEnabled(true);
        }
        m_selectedNet = idx;
    }

    void onConnect() {
        if (m_selectedNet < 0 || m_device.isEmpty()) return;
        const auto& net = m_networks[m_selectedNet];
        QString pw = m_pwInput->isVisible() ? m_pwInput->text() : "";

        m_progress->setVisible(true);
        m_connBtn->setEnabled(false);
        m_scanBtn->setEnabled(false);
        m_status->setText("Connecting to " + net.ssid + "...");
        m_status->setStyleSheet("");

        auto* worker = new ConnectWorker(m_device, net.ssid, pw);
        connect(worker, &ConnectWorker::success, this, [this](const QString& ssid){
            m_progress->setVisible(false);
            m_status->setText("Connected to " + ssid);
            m_status->setStyleSheet(QString("color:%1;").arg(Theme::GREEN));
            QTimer::singleShot(800, this, &WifiScreen::connected);
        });
        connect(worker, &ConnectWorker::failure, this, [this](const QString& msg){
            m_progress->setVisible(false);
            m_scanBtn->setEnabled(true);
            m_connBtn->setEnabled(true);
            m_status->setText("Connection failed.");
            m_status->setStyleSheet(QString("color:%1;").arg(Theme::RED));
            (void)msg;
        });
        connect(worker, &ConnectWorker::finished, worker, &QObject::deleteLater);
        worker->start();
    }

private:
    QString         m_device;
    QList<Network>  m_networks;
    int             m_selectedNet = -1;
    QLabel         *m_deviceLbl, *m_status;
    QProgressBar   *m_progress;
    QListWidget    *m_netList;
    QLineEdit      *m_pwInput;
    QPushButton    *m_scanBtn, *m_connBtn;
};
