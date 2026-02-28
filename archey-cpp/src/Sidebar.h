#pragma once
#include <QFrame>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QVector>
#include "Theme.h"

class Sidebar : public QFrame {
    Q_OBJECT
public:
    static constexpr const char* STEPS[] = {
        "Welcome","Language","Wi-Fi","Disk Setup",
        "User Setup","Desktop","Hardware","Packages","System","Install","Done"
    };
    static constexpr int STEP_COUNT = 11;

    explicit Sidebar(QWidget* parent = nullptr) : QFrame(parent) {
        setFixedWidth(200);
        setStyleSheet(QString(R"(
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a1228, stop:0.5 %1, stop:1 #1a1228);
                border-right: 1px solid %2;
            }
        )").arg(Theme::BG2).arg(Theme::BORDER));

        auto* v = new QVBoxLayout(this);
        v->setContentsMargins(20,40,20,32);
        v->setSpacing(2);

        // Logo row
        auto* logoRow = new QHBoxLayout();
        auto* dot  = new QLabel("✦");
        dot->setStyleSheet(QString("font-size:18px; color:%1; background:transparent;").arg(Theme::PINK));
        auto* name = new QLabel("Archey");
        name->setStyleSheet(QString("font-size:16px; font-weight:bold; color:%1; background:transparent; letter-spacing:1px;").arg(Theme::TEXT));
        logoRow->addWidget(dot);
        logoRow->addWidget(name);
        logoRow->addStretch();
        v->addLayout(logoRow);
        v->addSpacing(32);

        for (int i = 0; i < STEP_COUNT; ++i) {
            auto* lbl = new QLabel(QString("  %1").arg(STEPS[i]));
            lbl->setStyleSheet(inactiveStyle());
            v->addWidget(lbl);
            m_labels.append(lbl);
        }
        v->addStretch();

        auto* ver = new QLabel("v0.1.0");
        ver->setStyleSheet(QString("font-size:10px; color:%1; background:transparent; letter-spacing:2px;").arg(Theme::BORDER));
        v->addWidget(ver);
    }

    void setStep(int index) {
        for (int i = 0; i < m_labels.size(); ++i) {
            if (i == index)
                m_labels[i]->setStyleSheet(activeStyle());
            else if (i < index)
                m_labels[i]->setStyleSheet(doneStyle());
            else
                m_labels[i]->setStyleSheet(inactiveStyle());
        }
    }

private:
    QVector<QLabel*> m_labels;

    QString activeStyle() const {
        return QString("font-size:12px; font-weight:bold; color:%1;"
                       "background-color:#2d1a24; padding:8px 8px;"
                       "border-radius:7px; border-left:3px solid %1;").arg(Theme::PINK);
    }
    QString doneStyle() const {
        return QString("font-size:12px; color:%1; padding:8px 8px;"
                       "border-radius:7px; background:transparent;"
                       "border-left:3px solid #3d2a34;").arg(Theme::TEXT2);
    }
    QString inactiveStyle() const {
        return QString("font-size:12px; color:%1; padding:8px 8px;"
                       "border-radius:7px; background:transparent;").arg(Theme::TEXT3);
    }
};
