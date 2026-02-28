#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QFrame>
#include "Theme.h"

class WelcomeScreen : public QWidget {
    Q_OBJECT
signals:
    void proceed();

public:
    explicit WelcomeScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* v = new QVBoxLayout(this);
        v->setAlignment(Qt::AlignCenter);
        v->setSpacing(20);
        v->setContentsMargins(80,80,80,80);

        auto* glyph = new QLabel("✦");
        glyph->setStyleSheet(QString("font-size:52px; color:%1; background:transparent;").arg(Theme::PINK));
        glyph->setAlignment(Qt::AlignCenter);

        auto* title = new QLabel("Archey");
        title->setStyleSheet(QString("font-size:42px; font-weight:bold; color:%1; letter-spacing:4px; background:transparent;").arg(Theme::TEXT));
        title->setAlignment(Qt::AlignCenter);

        auto* tagline = new QLabel("a friendlier arch linux installer");
        tagline->setStyleSheet(QString("font-size:14px; color:%1; letter-spacing:3px; background:transparent;").arg(Theme::PINK));
        tagline->setAlignment(Qt::AlignCenter);

        auto* div = new QFrame();
        div->setFixedHeight(1);
        div->setStyleSheet(QString("background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 transparent, stop:0.5 %1, stop:1 transparent);").arg(Theme::ROSE));

        auto* warn = new QLabel("⚠  This installer will modify your disk partitions.\nBack up important data before continuing.");
        warn->setStyleSheet(QString(
            "font-size:13px; color:%1;"
            "background-color:#1f1520; border:1px solid #3d2535;"
            "border-left:3px solid %2;"
            "border-radius:8px; padding:16px 20px;"
        ).arg(Theme::TEXT2).arg(Theme::ROSE));
        warn->setAlignment(Qt::AlignCenter);
        warn->setWordWrap(true);

        auto* btn = new QPushButton("Get Started →");
        btn->setFixedWidth(220);
        btn->setFixedHeight(44);
        btn->setStyleSheet(QString(R"(
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %1, stop:1 %2);
                color: #12111a; border: none; border-radius: 8px;
                font-size: 14px; font-weight: bold; letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %2, stop:1 %3);
            }
        )").arg(Theme::ROSE).arg(Theme::PINK).arg(Theme::PINK2));
        connect(btn, &QPushButton::clicked, this, &WelcomeScreen::proceed);

        v->addWidget(glyph);
        v->addWidget(title);
        v->addWidget(tagline);
        v->addSpacing(8);
        v->addWidget(div);
        v->addSpacing(8);
        v->addWidget(warn);
        v->addSpacing(16);
        v->addWidget(btn, 0, Qt::AlignCenter);
    }
};
