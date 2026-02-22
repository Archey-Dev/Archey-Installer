#!/usr/bin/env python3
"""
Archey — Extra packages screen.
Lets the user pick common package groups to install.
"""

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from theme import MASTER_STYLE, PINK, PINK_DIM, ROSE, BG2, BORDER, TEXT, TEXT2, TEXT3, GREEN, YELLOW, RED

# ── Package groups ────────────────────────────────────────────────────────────

GROUPS = [
    {
        "id":       "dev",
        "name":     "Development Tools",
        "icon":     "[DEV]",
        "desc":     "GCC, make, cmake, Python, Node.js, Rust, Go",
        "packages": [
            "gcc", "g++", "make", "cmake", "gdb", "valgrind",
            "python", "python-pip", "nodejs", "npm",
            "rust", "cargo", "go",
            "git", "base-devel",
        ],
        "default": True,
    },
    {
        "id":       "browser",
        "name":     "Web Browser",
        "icon":     "[WEB]",
        "desc":     "Firefox",
        "packages": ["firefox"],
        "default": True,
    },
    {
        "id":       "media",
        "name":     "Media",
        "icon":     "[MED]",
        "desc":     "VLC, mpv, ffmpeg, ImageMagick",
        "packages": ["vlc", "mpv", "ffmpeg", "imagemagick"],
        "default": False,
    },
    {
        "id":       "office",
        "name":     "Office",
        "icon":     "[DOC]",
        "desc":     "LibreOffice Writer, Calc, Impress",
        "packages": ["libreoffice-fresh"],
        "default": False,
    },
    {
        "id":       "fonts",
        "name":     "Extra Fonts",
        "icon":     "[FNT]",
        "desc":     "Noto fonts, TTF Liberation, Fira Code, JetBrains Mono",
        "packages": [
            "noto-fonts", "noto-fonts-emoji", "noto-fonts-cjk",
            "ttf-liberation", "ttf-fira-code", "ttf-jetbrains-mono",
        ],
        "default": True,
    },
    {
        "id":       "audio",
        "name":     "Audio",
        "icon":     "[AUD]",
        "desc":     "PipeWire, PulseAudio compatibility, ALSA utils",
        "packages": [
            "pipewire", "pipewire-pulse", "pipewire-alsa",
            "wireplumber", "alsa-utils",
        ],
        "default": True,
    },
    {
        "id":       "bluetooth",
        "name":     "Bluetooth",
        "icon":     "[BT]",
        "desc":     "BlueZ, Blueman",
        "packages": ["bluez", "bluez-utils", "blueman"],
        "default": False,
    },
    {
        "id":       "printing",
        "name":     "Printing",
        "icon":     "[PRN]",
        "desc":     "CUPS, printer drivers",
        "packages": ["cups", "cups-pdf", "system-config-printer"],
        "default": False,
    },
    {
        "id":       "terminal",
        "name":     "Terminal Tools",
        "icon":     "[TRM]",
        "desc":     "htop, btop, neofetch, tmux, zsh, neovim",
        "packages": [
            "htop", "btop", "neofetch", "tmux",
            "zsh", "zsh-completions", "neovim",
        ],
        "default": True,
    },
    {
        "id":       "gaming",
        "name":     "Gaming",
        "icon":     "[GME]",
        "desc":     "Steam, Wine, gamemode, MangoHud",
        "packages": ["steam", "wine", "gamemode", "mangohud"],
        "default": False,
    },
    {
        "id":       "virt",
        "name":     "Virtualisation",
        "icon":     "[VM]",
        "desc":     "VirtualBox guest additions, QEMU, virt-manager",
        "packages": [
            "virtualbox-guest-utils", "qemu-full", "virt-manager",
            "libvirt", "dnsmasq",
        ],
        "default": False,
    },
    {
        "id":       "security",
        "name":     "Security",
        "icon":     "[SEC]",
        "desc":     "ufw firewall, fail2ban, ClamAV",
        "packages": ["ufw", "fail2ban", "clamav"],
        "default": False,
    },
]


# ── GPU detection ─────────────────────────────────────────────────────────────

GPU_DRIVERS = {
    "nvidia": {
        "id":       "gpu_nvidia",
        "name":     "NVIDIA GPU Drivers",
        "icon":     "[GPU]",
        "desc":     "nvidia, nvidia-utils, nvidia-settings, lib32-nvidia-utils",
        "packages": ["nvidia", "nvidia-utils", "nvidia-settings", "lib32-nvidia-utils"],
        "default":  True,
        "locked":   True,   # auto-detected, shown as recommended
    },
    "amd": {
        "id":       "gpu_amd",
        "name":     "AMD GPU Drivers",
        "icon":     "[GPU]",
        "desc":     "xf86-video-amdgpu, mesa, vulkan-radeon, lib32-mesa",
        "packages": ["xf86-video-amdgpu", "mesa", "vulkan-radeon",
                     "lib32-mesa", "lib32-vulkan-radeon"],
        "default":  True,
        "locked":   True,
    },
    "intel": {
        "id":       "gpu_intel",
        "name":     "Intel GPU Drivers",
        "icon":     "[GPU]",
        "desc":     "xf86-video-intel, mesa, vulkan-intel, lib32-mesa",
        "packages": ["xf86-video-intel", "mesa", "vulkan-intel", "lib32-mesa"],
        "default":  True,
        "locked":   True,
    },
    "vm": {
        "id":       "gpu_vm",
        "name":     "VM / Generic Display",
        "icon":     "[GPU]",
        "desc":     "xf86-video-vesa, mesa (VirtualBox / QEMU / unknown GPU)",
        "packages": ["xf86-video-vesa", "mesa"],
        "default":  True,
        "locked":   True,
    },
}

def detect_gpu() -> tuple[str, dict]:
    """
    Returns (vendor_string, GPU_DRIVERS entry).
    Reads lspci output to identify the GPU vendor.
    Falls back to vm/vesa if nothing recognised.
    """
    try:
        result = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=5
        )
        output = result.stdout.lower()
        # Check for VGA / 3D / Display controller lines
        gpu_lines = [l for l in output.splitlines()
                     if any(k in l for k in ("vga", "3d", "display", "graphics"))]
        combined = " ".join(gpu_lines)

        if "nvidia" in combined:
            return "NVIDIA", GPU_DRIVERS["nvidia"]
        elif "amd" in combined or "radeon" in combined or "advanced micro" in combined:
            return "AMD", GPU_DRIVERS["amd"]
        elif "intel" in combined:
            return "Intel", GPU_DRIVERS["intel"]
        else:
            return "Unknown / VM", GPU_DRIVERS["vm"]
    except Exception:
        return "Unknown / VM", GPU_DRIVERS["vm"]


# ── GPU card (special — auto-detected, pre-checked, non-removable) ────────────

class GPUCard(QFrame):
    def __init__(self, vendor: str, driver: dict):
        super().__init__()
        self.driver = driver
        self._build(vendor)

    def _build(self, vendor: str):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {PINK_DIM};
                border: 2px solid {ROSE};
                border-radius: 10px;
            }}
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        # Lock icon — always installed
        lock = QLabel("[*]")
        lock.setFixedWidth(32)
        lock.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {PINK}; background: transparent;")
        row.addWidget(lock)

        text = QVBoxLayout()
        text.setSpacing(3)

        name = QLabel(f"GPU: {vendor}  —  {self.driver['name']}")
        name.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT}; background: transparent;")

        desc = QLabel(self.driver["desc"])
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")

        auto = QLabel("Auto-detected  |  Will always be installed")
        auto.setStyleSheet(f"font-size: 10px; color: {PINK}; background: transparent;")

        text.addWidget(name)
        text.addWidget(desc)
        text.addWidget(auto)
        row.addLayout(text, stretch=1)

    def get_packages(self):
        return self.driver["packages"]



class GroupCard(QFrame):
    def __init__(self, group: dict):
        super().__init__()
        self.group = group
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG2};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(14)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.group["default"])
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border-radius: 5px;
                border: 2px solid {BORDER};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {PINK};
                border-color: {PINK};
                image: none;
            }}
            QCheckBox::indicator:hover {{ border-color: {ROSE}; }}
        """)
        self.checkbox.stateChanged.connect(self._on_toggle)
        row.addWidget(self.checkbox)

        tag = QLabel(self.group["icon"])
        tag.setFixedWidth(44)
        tag.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {PINK}; background: transparent;")
        row.addWidget(tag)

        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(self.group["name"])
        name.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT}; background: transparent;")
        desc = QLabel(self.group["desc"])
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")
        text.addWidget(name); text.addWidget(desc)
        row.addLayout(text, stretch=1)

        pkgs = QLabel(f"{len(self.group['packages'])} pkg(s)")
        pkgs.setStyleSheet(f"font-size: 10px; color: {TEXT3}; background: transparent;")
        pkgs.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(pkgs)

    def _on_toggle(self):
        if self.checkbox.isChecked():
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {PINK_DIM};
                    border: 1px solid {ROSE};
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
            """)

    def is_checked(self):
        return self.checkbox.isChecked()

    def get_packages(self):
        return self.group["packages"] if self.is_checked() else []


class ExtrasScreen(QWidget):
    confirmed = pyqtSignal(list)   # flat list of extra packages
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._cards = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        t = QLabel("Extra Packages"); t.setObjectName("title")
        s = QLabel("Choose what to install alongside your base system. You can always add more later with pacman.")
        s.setObjectName("sub"); s.setWordWrap(True)
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(4)

        # ── GPU section ────────────────────────────────────────────────────
        gpu_lbl = QLabel("GPU DRIVER  (auto-detected)"); gpu_lbl.setObjectName("sec")
        root.addWidget(gpu_lbl)
        vendor, driver = detect_gpu()
        self._gpu_card = GPUCard(vendor, driver)
        root.addWidget(self._gpu_card)

        pkg_lbl = QLabel("PACKAGES"); pkg_lbl.setObjectName("sec")
        root.addWidget(pkg_lbl)

        # Select all / none buttons
        sel_row = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.setObjectName("secondary")
        sel_all.setFixedWidth(120)
        sel_all.clicked.connect(lambda: self._set_all(True))
        sel_none = QPushButton("Select None")
        sel_none.setObjectName("secondary")
        sel_none.setFixedWidth(120)
        sel_none.clicked.connect(lambda: self._set_all(False))
        sel_row.addWidget(sel_all)
        sel_row.addWidget(sel_none)
        sel_row.addStretch()
        root.addLayout(sel_row)

        # Scrollable card list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(container)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(0, 0, 8, 0)

        for group in GROUPS:
            card = GroupCard(group)
            card._on_toggle()   # apply initial style based on default
            card_layout.addWidget(card)
            self._cards.append(card)

        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        # Package count summary
        self.summary = QLabel("")
        self.summary.setObjectName("sub")
        root.addWidget(self.summary)
        self._update_summary()

        # Connect all checkboxes to summary update
        for card in self._cards:
            card.checkbox.stateChanged.connect(self._update_summary)

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

    def _set_all(self, checked: bool):
        for card in self._cards:
            card.checkbox.setChecked(checked)

    def _update_summary(self):
        pkgs = self._get_packages()
        groups_selected = sum(1 for c in self._cards if c.is_checked())
        self.summary.setText(
            f"{groups_selected} group(s) selected  |  {len(pkgs)} extra package(s) to install"
        )

    def _get_packages(self):
        seen, out = set(), []
        # Always include GPU packages
        for pkg in self._gpu_card.get_packages():
            if pkg not in seen:
                seen.add(pkg)
                out.append(pkg)
        for card in self._cards:
            for pkg in card.get_packages():
                if pkg not in seen:
                    seen.add(pkg)
                    out.append(pkg)
        return out

    def _on_confirm(self):
        self.confirmed.emit(self._get_packages())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = ExtrasScreen()
    s.confirmed.connect(lambda pkgs: print(f"{len(pkgs)} packages: {pkgs[:5]}..."))
    s.show()
    sys.exit(app.exec())
