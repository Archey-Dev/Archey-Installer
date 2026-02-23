#!/usr/bin/env python3
"""
Archey — System setup screen.
Audio, Bluetooth and Printing — choose your stack, Archey handles the rest.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QButtonGroup,
    QRadioButton, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from theme import (MASTER_STYLE, PINK, PINK_DIM, ROSE, BG, BG2, BG3,
                   BORDER, TEXT, TEXT2, TEXT3, GREEN, YELLOW)


# ── Audio stacks ──────────────────────────────────────────────────────────────

AUDIO_OPTIONS = [
    {
        "id":       "pipewire",
        "name":     "PipeWire  (recommended)",
        "desc":     "Modern low-latency audio server. Replaces PulseAudio and JACK. "
                    "Works great with Bluetooth, gaming and pro audio.",
        "packages": [
            "pipewire", "pipewire-alsa", "pipewire-pulse",
            "pipewire-jack", "wireplumber", "alsa-utils",
        ],
        "systemd":  ["pipewire", "pipewire-pulse", "wireplumber"],
        "default":  True,
    },
    {
        "id":       "pulseaudio",
        "name":     "PulseAudio  (legacy)",
        "desc":     "Older but very stable audio server. Good compatibility. "
                    "Choose this if you have hardware that PipeWire struggles with.",
        "packages": [
            "pulseaudio", "pulseaudio-alsa", "pulseaudio-bluetooth",
            "alsa-utils", "pavucontrol",
        ],
        "systemd":  ["pulseaudio"],
        "default":  False,
    },
    {
        "id":       "none",
        "name":     "No audio server",
        "desc":     "ALSA only. Minimal setup — only one app can use audio at a time. "
                    "For advanced users who know what they are doing.",
        "packages": ["alsa-utils"],
        "systemd":  [],
        "default":  False,
    },
]

# ── Bluetooth options ─────────────────────────────────────────────────────────

BLUETOOTH_OPTIONS = [
    {
        "id":       "bluez_blueman",
        "name":     "BlueZ + Blueman  (recommended)",
        "desc":     "BlueZ is the official Linux Bluetooth stack. "
                    "Blueman provides a clean GUI tray applet.",
        "packages": ["bluez", "bluez-utils", "blueman"],
        "systemd":  ["bluetooth"],
        "default":  True,
    },
    {
        "id":       "bluez_only",
        "name":     "BlueZ only  (no GUI)",
        "desc":     "Command-line Bluetooth via bluetoothctl. "
                    "Good if your DE provides its own Bluetooth manager.",
        "packages": ["bluez", "bluez-utils"],
        "systemd":  ["bluetooth"],
        "default":  False,
    },
    {
        "id":       "none",
        "name":     "No Bluetooth",
        "desc":     "Skip Bluetooth entirely.",
        "packages": [],
        "systemd":  [],
        "default":  False,
    },
]

# ── Printing options ──────────────────────────────────────────────────────────

PRINTING_OPTIONS = [
    {
        "id":       "cups_full",
        "name":     "CUPS + drivers  (recommended)",
        "desc":     "Full printing stack with GUI config tool, PDF printing, "
                    "HP and Epson driver support.",
        "packages": [
            "cups", "cups-pdf", "system-config-printer",
            "hplip", "epson-inkjet-printer-escpr",
        ],
        "systemd":  ["cups"],
        "default":  True,
    },
    {
        "id":       "cups_minimal",
        "name":     "CUPS minimal",
        "desc":     "Just CUPS, no extra drivers or GUI tools. "
                    "Install your printer driver manually.",
        "packages": ["cups"],
        "systemd":  ["cups"],
        "default":  False,
    },
    {
        "id":       "none",
        "name":     "No printing",
        "desc":     "Skip printing entirely.",
        "packages": [],
        "systemd":  [],
        "default":  False,
    },
]


# ── Section widget ─────────────────────────────────────────────────────────────

class OptionCard(QFrame):
    """A selectable radio card for one option."""
    selected = pyqtSignal(dict)

    def __init__(self, option: dict, group: QButtonGroup):
        super().__init__()
        self.option = option
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        self.radio = QRadioButton()
        self.radio.setChecked(option["default"])
        self.radio.setStyleSheet(f"""
            QRadioButton::indicator {{
                width: 16px; height: 16px;
                border-radius: 8px;
                border: 2px solid {BORDER};
                background: {BG};
            }}
            QRadioButton::indicator:checked {{
                background: {PINK}; border-color: {PINK};
            }}
        """)
        self.radio.toggled.connect(self._on_toggle)
        group.addButton(self.radio)
        row.addWidget(self.radio)

        text = QVBoxLayout()
        text.setSpacing(3)
        name = QLabel(option["name"])
        name.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT}; background: transparent;")
        desc = QLabel(option["desc"])
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")
        desc.setWordWrap(True)
        pkgs = QLabel(f"Packages: {', '.join(option['packages']) if option['packages'] else 'none'}")
        pkgs.setStyleSheet(f"font-size: 10px; color: {TEXT3}; background: transparent;")
        text.addWidget(name); text.addWidget(desc); text.addWidget(pkgs)
        row.addLayout(text, stretch=1)

    def _on_toggle(self, checked: bool):
        self._active = checked
        self._apply_style()
        if checked:
            self.selected.emit(self.option)

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {PINK_DIM};
                    border: 2px solid {ROSE};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG2};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                }}
                QFrame:hover {{ border-color: {ROSE}; }}
            """)

    def mousePressEvent(self, event):
        self.radio.setChecked(True)


class SectionWidget(QWidget):
    """Groups a title + set of OptionCards with their own radio group."""

    def __init__(self, title: str, icon: str, options: list):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self._selected = next(o for o in options if o["default"])
        self._cards = []

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        hdr = QHBoxLayout()
        tag = QLabel(icon)
        tag.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {PINK}; background: transparent;")
        lbl = QLabel(title)
        lbl.setObjectName("sec")
        hdr.addWidget(tag); hdr.addWidget(lbl); hdr.addStretch()
        v.addLayout(hdr)

        group = QButtonGroup(self)
        for opt in options:
            card = OptionCard(opt, group)
            card.selected.connect(self._on_select)
            if opt["default"]:
                card._active = True
                card._apply_style()
            v.addWidget(card)
            self._cards.append(card)

    def _on_select(self, option: dict):
        self._selected = option
        for card in self._cards:
            card._active = card.option["id"] == option["id"]
            card._apply_style()

    def get_selected(self) -> dict:
        return self._selected


# ── Main screen ───────────────────────────────────────────────────────────────

class SystemScreen(QWidget):
    # Emits (packages_list, systemd_services_list)
    confirmed = pyqtSignal(list, list)
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        t = QLabel("System Setup"); t.setObjectName("title")
        s = QLabel("Choose your audio server, Bluetooth stack and printing setup.")
        s.setObjectName("sub")
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(4)

        # Scrollable sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cv = QVBoxLayout(container)
        cv.setContentsMargins(0, 0, 8, 0)
        cv.setSpacing(20)

        self.audio_section = SectionWidget(
            "AUDIO SERVER", "[AUD]", AUDIO_OPTIONS
        )
        self.bt_section = SectionWidget(
            "BLUETOOTH", "[BT]", BLUETOOTH_OPTIONS
        )
        self.print_section = SectionWidget(
            "PRINTING", "[PRN]", PRINTING_OPTIONS
        )

        cv.addWidget(self.audio_section)
        cv.addWidget(self.bt_section)
        cv.addWidget(self.print_section)
        cv.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        # Summary
        self.summary = QLabel("")
        self.summary.setObjectName("sub")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        self._update_summary()

        # Wire summary updates
        for section in (self.audio_section, self.bt_section, self.print_section):
            for card in section._cards:
                card.radio.toggled.connect(self._update_summary)

        # Buttons
        btn_row = QHBoxLayout()
        self.back_btn = QPushButton("<- Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back.emit)

        self.confirm_btn = QPushButton("Continue ->")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(self.back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        root.addLayout(btn_row)

    def _update_summary(self):
        a = self.audio_section.get_selected()
        b = self.bt_section.get_selected()
        p = self.print_section.get_selected()
        total = len(a["packages"]) + len(b["packages"]) + len(p["packages"])
        self.summary.setText(
            f"Audio: {a['name'].split('(')[0].strip()}  |  "
            f"Bluetooth: {b['name'].split('(')[0].strip()}  |  "
            f"Printing: {p['name'].split('(')[0].strip()}  |  "
            f"{total} package(s)"
        )

    def _on_confirm(self):
        a = self.audio_section.get_selected()
        b = self.bt_section.get_selected()
        p = self.print_section.get_selected()

        packages = []
        services = []
        seen = set()
        for opt in (a, b, p):
            for pkg in opt["packages"]:
                if pkg not in seen:
                    seen.add(pkg)
                    packages.append(pkg)
            services.extend(opt["systemd"])

        self.confirmed.emit(packages, services)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = SystemScreen()
    s.confirmed.connect(lambda pkgs, svcs: print(f"pkgs={pkgs}\nservices={svcs}"))
    s.show()
    sys.exit(app.exec())