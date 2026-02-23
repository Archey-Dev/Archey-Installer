#!/usr/bin/env python3
"""
Archey — Language, Timezone & Keyboard layout screen.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView
from theme import MASTER_STYLE, PINK, TEXT, TEXT2, TEXT3, BG2, BORDER, GREEN

# ── Data ──────────────────────────────────────────────────────────────────────

TIMEZONES = [
    "UTC",
    "America/New_York","America/Chicago","America/Denver","America/Los_Angeles",
    "America/Toronto","America/Vancouver","America/Sao_Paulo","America/Mexico_City",
    "America/Buenos_Aires","America/Bogota","America/Lima","America/Santiago",
    "Europe/London","Europe/Paris","Europe/Berlin","Europe/Rome","Europe/Madrid",
    "Europe/Amsterdam","Europe/Stockholm","Europe/Warsaw","Europe/Prague",
    "Europe/Vienna","Europe/Zurich","Europe/Helsinki","Europe/Athens",
    "Europe/Istanbul","Europe/Moscow","Europe/Kiev","Europe/Lisbon",
    "Europe/Dublin","Europe/Oslo","Europe/Copenhagen","Europe/Brussels",
    "Asia/Tokyo","Asia/Shanghai","Asia/Hong_Kong","Asia/Singapore","Asia/Seoul",
    "Asia/Kolkata","Asia/Dubai","Asia/Tehran","Asia/Bangkok","Asia/Jakarta",
    "Asia/Karachi","Asia/Dhaka","Asia/Tashkent","Asia/Almaty","Asia/Tbilisi",
    "Australia/Sydney","Australia/Melbourne","Australia/Perth","Australia/Brisbane",
    "Pacific/Auckland","Pacific/Honolulu","Pacific/Fiji",
    "Africa/Cairo","Africa/Johannesburg","Africa/Lagos","Africa/Nairobi",
    "Africa/Casablanca","Africa/Accra",
]

LOCALES = [
    ("en_US.UTF-8", "English (United States)"),
    ("en_GB.UTF-8", "English (United Kingdom)"),
    ("en_AU.UTF-8", "English (Australia)"),
    ("en_CA.UTF-8", "English (Canada)"),
    ("en_IE.UTF-8", "English (Ireland)"),
    ("de_DE.UTF-8", "Deutsch (Deutschland)"),
    ("de_AT.UTF-8", "Deutsch (Österreich)"),
    ("de_CH.UTF-8", "Deutsch (Schweiz)"),
    ("fr_FR.UTF-8", "Français (France)"),
    ("fr_BE.UTF-8", "Français (Belgique)"),
    ("fr_CA.UTF-8", "Français (Canada)"),
    ("fr_CH.UTF-8", "Français (Suisse)"),
    ("es_ES.UTF-8", "Español (España)"),
    ("es_MX.UTF-8", "Español (México)"),
    ("es_AR.UTF-8", "Español (Argentina)"),
    ("es_CO.UTF-8", "Español (Colombia)"),
    ("pt_BR.UTF-8", "Português (Brasil)"),
    ("pt_PT.UTF-8", "Português (Portugal)"),
    ("it_IT.UTF-8", "Italiano (Italia)"),
    ("nl_NL.UTF-8", "Nederlands (Nederland)"),
    ("nl_BE.UTF-8", "Nederlands (België)"),
    ("pl_PL.UTF-8", "Polski (Polska)"),
    ("cs_CZ.UTF-8", "Čeština (Česká republika)"),
    ("sk_SK.UTF-8", "Slovenčina (Slovensko)"),
    ("hu_HU.UTF-8", "Magyar (Magyarország)"),
    ("ro_RO.UTF-8", "Română (România)"),
    ("sv_SE.UTF-8", "Svenska (Sverige)"),
    ("nb_NO.UTF-8", "Norsk bokmål (Norge)"),
    ("fi_FI.UTF-8", "Suomi (Suomi)"),
    ("da_DK.UTF-8", "Dansk (Danmark)"),
    ("ru_RU.UTF-8", "Русский (Россия)"),
    ("uk_UA.UTF-8", "Українська (Україна)"),
    ("bg_BG.UTF-8", "Български (България)"),
    ("el_GR.UTF-8", "Ελληνικά (Ελλάδα)"),
    ("tr_TR.UTF-8", "Türkçe (Türkiye)"),
    ("zh_CN.UTF-8", "中文 (简体)"),
    ("zh_TW.UTF-8", "中文 (繁體)"),
    ("ja_JP.UTF-8", "日本語 (日本)"),
    ("ko_KR.UTF-8", "한국어 (한국)"),
    ("ar_SA.UTF-8", "العربية (السعودية)"),
    ("he_IL.UTF-8", "עברית (ישראל)"),
    ("hi_IN.UTF-8", "हिन्दी (भारत)"),
    ("th_TH.UTF-8", "ภาษาไทย (ไทย)"),
    ("vi_VN.UTF-8", "Tiếng Việt (Việt Nam)"),
    ("id_ID.UTF-8", "Bahasa Indonesia"),
    ("ms_MY.UTF-8", "Bahasa Melayu (Malaysia)"),
]

KEYMAPS = [
    ("us",          "English (US)"),
    ("us-acentos",  "English (US, intl. with dead keys)"),
    ("gb",          "English (UK)"),
    ("au",          "English (Australia)"),
    ("de",          "Deutsch (Deutschland)"),
    ("de-latin1",   "Deutsch (Latin-1)"),
    ("at",          "Deutsch (Österreich)"),
    ("ch",          "Deutsch (Schweiz)"),
    ("fr",          "Français (France)"),
    ("be-latin1",   "Français (Belgique)"),
    ("fr-latin1",   "Français (Latin-1)"),
    ("es",          "Español (España)"),
    ("la-latin1",   "Español (Latin America)"),
    ("br-abnt2",    "Português (Brasil ABNT2)"),
    ("pt-latin1",   "Português (Portugal)"),
    ("it",          "Italiano"),
    ("nl",          "Nederlands"),
    ("pl2",         "Polski"),
    ("cz-qwerty",   "Čeština (QWERTY)"),
    ("cz",          "Čeština (QWERTZ)"),
    ("sk-qwerty",   "Slovenčina (QWERTY)"),
    ("hu",          "Magyar"),
    ("ro",          "Română"),
    ("sv-latin1",   "Svenska"),
    ("no",          "Norsk"),
    ("fi",          "Suomi"),
    ("dk",          "Dansk"),
    ("ru",          "Русский"),
    ("ua",          "Українська"),
    ("bg_bds-utf8", "Български"),
    ("gr",          "Ελληνικά"),
    ("trq",         "Türkçe (Q)"),
    ("trf",         "Türkçe (F)"),
    ("jp106",       "日本語"),
    ("kr",          "한국어"),
    ("dvorak",      "Dvorak (US)"),
    ("dvorak-l",    "Dvorak (Left-handed)"),
    ("dvorak-r",    "Dvorak (Right-handed)"),
    ("colemak",     "Colemak"),
    ("workman",     "Workman"),
    ("azerty",      "AZERTY"),
    ("qwertz",      "QWERTZ"),
]


# ── Searchable list helper ────────────────────────────────────────────────────

def make_search_list(placeholder, items, on_select):
    """Returns (container_widget, list_widget, populate_fn)."""
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    v = QVBoxLayout(container)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(6)

    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    v.addWidget(search)

    lst = QListWidget()
    lst.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    lst.itemSelectionChanged.connect(lambda: on_select(lst))
    v.addWidget(lst)

    def populate(query=""):
        lst.clear()
        q = query.lower()
        for code, label in items:
            if q and q not in code.lower() and q not in label.lower():
                continue
            item = QListWidgetItem(f"{label}  [{code}]")
            item.setData(Qt.ItemDataRole.UserRole, code)
            lst.addItem(item)

    search.textChanged.connect(populate)
    populate()
    return container, lst, populate


# ── Main screen ───────────────────────────────────────────────────────────────

class LocaleScreen(QWidget):
    confirmed = pyqtSignal(str, str, str)   # locale, timezone, keymap
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE + f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {TEXT3};
                padding: 8px 20px;
                border: none;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QTabBar::tab:selected {{
                color: {PINK};
                border-bottom: 2px solid {PINK};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{ color: {TEXT}; }}
        """)
        self._sel_locale  = "en_US.UTF-8"
        self._sel_tz      = "UTC"
        self._sel_keymap  = "us"
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        t = QLabel("Language & Region"); t.setObjectName("title")
        s = QLabel("Set your locale, timezone and keyboard layout.")
        s.setObjectName("sub")
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(4)

        # Tabs
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # ── Tab 1: Locale ──────────────────────────────────────────────────
        locale_tab, self.locale_list, _ = make_search_list(
            "Search language…", LOCALES, self._on_locale_select
        )
        tabs.addTab(locale_tab, "🌐  Language")

        # ── Tab 2: Timezone ────────────────────────────────────────────────
        tz_items = [(tz, tz) for tz in TIMEZONES]
        tz_tab, self.tz_list, _ = make_search_list(
            "Search timezone…", tz_items, self._on_tz_select
        )
        tabs.addTab(tz_tab, "🕐  Timezone")

        # ── Tab 3: Keyboard ────────────────────────────────────────────────
        kb_tab, self.kb_list, _ = make_search_list(
            "Search keyboard layout…", KEYMAPS, self._on_kb_select
        )
        tabs.addTab(kb_tab, "⌨️  Keyboard")

        root.addWidget(tabs, stretch=1)

        # Summary bar
        self.summary = QLabel("")
        self.summary.setObjectName("info")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        self._update_summary()

        # Buttons
        btn_row = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back.emit)

        self.confirm_btn = QPushButton("Continue →")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(self.back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        root.addLayout(btn_row)

        # Select defaults
        self._select_default(self.locale_list, "en_US.UTF-8")
        self._select_default(self.tz_list, "UTC")
        self._select_default(self.kb_list, "us")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_locale_select(self, lst):
        items = lst.selectedItems()
        if items:
            self._sel_locale = items[0].data(Qt.ItemDataRole.UserRole)
            self._update_summary()

    def _on_tz_select(self, lst):
        items = lst.selectedItems()
        if items:
            self._sel_tz = items[0].data(Qt.ItemDataRole.UserRole)
            self._update_summary()

    def _on_kb_select(self, lst):
        items = lst.selectedItems()
        if items:
            self._sel_keymap = items[0].data(Qt.ItemDataRole.UserRole)
            self._update_summary()

    def _select_default(self, lst, value):
        for i in range(lst.count()):
            item = lst.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == value:
                lst.setCurrentItem(item)
                lst.scrollToItem(item)
                break

    def _update_summary(self):
        self.summary.setText(
            f"Locale: {self._sel_locale}   |   "
            f"Timezone: {self._sel_tz}   |   "
            f"Keyboard: {self._sel_keymap}"
        )

    def _on_confirm(self):
        self.confirmed.emit(self._sel_locale, self._sel_tz, self._sel_keymap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = LocaleScreen()
    s.confirmed.connect(lambda l, t, k: print(f"locale={l}  tz={t}  kb={k}"))
    s.show()
    sys.exit(app.exec())
