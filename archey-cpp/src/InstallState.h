#pragma once
#include <QString>
#include <QStringList>
#include <QVariantMap>

struct InstallState {
    // Locale
    QString locale   = "en_US.UTF-8";
    QString timezone = "UTC";
    QString keymap   = "us";

    // Network
    QString wifiSsid;

    // Disk
    QVariantMap disk;
    QVariantMap efiPartition;
    QVariantMap windowsPartition;
    double      archSizeGb  = 40.0;
    QString     installMode = "wipe";

    // User
    QString hostname;
    QString username;
    QString password;

    // Desktop
    QVariantMap de;   // keys: name, packages (QStringList), dm (display manager)

    // Packages
    QStringList cpuPackages;
    QStringList gpuPackages;
    QStringList userPackages;
    QStringList systemPackages;
    QStringList systemServices;
};
