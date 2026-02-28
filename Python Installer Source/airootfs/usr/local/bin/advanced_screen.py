#!/usr/bin/env python3
"""
Archey — Advanced options screen.
Kernel selection + optional extra package groups.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QButtonGroup,
    QRadioButton, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from theme import (MASTER_STYLE, PINK, PINK_DIM, ROSE, BG, BG2,
                   BORDER, TEXT, TEXT2, TEXT3)

KERNEL_OPTIONS = [
    {
        "id": "linux",
        "name": "Linux (default)",
        "desc": "Balanced and most widely supported Arch kernel.",
        "packages": ["linux", "linux-headers"],
        "default": True,
    },
    {
        "id": "linux-zen",
        "name": "Linux Zen",
        "desc": "Performance-tuned kernel for desktop responsiveness.",
        "packages": ["linux-zen", "linux-zen-headers"],
        "default": False,
    },
    {
        "id": "linux-hardened",
        "name": "Linux Hardened",
        "desc": "Security-focused kernel with additional hardening.",
        "packages": ["linux-hardened", "linux-hardened-headers"],
        "default": False,
    },
    {
        "id": "linux-lts",
        "name": "Linux LTS",
        "desc": "Long-term support kernel for maximum stability.",
        "packages": ["linux-lts", "linux-lts-headers"],
        "default": False,
    },
]

OPTIONAL_GROUPS = [
    {
        "id": "flatpak",
        "name": "Flatpak",
        "desc": "Universal app runtime and package manager.",
        "packages": ["flatpak"],
        "default": False,
    },
    {
        "id": "snapper",
        "name": "Snapper",
        "desc": "Snapshot tooling (useful with btrfs setups).",
        "packages": ["snapper"],
        "default": False,
    },
    {
        "id": "network_tools",
        "name": "Network tools",
        "desc": "Useful diagnostics (nmap, tcpdump, traceroute, whois).",
        "packages": ["nmap", "tcpdump", "traceroute", "whois"],
        "default": False,
    },
]


class KernelCard(QFrame):
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
        pkgs = QLabel(f"Packages: {', '.join(option['packages'])}")
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


class AdvancedScreen(QWidget):
    confirmed = pyqtSignal(str, list)
    back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._selected_kernel = next(o for o in KERNEL_OPTIONS if o["default"])
        self._checks = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        title = QLabel("Advanced Options")
        title.setObjectName("title")
        sub = QLabel("Pick your kernel and optional extras.")
        sub.setObjectName("sub")
        root.addWidget(title)
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 6, 0, 6)
        v.setSpacing(8)

        sec1 = QLabel("KERNEL")
        sec1.setObjectName("sec")
        v.addWidget(sec1)

        group = QButtonGroup(self)
        for opt in KERNEL_OPTIONS:
            c = KernelCard(opt, group)
            c.selected.connect(lambda o, self=self: setattr(self, "_selected_kernel", o))
            v.addWidget(c)

        sec2 = QLabel("OPTIONAL EXTRAS")
        sec2.setObjectName("sec")
        v.addWidget(sec2)

        for grp in OPTIONAL_GROUPS:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG2};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                }}
            """)
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            row.setSpacing(10)

            chk = QCheckBox()
            chk.setChecked(grp["default"])
            chk.setStyleSheet(f"""
                QCheckBox::indicator {{
                    width: 16px; height: 16px;
                    border-radius: 3px;
                    border: 2px solid {BORDER};
                    background: {BG};
                }}
                QCheckBox::indicator:checked {{
                    background: {PINK}; border-color: {PINK};
                }}
            """)
            row.addWidget(chk)

            txt = QVBoxLayout()
            name = QLabel(grp["name"])
            name.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT}; background: transparent;")
            desc = QLabel(grp["desc"])
            desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")
            desc.setWordWrap(True)
            pkgs = QLabel(f"Packages: {', '.join(grp['packages'])}")
            pkgs.setStyleSheet(f"font-size: 10px; color: {TEXT3}; background: transparent;")
            txt.addWidget(name); txt.addWidget(desc); txt.addWidget(pkgs)
            row.addLayout(txt, stretch=1)

            self._checks[grp["id"]] = (chk, grp["packages"])
            v.addWidget(card)

        v.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        btns = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("secondary")
        back_btn.clicked.connect(self.back.emit)

        cont_btn = QPushButton("Continue →")
        cont_btn.setObjectName("primary")
        cont_btn.clicked.connect(self._on_confirm)

        btns.addWidget(back_btn)
        btns.addStretch()
        btns.addWidget(cont_btn)
        root.addLayout(btns)

    def _on_confirm(self):
        extra = []
        for _, (chk, pkgs) in self._checks.items():
            if chk.isChecked():
                extra.extend(pkgs)
        self.confirmed.emit(self._selected_kernel["id"], extra)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AdvancedScreen()
    w.show()
    sys.exit(app.exec())
