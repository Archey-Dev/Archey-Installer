#!/usr/bin/env python3
"""
ArchInstall — main entry point.
Dark Rose aesthetic: deep charcoal + hot pink accents.
Animated fade transitions between screens.
"""

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget,
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QScreen, QLinearGradient, QColor, QPainter, QPalette

from theme        import MASTER_STYLE, BG, BG2, BORDER, PINK, PINK2, ROSE, TEXT, TEXT2, TEXT3, fade_transition
from wifi_screen  import WifiScreen
from disk_screen  import DiskScreen
from user_screen  import UserScreen
from de_screen    import DEScreen
from locale_screen import LocaleScreen
from packages_screen  import PackagesScreen
from hardware_screen  import HardwareScreen
from system_screen   import SystemScreen
from advanced_screen import AdvancedScreen
from install_screen import InstallScreen



# ── UEFI check ────────────────────────────────────────────────────────────────

def is_uefi() -> bool:
    """Returns True if system booted in UEFI mode."""
    import os
    return os.path.isdir("/sys/firmware/efi")


class UEFIBlockScreen(QWidget):
    """Shown when system is not UEFI. Offers to exit or continue anyway."""
    proceed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        v = QVBoxLayout(self)
        v.setContentsMargins(80, 0, 80, 0)
        v.setSpacing(16)
        v.addStretch(2)

        glyph = QLabel("⚠")
        glyph.setStyleSheet(f"font-size: 52px; color: {ROSE}; background: transparent;")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(glyph)

        title = QLabel("UEFI Not Detected")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)

        desc = QLabel(
            "Archey requires a UEFI system to install.\n\n"
            "This machine appears to have booted in Legacy BIOS mode. "
            "The installer uses a GPT + EFI partition layout which will not "
            "work on a BIOS/MBR system.\n\n"
            "If you believe this is wrong (e.g. you are in a VM with EFI enabled), "
            "you can continue anyway."
        )
        desc.setObjectName("sub")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(desc)

        v.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        exit_btn = QPushButton("Exit Installer")
        exit_btn.setObjectName("secondary")
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ROSE}, stop:1 {PINK});
                color: #12111a; border: none;
                border-radius: 8px;
                font-size: 14px; font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PINK}, stop:1 {PINK2});
            }}
        """)
        exit_btn.clicked.connect(lambda: QApplication.quit())

        continue_btn = QPushButton("Continue Anyway →")
        continue_btn.setObjectName("primary")
        continue_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ROSE}, stop:1 {PINK});
                color: #12111a; border: none;
                border-radius: 8px;
                font-size: 14px; font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PINK}, stop:1 {PINK2});
            }}
        """)
        continue_btn.clicked.connect(self.proceed.emit)

        btn_row.addStretch()
        btn_row.addWidget(exit_btn)
        btn_row.addWidget(continue_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)
        v.addStretch(3)


# ── Internet check ────────────────────────────────────────────────────────────

class NetCheckWorker(QThread):
    has_internet = pyqtSignal(bool)
    def run(self):
        try:
            r = subprocess.run(["ping","-c","1","-W","2","8.8.8.8"],
                               capture_output=True, timeout=5)
            self.has_internet.emit(r.returncode == 0)
        except Exception:
            self.has_internet.emit(False)


# ── Shared state ──────────────────────────────────────────────────────────────

class InstallState:
    def __init__(self):
        self.wifi_ssid      = ""
        self.locale         = "en_US.UTF-8"
        self.timezone       = "UTC"
        self.keymap         = "us"
        self.user_packages   = []
        self.cpu_packages    = []
        self.gpu_packages    = []
        self.system_packages = []
        self.system_services = []
        self.kernel_choice   = "linux"
        self.advanced_packages = []
        self.disk           = {}
        self.efi_partition  = {}
        self.arch_size_gb   = 40.0
        self.install_mode   = "dualboot"
        self.hostname       = ""
        self.username       = ""
        self.password       = ""
        self.de             = {}
        self.root_partition = ""
        self.efi_mount      = ""


# ── Sidebar ───────────────────────────────────────────────────────────────────

STEPS = ["Welcome", "Language", "Wi-Fi", "Disk Setup",
         "User Setup", "Desktop", "Hardware", "Packages", "Advanced", "System", "Install", "Done"]

class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a1228, stop:0.5 {BG2}, stop:1 #1a1228);
                border-right: 1px solid {BORDER};
            }}
        """)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 40, 20, 32)
        v.setSpacing(2)

        # Logo
        logo_row = QHBoxLayout()
        dot = QLabel("✦")
        dot.setStyleSheet(f"font-size: 18px; color: {PINK}; background: transparent;")
        name = QLabel("Archey")
        name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT}; background: transparent; letter-spacing: 1px;")
        logo_row.addWidget(dot)
        logo_row.addWidget(name)
        logo_row.addStretch()
        v.addLayout(logo_row)
        v.addSpacing(32)

        self._labels = []
        for i, step in enumerate(STEPS):
            lbl = QLabel(f"  {step}")
            lbl.setStyleSheet(f"font-size: 12px; color: {TEXT3}; padding: 8px 8px; border-radius: 7px; background: transparent;")
            v.addWidget(lbl)
            self._labels.append(lbl)

        v.addStretch()

        # Decorative bottom
        ver = QLabel("v0.1.0")
        ver.setStyleSheet(f"font-size: 10px; color: {BORDER}; background: transparent; letter-spacing: 2px;")
        v.addWidget(ver)

    def set_step(self, index: int):
        for i, lbl in enumerate(self._labels):
            if i == index:
                lbl.setStyleSheet(
                    f"font-size: 12px; font-weight: bold; color: {PINK};"
                    f"background-color: #2d1a24; padding: 8px 8px;"
                    f"border-radius: 7px; border-left: 3px solid {PINK};"
                )
            elif i < index:
                lbl.setStyleSheet(
                    f"font-size: 12px; color: {TEXT2}; padding: 8px 8px;"
                    f"border-radius: 7px; background: transparent;"
                    f"border-left: 3px solid #3d2a34;"
                )
            else:
                lbl.setStyleSheet(
                    f"font-size: 12px; color: {TEXT3}; padding: 8px 8px;"
                    f"border-radius: 7px; background: transparent;"
                )


# ── Welcome screen ────────────────────────────────────────────────────────────

class WelcomeScreen(QWidget):
    proceed = pyqtSignal()

    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(20)
        v.setContentsMargins(80, 80, 80, 80)

        # Big decorative glyph
        glyph = QLabel("✦")
        glyph.setStyleSheet(f"font-size: 52px; color: {PINK}; background: transparent;")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Archey")
        title.setStyleSheet(
            f"font-size: 42px; font-weight: bold; color: {TEXT};"
            f"letter-spacing: 4px; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("a friendlier arch linux installer")
        tagline.setStyleSheet(f"font-size: 14px; color: {PINK}; letter-spacing: 3px; background: transparent;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 transparent, stop:0.5 {ROSE}, stop:1 transparent);")

        warn = QLabel("⚠  This installer will modify your disk partitions.\nBack up important data before continuing.")
        warn.setStyleSheet(
            f"font-size: 13px; color: {TEXT2};"
            f"background-color: #1f1520; border: 1px solid #3d2535;"
            f"border-left: 3px solid {ROSE};"
            f"border-radius: 8px; padding: 16px 20px;"
        )
        warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warn.setWordWrap(True)

        btn = QPushButton("Get Started →")
        btn.setFixedWidth(220)
        btn.setFixedHeight(44)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ROSE}, stop:1 {PINK});
                color: #12111a; border: none;
                border-radius: 8px;
                font-size: 14px; font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PINK}, stop:1 {PINK2});
            }}
        """)
        btn.clicked.connect(self.proceed.emit)

        v.addWidget(glyph)
        v.addWidget(title)
        v.addWidget(tagline)
        v.addSpacing(8)
        v.addWidget(div)
        v.addSpacing(8)
        v.addWidget(warn)
        v.addSpacing(16)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ── Done screen ───────────────────────────────────────────────────────────────

class DoneScreen(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(20)
        v.setContentsMargins(80, 80, 80, 80)

        glyph = QLabel("Archey\n✦")
        glyph.setStyleSheet(f"font-size: 64px; color: {PINK}; background: transparent;")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Installation Complete")
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {TEXT}; letter-spacing: 2px; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Arch Linux has been installed successfully.\nRemove the USB drive and reboot to start using your system.")
        sub.setStyleSheet(f"font-size: 14px; color: {TEXT2}; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        btn = QPushButton("Reboot Now")
        btn.setObjectName("primary")
        btn.setFixedWidth(200)
        btn.setFixedHeight(44)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ROSE}, stop:1 {PINK});
                color: #12111a; border: none;
                border-radius: 8px;
                font-size: 14px; font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PINK}, stop:1 {PINK2});
            }}
        """)
        btn.clicked.connect(lambda: subprocess.run(["reboot"]))

        v.addWidget(glyph)
        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(16)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = InstallState()
        self._already_online = False
        self.setWindowTitle("Archey")
        self.setStyleSheet(MASTER_STYLE)
        self._build_ui()
        self._goto(1)

        self._net = NetCheckWorker()
        self._net.has_internet.connect(lambda online: setattr(self, '_already_online', online))
        self._net.start()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar()
        row.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        row.addWidget(self.stack, stretch=1)

        # -1 — UEFI block (shown before welcome if needed, then removed)
        self.uefi_block = UEFIBlockScreen()
        self.uefi_block.proceed.connect(self._on_uefi_proceed)
        self.stack.addWidget(self.uefi_block)

        # 0 — Welcome (index 1 if UEFI block shown, but _real_offset handles this)
        self.welcome = WelcomeScreen()
        self.welcome.proceed.connect(self._after_welcome)
        self.stack.addWidget(self.welcome)

        # 1 — Language / Timezone
        self.locale = LocaleScreen()
        self.locale.confirmed.connect(self._on_locale_confirmed)
        self.locale.back.connect(lambda: self._goto(1))
        self.stack.addWidget(self.locale)

        # 2 — Wi-Fi
        self.wifi = WifiScreen()
        self.wifi.connected.connect(self._on_wifi_connected)
        self.stack.addWidget(self.wifi)

        # 3 — Disk
        self.disk = DiskScreen()
        self.disk.confirmed.connect(self._on_disk_confirmed)
        self.disk.back.connect(lambda: self._goto(3))
        self.stack.addWidget(self.disk)

        # 4 — User
        self.user = UserScreen()
        self.user.confirmed.connect(self._on_user_confirmed)
        self.user.back.connect(lambda: self._goto(4))
        self.stack.addWidget(self.user)

        # 5 — Desktop
        self.de = DEScreen()
        self.de.confirmed.connect(self._on_de_confirmed)
        self.de.back.connect(lambda: self._goto(5))
        self.stack.addWidget(self.de)

        # 6 — Hardware (CPU + GPU)
        self.hardware = HardwareScreen()
        self.hardware.confirmed.connect(self._on_hardware_confirmed)
        self.hardware.back.connect(lambda: self._goto(6))
        self.stack.addWidget(self.hardware)

        # 7 — Package search
        self.packages = PackagesScreen()
        self.packages.confirmed.connect(self._on_packages_confirmed)
        self.packages.back.connect(lambda: self._goto(7))
        self.stack.addWidget(self.packages)

        # 8 — Advanced options (kernel + optional extras)
        self.advanced = AdvancedScreen()
        self.advanced.confirmed.connect(self._on_advanced_confirmed)
        self.advanced.back.connect(lambda: self._goto(8))
        self.stack.addWidget(self.advanced)

        # 9 — System setup (audio / bluetooth / printing)
        self.system = SystemScreen()
        self.system.confirmed.connect(self._on_system_confirmed)
        self.system.back.connect(lambda: self._goto(9))
        self.stack.addWidget(self.system)

        # 10 — Install
        self.install_screen = InstallScreen()
        self.install_screen.finished.connect(lambda: self._goto(12))
        self.stack.addWidget(self.install_screen)

        # 11 — Done
        self.done = DoneScreen()
        self.stack.addWidget(self.done)

    # ── Navigation with fade ──────────────────────────────────────────────────

    def _goto(self, index: int):
        old = self.stack.currentWidget()
        self.stack.setCurrentIndex(index)
        new = self.stack.currentWidget()
        if old and old is not new:
            fade_transition(old, new, duration=200)
        self.sidebar.set_step(max(0, index - 1))  # offset for uefi block at index 0

    # ── Flow logic ────────────────────────────────────────────────────────────

    def _after_welcome(self):
        self._goto(2)   # locale

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_uefi_proceed(self):
        """Called when UEFI check passes or user overrides."""
        self.sidebar.setVisible(True)
        self.stack.setCurrentIndex(1)   # Welcome is index 1 (0 = uefi block)
        self.sidebar.set_step(0)

    def _on_wifi_connected(self):
        self._presync_db()
        self._goto(4)

    def _presync_db(self):
        """Init keyring, refresh mirrors, then sync pacman db."""
        try:
            subprocess.Popen(
                ["/bin/sh", "-c",
                 "pacman-key --init"
                 " && pacman-key --populate archlinux"
                 " && reflector --latest 20 --sort rate --save /etc/pacman.d/mirrorlist"
                 " && pacman -Sy --noconfirm"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass   # non-fatal — packages screen will retry

    def _on_locale_confirmed(self, locale: str, tz: str, keymap: str):
        self.state.locale   = locale
        self.state.timezone = tz
        self.state.keymap   = keymap
        # Skip Wi-Fi if already online — pre-sync db immediately
        if self._already_online:
            self._presync_db()
            self._goto(4)
        else:
            self._goto(3)

    def _on_disk_confirmed(self, disk, efi, gb, mode):
        self.state.disk         = disk
        self.state.efi_partition = efi
        self.state.arch_size_gb = gb
        self.state.install_mode = mode
        self._goto(5)

    def _on_user_confirmed(self, hostname, username, password):
        self.state.hostname = hostname
        self.state.username = username
        self.state.password = password
        self._goto(6)

    def _on_de_confirmed(self, de):
        self.state.de = de
        self._goto(7)

    def _on_hardware_confirmed(self, cpu_pkgs: list, gpu_pkgs: list):
        self.state.cpu_packages = cpu_pkgs
        self.state.gpu_packages = gpu_pkgs
        self._goto(8)

    def _on_packages_confirmed(self, packages: list):
        self.state.user_packages = packages
        self._goto(9)

    def _on_advanced_confirmed(self, kernel_choice: str, extra_packages: list):
        self.state.kernel_choice = kernel_choice
        self.state.advanced_packages = extra_packages
        self._goto(10)

    def _on_system_confirmed(self, packages: list, services: list):
        self.state.system_packages = packages
        self.state.system_services = services
        self._goto(11)
        self.install_screen.start(self.state)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("IBM Plex Mono", 13))
    window = MainWindow()
    # Force fullscreen — works inside VirtualBox and on real hardware
    screen = app.primaryScreen().geometry()
    window.setGeometry(screen)
    window.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.FramelessWindowHint
    )
    window.showFullScreen()
    sys.exit(app.exec())
