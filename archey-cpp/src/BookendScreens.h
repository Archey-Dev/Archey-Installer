#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QApplication>
#include <QProcess>
#include "Theme.h"

// ── UEFI block ────────────────────────────────────────────────────────────────

class UEFIBlockScreen : public QWidget {
    Q_OBJECT
signals:
    void proceed();

public:
    explicit UEFIBlockScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* v = new QVBoxLayout(this);
        v->setContentsMargins(80,0,80,0);
        v->setSpacing(16);
        v->addStretch(2);

        auto* glyph = new QLabel("⚠");
        glyph->setStyleSheet(QString("font-size:52px; color:%1; background:transparent;").arg(Theme::ROSE));
        glyph->setAlignment(Qt::AlignCenter);
        v->addWidget(glyph);

        auto* title = new QLabel("UEFI Not Detected");
        title->setObjectName("title");
        title->setAlignment(Qt::AlignCenter);
        v->addWidget(title);

        auto* desc = new QLabel(
            "Archey requires a UEFI system to install.\n\n"
            "This machine appears to have booted in Legacy BIOS mode. "
            "The installer uses a GPT + EFI partition layout which will not "
            "work on a BIOS/MBR system.\n\n"
            "If you believe this is wrong (e.g. you are in a VM with EFI enabled), "
            "you can continue anyway."
        );
        desc->setObjectName("sub");
        desc->setWordWrap(true);
        desc->setAlignment(Qt::AlignCenter);
        v->addWidget(desc);
        v->addSpacing(16);

        auto* btnRow = new QHBoxLayout();
        btnRow->setSpacing(12);

        auto* exitBtn = new QPushButton("Exit Installer");
        exitBtn->setObjectName("secondary"); exitBtn->setStyleSheet(Theme::secondaryBtn());
        connect(exitBtn, &QPushButton::clicked, qApp, &QApplication::quit);

        auto* contBtn = new QPushButton("Continue Anyway →");
        contBtn->setObjectName("primary"); contBtn->setStyleSheet(Theme::primaryBtn());
        connect(contBtn, &QPushButton::clicked, this, &UEFIBlockScreen::proceed);

        btnRow->addStretch();
        btnRow->addWidget(exitBtn);
        btnRow->addWidget(contBtn);
        btnRow->addStretch();
        v->addLayout(btnRow);
        v->addStretch(3);
    }
};

// ── Done screen ───────────────────────────────────────────────────────────────

class DoneScreen : public QWidget {
    Q_OBJECT
public:
    explicit DoneScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* v = new QVBoxLayout(this);
        v->setAlignment(Qt::AlignCenter);
        v->setSpacing(20);
        v->setContentsMargins(80,80,80,80);

        auto* glyph = new QLabel("✦");
        glyph->setStyleSheet(QString("font-size:64px; color:%1; background:transparent;").arg(Theme::PINK));
        glyph->setAlignment(Qt::AlignCenter);

        auto* title = new QLabel("Installation Complete");
        title->setStyleSheet(QString("font-size:32px; font-weight:bold; color:%1; letter-spacing:2px; background:transparent;").arg(Theme::TEXT));
        title->setAlignment(Qt::AlignCenter);

        auto* sub = new QLabel("Arch Linux has been installed successfully.\nRemove the USB drive and reboot to start using your system.");
        sub->setStyleSheet(QString("font-size:14px; color:%1; background:transparent;").arg(Theme::TEXT2));
        sub->setAlignment(Qt::AlignCenter);
        sub->setWordWrap(true);

        auto* btn = new QPushButton("Reboot Now");
        btn->setObjectName("primary"); btn->setStyleSheet(Theme::primaryBtn());
        btn->setFixedWidth(200);
        btn->setFixedHeight(44);
        connect(btn, &QPushButton::clicked, this, [](){
            QProcess::startDetached("reboot", {});
        });

        v->addWidget(glyph);
        v->addWidget(title);
        v->addWidget(sub);
        v->addSpacing(16);
        v->addWidget(btn, 0, Qt::AlignCenter);
    }
};
