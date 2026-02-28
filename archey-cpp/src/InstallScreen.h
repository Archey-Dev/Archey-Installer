#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QProgressBar>
#include <QTextEdit>
#include <QPushButton>
#include <QScrollBar>
#include "Theme.h"
#include "InstallState.h"
#include "InstallWorker.h"

class InstallScreen : public QWidget {
    Q_OBJECT
signals:
    void finished();

public:
    explicit InstallScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(16);

        auto* t = new QLabel("Installing Arch Linux"); t->setObjectName("title");
        root->addWidget(t);

        m_stepLbl = new QLabel("Preparing...");
        m_stepLbl->setObjectName("sub");
        root->addWidget(m_stepLbl);

        m_progress = new QProgressBar();
        m_progress->setRange(0,100);
        m_progress->setValue(0);
        m_progress->setTextVisible(false);
        m_progress->setFixedHeight(10);
        root->addWidget(m_progress);

        m_pctLbl = new QLabel("0%");
        m_pctLbl->setStyleSheet(QString("font-size:13px; color:%1;").arg(Theme::PINK));
        m_pctLbl->setAlignment(Qt::AlignRight);
        root->addWidget(m_pctLbl);

        auto* logLbl = new QLabel("INSTALLATION LOG"); logLbl->setObjectName("sec");
        root->addWidget(logLbl);

        m_log = new QTextEdit();
        m_log->setReadOnly(true);
        m_log->setStyleSheet(QString(
            "QTextEdit { background:%1; border:1px solid %2; border-radius:10px;"
            "font-family:'IBM Plex Mono',monospace; font-size:11px; color:%3; padding:10px; }"
        ).arg(Theme::BG2).arg(Theme::BORDER).arg(Theme::TEXT3));
        root->addWidget(m_log, 1);

        m_failLbl = new QLabel();
        m_failLbl->setObjectName("err");
        m_failLbl->setWordWrap(true);
        m_failLbl->setVisible(false);
        root->addWidget(m_failLbl);
    }

    void start(const InstallState& state) {
        m_log->clear();
        m_progress->setValue(0);
        m_failLbl->setVisible(false);

        m_worker = new InstallWorker(state);
        connect(m_worker, &InstallWorker::progress, this, [this](const QString& msg, int pct){
            m_stepLbl->setText(msg);
            m_progress->setValue(pct);
            m_pctLbl->setText(QString("%1%").arg(pct));
        });
        connect(m_worker, &InstallWorker::logLine, this, [this](const QString& line){
            // Colour-code log lines
            QString colour = Theme::TEXT3;
            if (line.startsWith("$ "))          colour = Theme::PINK;
            else if (line.startsWith("[") && line.contains("%]")) colour = Theme::YELLOW;
            else if (line.contains("error", Qt::CaseInsensitive) ||
                     line.contains("failed", Qt::CaseInsensitive)) colour = Theme::RED;
            else if (line.contains("warning", Qt::CaseInsensitive)) colour = Theme::YELLOW;
            else if (line.startsWith("==>"))    colour = Theme::GREEN;

            m_log->append(QString("<span style='color:%1'>%2</span>")
                          .arg(colour, line.toHtmlEscaped()));
            m_log->verticalScrollBar()->setValue(m_log->verticalScrollBar()->maximum());
        });
        connect(m_worker, &InstallWorker::succeeded, this, [this](){
            m_stepLbl->setText("Installation complete!");
            m_progress->setValue(100);
            m_pctLbl->setText("100%");
            emit finished();
        });
        connect(m_worker, &InstallWorker::failed, this, [this](const QString& err){
            m_failLbl->setText("Error: " + err);
            m_failLbl->setVisible(true);
            m_stepLbl->setText("Installation Failed");
            m_stepLbl->setStyleSheet(QString("color:%1;").arg(Theme::RED));
        });
        connect(m_worker, &InstallWorker::finished, m_worker, &QObject::deleteLater);
        m_worker->start();
    }

private:
    QLabel       *m_stepLbl, *m_pctLbl, *m_failLbl;
    QProgressBar *m_progress;
    QTextEdit    *m_log;
    InstallWorker *m_worker = nullptr;
};
