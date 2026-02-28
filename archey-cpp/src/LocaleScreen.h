#pragma once
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QLineEdit>
#include <QListWidget>
#include <QTabWidget>
#include <QFrame>
#include "Theme.h"

class LocaleScreen : public QWidget {
    Q_OBJECT
signals:
    void confirmed(QString locale, QString timezone, QString keymap);
    void back();

public:
    explicit LocaleScreen(QWidget* parent = nullptr) : QWidget(parent) {
        auto* root = new QVBoxLayout(this);
        root->setContentsMargins(48,40,48,32);
        root->setSpacing(12);

        auto* t = new QLabel("Language & Region"); t->setObjectName("title");
        auto* s = new QLabel("Choose your locale, timezone and keyboard layout.");
        s->setObjectName("sub"); s->setWordWrap(true);
        root->addWidget(t); root->addWidget(s);

        // Tabs
        auto* tabs = new QTabWidget();
        tabs->setStyleSheet(QString(R"(
            QTabWidget::pane { border: 1px solid %1; border-radius: 8px; background: %2; }
            QTabBar::tab { background: %3; color: %4; padding: 8px 20px; border-radius: 6px; margin-right: 4px; font-size: 12px; }
            QTabBar::tab:selected { background: %5; color: %6; font-weight: bold; }
        )").arg(Theme::BORDER).arg(Theme::BG2).arg(Theme::BG3).arg(Theme::TEXT3).arg(Theme::PINK_DIM).arg(Theme::PINK));
        tabs->setMaximumHeight(460);
        root->addWidget(tabs, 1);

        // ── Locale tab ─────────────────────────────────────────────────────
        auto* localeTab = new QWidget();
        auto* lv = new QVBoxLayout(localeTab);
        lv->setContentsMargins(12,12,12,12);
        m_localeSearch = new QLineEdit(); m_localeSearch->setPlaceholderText("Search locales...");
        m_localeList   = new QListWidget();
        lv->addWidget(m_localeSearch); lv->addWidget(m_localeList);
        connect(m_localeSearch, &QLineEdit::textChanged, this, &LocaleScreen::filterLocales);
        connect(m_localeList, &QListWidget::currentTextChanged, this, [this](const QString& t){ m_locale = t; });
        tabs->addTab(localeTab, "Locale");

        // ── Timezone tab ───────────────────────────────────────────────────
        auto* tzTab = new QWidget();
        auto* tv = new QVBoxLayout(tzTab);
        tv->setContentsMargins(12,12,12,12);
        m_tzSearch = new QLineEdit(); m_tzSearch->setPlaceholderText("Search timezones...");
        m_tzList   = new QListWidget();
        tv->addWidget(m_tzSearch); tv->addWidget(m_tzList);
        connect(m_tzSearch, &QLineEdit::textChanged, this, &LocaleScreen::filterTimezones);
        connect(m_tzList, &QListWidget::currentTextChanged, this, [this](const QString& t){ m_timezone = t; });
        tabs->addTab(tzTab, "Timezone");

        // ── Keyboard tab ───────────────────────────────────────────────────
        auto* kbTab = new QWidget();
        auto* kv = new QVBoxLayout(kbTab);
        kv->setContentsMargins(12,12,12,12);
        m_kbSearch = new QLineEdit(); m_kbSearch->setPlaceholderText("Search keymaps...");
        m_kbList   = new QListWidget();
        kv->addWidget(m_kbSearch); kv->addWidget(m_kbList);
        connect(m_kbSearch, &QLineEdit::textChanged, this, &LocaleScreen::filterKeymaps);
        connect(m_kbList, &QListWidget::currentTextChanged, this, [this](const QString& t){ m_keymap = t; });
        tabs->addTab(kbTab, "Keyboard");

        // Summary
        m_summaryLbl = new QLabel();
        m_summaryLbl->setObjectName("hint");
        root->addWidget(m_summaryLbl);

        // Buttons
        auto* btnRow = new QHBoxLayout();
        auto* backBtn = new QPushButton("← Back"); backBtn->setObjectName("secondary"); backBtn->setStyleSheet(Theme::secondaryBtn());
        auto* nextBtn = new QPushButton("Continue →"); nextBtn->setObjectName("primary"); nextBtn->setStyleSheet(Theme::primaryBtn());
        connect(backBtn, &QPushButton::clicked, this, &LocaleScreen::back);
        connect(nextBtn, &QPushButton::clicked, this, &LocaleScreen::onConfirm);
        btnRow->addWidget(backBtn); btnRow->addStretch(); btnRow->addWidget(nextBtn);
        root->addLayout(btnRow);

        populateAll();
    }

private slots:
    void filterLocales(const QString& q) {
        for (int i = 0; i < m_localeList->count(); ++i) {
            auto* it = m_localeList->item(i);
            it->setHidden(!it->text().contains(q, Qt::CaseInsensitive));
        }
    }
    void filterTimezones(const QString& q) {
        for (int i = 0; i < m_tzList->count(); ++i) {
            auto* it = m_tzList->item(i);
            it->setHidden(!it->text().contains(q, Qt::CaseInsensitive));
        }
    }
    void filterKeymaps(const QString& q) {
        for (int i = 0; i < m_kbList->count(); ++i) {
            auto* it = m_kbList->item(i);
            it->setHidden(!it->text().contains(q, Qt::CaseInsensitive));
        }
    }
    void onConfirm() {
        if (m_locale.isEmpty())   m_locale   = "en_US.UTF-8";
        if (m_timezone.isEmpty()) m_timezone = "UTC";
        if (m_keymap.isEmpty())   m_keymap   = "us";
        emit confirmed(m_locale, m_timezone, m_keymap);
    }

private:
    QString m_locale   = "en_US.UTF-8";
    QString m_timezone = "UTC";
    QString m_keymap   = "us";
    QLineEdit   *m_localeSearch, *m_tzSearch, *m_kbSearch;
    QListWidget *m_localeList, *m_tzList, *m_kbList;
    QLabel      *m_summaryLbl;

    void populateAll() {
        // Locales
        QStringList locales = {
            "en_US.UTF-8","en_GB.UTF-8","de_DE.UTF-8","fr_FR.UTF-8",
            "es_ES.UTF-8","it_IT.UTF-8","pt_BR.UTF-8","pt_PT.UTF-8",
            "ru_RU.UTF-8","ja_JP.UTF-8","zh_CN.UTF-8","zh_TW.UTF-8",
            "ko_KR.UTF-8","nl_NL.UTF-8","pl_PL.UTF-8","sv_SE.UTF-8",
            "nb_NO.UTF-8","da_DK.UTF-8","fi_FI.UTF-8","cs_CZ.UTF-8",
            "hu_HU.UTF-8","ro_RO.UTF-8","uk_UA.UTF-8","tr_TR.UTF-8",
            "ar_EG.UTF-8","he_IL.UTF-8","fa_IR.UTF-8","th_TH.UTF-8",
            "vi_VN.UTF-8","id_ID.UTF-8",
        };
        for (const auto& l : locales) {
            auto* it = new QListWidgetItem(l, m_localeList);
            if (l == "en_US.UTF-8") { m_localeList->setCurrentItem(it); }
        }

        // Timezones (common subset)
        QStringList tzs = {
            "UTC",
            "America/New_York","America/Chicago","America/Denver","America/Los_Angeles",
            "America/Toronto","America/Vancouver","America/Sao_Paulo","America/Mexico_City",
            "America/Buenos_Aires","America/Bogota","America/Lima",
            "Europe/London","Europe/Paris","Europe/Berlin","Europe/Rome","Europe/Madrid",
            "Europe/Amsterdam","Europe/Stockholm","Europe/Oslo","Europe/Warsaw",
            "Europe/Prague","Europe/Vienna","Europe/Zurich","Europe/Athens",
            "Europe/Bucharest","Europe/Kiev","Europe/Moscow","Europe/Istanbul",
            "Asia/Tokyo","Asia/Seoul","Asia/Shanghai","Asia/Hong_Kong","Asia/Singapore",
            "Asia/Kolkata","Asia/Karachi","Asia/Dubai","Asia/Tehran","Asia/Riyadh",
            "Asia/Bangkok","Asia/Jakarta","Asia/Manila","Asia/Taipei",
            "Australia/Sydney","Australia/Melbourne","Australia/Perth","Australia/Brisbane",
            "Pacific/Auckland","Pacific/Honolulu","Africa/Cairo","Africa/Johannesburg",
            "Africa/Lagos","Africa/Nairobi",
        };
        for (const auto& tz : tzs) {
            auto* it = new QListWidgetItem(tz, m_tzList);
            if (tz == "UTC") { m_tzList->setCurrentItem(it); }
        }

        // Keymaps
        QStringList kbs = {
            "us","uk","de","fr","es","it","pt","ru","jp106",
            "dvorak","colemak","pl","cz","hu","ro","tr","ar",
            "be","br-abnt2","ca","ch","dk","fi","gr","il",
            "latam","nl","no","se","sk","ua",
        };
        for (const auto& kb : kbs) {
            auto* it = new QListWidgetItem(kb, m_kbList);
            if (kb == "us") { m_kbList->setCurrentItem(it); }
        }
    }
};
