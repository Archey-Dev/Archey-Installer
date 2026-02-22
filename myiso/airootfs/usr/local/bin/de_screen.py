#!/usr/bin/env python3
"""
Archey — Desktop environment picker.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from theme import MASTER_STYLE, PINK, PINK2, PINK_DIM, ROSE, BG2, BORDER, TEXT, TEXT2, TEXT3

DES = [
    {"id": "gnome",    "name": "GNOME",         "icon": "◯",
     "desc": "Clean, modern, touch-friendly. The most polished experience.",
     "packages": ["gnome", "gnome-extra", "gdm"], "dm": "gdm",
     "ram": "~800 MB", "style": "Modern / Minimal"},
    {"id": "kde",      "name": "KDE Plasma",    "icon": "❖",
     "desc": "Highly customisable, Windows-like layout. Great for power users.",
     "packages": ["plasma", "kde-applications", "sddm"], "dm": "sddm",
     "ram": "~600 MB", "style": "Customisable / Feature-rich"},
    {"id": "xfce",     "name": "XFCE",          "icon": "⚙",
     "desc": "Lightweight and fast. Great for older hardware.",
     "packages": ["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"], "dm": "lightdm",
     "ram": "~300 MB", "style": "Lightweight / Classic"},
    {"id": "cinnamon", "name": "Cinnamon",       "icon": "✽",
     "desc": "Traditional desktop, very familiar for Windows users.",
     "packages": ["cinnamon", "lightdm", "lightdm-gtk-greeter"], "dm": "lightdm",
     "ram": "~500 MB", "style": "Traditional / Familiar"},
    {"id": "mate",     "name": "MATE",           "icon": "☘",
     "desc": "Classic GNOME 2 style. Stable and lightweight.",
     "packages": ["mate", "mate-extra", "lightdm", "lightdm-gtk-greeter"], "dm": "lightdm",
     "ram": "~350 MB", "style": "Classic / Stable"},
    {"id": "i3",       "name": "i3 (Tiling WM)", "icon": "⌗",
     "desc": "Keyboard-driven tiling window manager. Minimal, fast, no frills.",
     "packages": ["i3-wm", "i3status", "dmenu", "xterm", "lightdm", "lightdm-gtk-greeter"], "dm": "lightdm",
     "ram": "~100 MB", "style": "Minimal / Keyboard-driven"},
    {"id": "none",     "name": "No Desktop",     "icon": "▣",
     "desc": "Install base system only. Configure everything yourself.",
     "packages": [], "dm": "",
     "ram": "~50 MB",  "style": "Bare / DIY"},
]


class DECard(QFrame):
    selected = pyqtSignal(dict)

    def __init__(self, de):
        super().__init__()
        self.de = de
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet("""
            QFrame {
                background: #3d1f2d;
                border-radius: 10px;
                border: 1px solid #2e2b3d;
            }
        """)
        icon_lbl = QLabel(de["icon"])
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 20px; color: #ff6b9d; background: transparent; border: none;")
        icon_inner = QVBoxLayout(icon_box)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_inner.addWidget(icon_lbl)
        layout.addWidget(icon_box)

        text = QVBoxLayout()
        text.setSpacing(3)
        name = QLabel(de["name"])
        name.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT}; background: transparent;")
        desc = QLabel(de["desc"])
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")
        desc.setWordWrap(True)
        text.addWidget(name); text.addWidget(desc)
        layout.addLayout(text, stretch=1)

        tags = QVBoxLayout()
        tags.setSpacing(2)
        tags.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        style_lbl = QLabel(de["style"])
        style_lbl.setStyleSheet(f"font-size: 10px; color: {PINK}; background: transparent;")
        style_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        ram_lbl = QLabel(f"RAM: {de['ram']}")
        ram_lbl.setStyleSheet(f"font-size: 10px; color: {TEXT3}; background: transparent;")
        ram_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        tags.addWidget(style_lbl); tags.addWidget(ram_lbl)
        layout.addLayout(tags)

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {PINK_DIM};
                    border: 2px solid {PINK};
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

    def set_active(self, active):
        self._active = active
        self._apply_style()

    def mousePressEvent(self, event):
        self.selected.emit(self.de)


class DEScreen(QWidget):
    confirmed = pyqtSignal(dict)
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.selected_de = DES[0]
        self._cards = []
        self.setStyleSheet(MASTER_STYLE)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        t = QLabel("Desktop Environment"); t.setObjectName("title")
        s = QLabel("Choose what your desktop will look like after installation.")
        s.setObjectName("sub")
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        card_container = QWidget()
        card_container.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(card_container)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(0, 0, 8, 0)

        for de in DES:
            card = DECard(de)
            card.selected.connect(self._on_card_select)
            card_layout.addWidget(card)
            self._cards.append(card)

        scroll.setWidget(card_container)
        root.addWidget(scroll, stretch=1)

        self.summary = QLabel("")
        self.summary.setObjectName("sub")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)

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

        self._on_card_select(DES[0])

    def _on_card_select(self, de):
        self.selected_de = de
        for card in self._cards:
            card.set_active(card.de["id"] == de["id"])
        pkgs = ", ".join(de["packages"]) if de["packages"] else "none"
        self.summary.setText(
            f"Selected: {de['name']}  |  Display manager: {de['dm'] or 'none'}  |  Packages: {pkgs}"
        )

    def _on_confirm(self):
        self.confirmed.emit(self.selected_de)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = DEScreen()
    s.confirmed.connect(lambda de: print(f"DE: {de['name']}"))
    s.show()
    sys.exit(app.exec())
