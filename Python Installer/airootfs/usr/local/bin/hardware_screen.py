#!/usr/bin/env python3
"""
Archey — Hardware detection screen.
Two sub-pages: CPU then GPU. Shows detected hardware, lets user override.
"""

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QRadioButton, QButtonGroup, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from theme import (MASTER_STYLE, PINK, PINK_DIM, ROSE, BG, BG2, BG3,
                   BORDER, TEXT, TEXT2, TEXT3, GREEN, YELLOW, RED)


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_cpu() -> tuple[str, str]:
    """Returns (vendor, display_name)."""
    try:
        with open("/proc/cpuinfo") as f:
            info = f.read()
        for line in info.splitlines():
            if line.startswith("model name"):
                name = line.split(":", 1)[1].strip()
                vendor = "intel" if "intel" in name.lower() else \
                         "amd"   if "amd"   in name.lower() else "unknown"
                return vendor, name
    except Exception:
        pass
    return "unknown", "Unknown CPU"

def detect_gpu() -> tuple[str, str]:
    """Returns (vendor, display_name)."""
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            l = line.lower()
            if any(k in l for k in ("vga", "3d", "display", "graphics")):
                name = line.split(":", 2)[-1].strip()
                vendor = "nvidia" if "nvidia" in l else \
                         "amd"    if ("amd" in l or "radeon" in l or "advanced micro" in l) else \
                         "intel"  if "intel" in l else "vm"
                return vendor, name
    except Exception:
        pass
    return "vm", "Unknown / VM GPU"


# ── CPU options ───────────────────────────────────────────────────────────────

CPU_OPTIONS = [
    {
        "id":       "intel",
        "name":     "Intel",
        "desc":     "Installs intel-ucode microcode updates.",
        "packages": ["intel-ucode"],
    },
    {
        "id":       "amd",
        "name":     "AMD",
        "desc":     "Installs amd-ucode microcode updates.",
        "packages": ["amd-ucode"],
    },
    {
        "id":       "unknown",
        "name":     "Other / Skip",
        "desc":     "No microcode package will be installed.",
        "packages": [],
    },
]

GPU_OPTIONS = [
    {
        "id":       "nvidia",
        "name":     "NVIDIA",
        "desc":     "nvidia, nvidia-utils, nvidia-settings, lib32-nvidia-utils",
        "packages": ["nvidia", "nvidia-utils", "nvidia-settings", "lib32-nvidia-utils"],
    },
    {
        "id":       "amd",
        "name":     "AMD / ATI",
        "desc":     "xf86-video-amdgpu, mesa, vulkan-radeon, lib32-mesa",
        "packages": ["xf86-video-amdgpu", "mesa", "vulkan-radeon",
                     "lib32-mesa", "lib32-vulkan-radeon"],
    },
    {
        "id":       "intel",
        "name":     "Intel",
        "desc":     "xf86-video-intel, mesa, vulkan-intel, lib32-mesa",
        "packages": ["xf86-video-intel", "mesa", "vulkan-intel", "lib32-mesa"],
    },
    {
        "id":       "vm",
        "name":     "VM / Generic",
        "desc":     "xf86-video-vesa, mesa — for VirtualBox, QEMU or unknown GPU",
        "packages": ["xf86-video-vesa", "mesa"],
    },
]


# ── Shared option card ────────────────────────────────────────────────────────

class OptionCard(QFrame):
    chosen = pyqtSignal(dict)

    def __init__(self, option: dict, group: QButtonGroup, detected: bool = False):
        super().__init__()
        self.option   = option
        self._active  = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        self.radio = QRadioButton()
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

        name_row = QHBoxLayout()
        name = QLabel(option["name"])
        name.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT}; background: transparent;")
        name_row.addWidget(name)
        if detected:
            badge = QLabel(" ✦ detected ")
            badge.setStyleSheet(f"""
                font-size: 10px; color: {PINK};
                background: {PINK_DIM};
                border-radius: 4px; padding: 1px 6px;
            """)
            name_row.addWidget(badge)
        name_row.addStretch()
        text.addLayout(name_row)

        desc = QLabel(option["desc"])
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT2}; background: transparent;")
        desc.setWordWrap(True)
        text.addWidget(desc)

        row.addLayout(text, stretch=1)

    def _on_toggle(self, checked: bool):
        self._active = checked
        self._apply_style()
        if checked:
            self.chosen.emit(self.option)

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {PINK_DIM};
                    border: 2px solid {ROSE};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {BG2};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                }}
                QFrame:hover {{ border-color: {ROSE}; }}
            """)

    def mousePressEvent(self, event):
        self.radio.setChecked(True)

    def set_checked(self, checked: bool):
        self.radio.setChecked(checked)


# ── CPU sub-page ──────────────────────────────────────────────────────────────

class CPUPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self._selected = None
        self._cards    = []
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        # Detection banner
        vendor, name = detect_cpu()
        self._selected = next((o for o in CPU_OPTIONS if o["id"] == vendor), CPU_OPTIONS[2])

        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-left: 3px solid {PINK};
                border-radius: 10px;
            }}
        """)
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        detected_lbl = QLabel("⚙  Detected CPU")
        detected_lbl.setStyleSheet(f"font-size: 11px; color: {PINK}; font-weight: bold; background: transparent;")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT}; background: transparent;")
        name_lbl.setWordWrap(True)
        bl.addWidget(detected_lbl)
        bl.addWidget(name_lbl)
        v.addWidget(banner)

        lbl = QLabel("MICROCODE")
        lbl.setObjectName("sec")
        v.addWidget(lbl)

        hint = QLabel("Microcode updates fix CPU bugs and security issues. Select your CPU vendor.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        group = QButtonGroup(self)
        for opt in CPU_OPTIONS:
            is_detected = opt["id"] == vendor
            card = OptionCard(opt, group, detected=is_detected)
            card.chosen.connect(self._on_choose)
            if is_detected:
                card.set_checked(True)
            v.addWidget(card)
            self._cards.append(card)

    def _on_choose(self, option: dict):
        self._selected = option

    def get_selected(self) -> dict:
        return self._selected


# ── GPU sub-page ──────────────────────────────────────────────────────────────

class GPUPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self._selected = None
        self._cards    = []
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        vendor, name = detect_gpu()
        self._selected = next((o for o in GPU_OPTIONS if o["id"] == vendor), GPU_OPTIONS[3])

        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-left: 3px solid {PINK};
                border-radius: 10px;
            }}
        """)
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        detected_lbl = QLabel("◈  Detected GPU")
        detected_lbl.setStyleSheet(f"font-size: 11px; color: {PINK}; font-weight: bold; background: transparent;")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: 13px; color: {TEXT}; background: transparent;")
        name_lbl.setWordWrap(True)
        bl.addWidget(detected_lbl)
        bl.addWidget(name_lbl)
        v.addWidget(banner)

        lbl = QLabel("DRIVER")
        lbl.setObjectName("sec")
        v.addWidget(lbl)

        hint = QLabel("If the detected driver looks wrong, pick the correct one below.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)

        group = QButtonGroup(self)
        for opt in GPU_OPTIONS:
            is_detected = opt["id"] == vendor
            card = OptionCard(opt, group, detected=is_detected)
            card.chosen.connect(self._on_choose)
            if is_detected:
                card.set_checked(True)
            v.addWidget(card)
            self._cards.append(card)

    def _on_choose(self, option: dict):
        self._selected = option

    def get_selected(self) -> dict:
        return self._selected


# ── Main screen (CPU → GPU) ───────────────────────────────────────────────────

class HardwareScreen(QWidget):
    # Emits (cpu_packages, gpu_packages)
    confirmed = pyqtSignal(list, list)
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._page = 0   # 0 = CPU, 1 = GPU
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        # Header
        self.title = QLabel("CPU")
        self.title.setObjectName("title")
        self.subtitle = QLabel("Confirm your processor for microcode installation.")
        self.subtitle.setObjectName("sub")
        root.addWidget(self.title)
        root.addWidget(self.subtitle)
        root.addSpacing(4)

        # Page indicator
        ind_row = QHBoxLayout()
        self.ind_cpu = self._make_indicator("CPU", True)
        self.ind_gpu = self._make_indicator("GPU", False)
        ind_row.addStretch()
        ind_row.addWidget(self.ind_cpu)
        ind_row.addSpacing(8)
        ind_row.addWidget(self.ind_gpu)
        ind_row.addStretch()
        root.addLayout(ind_row)

        # Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        scroll_cpu = self._wrap_scroll(CPUPage())
        scroll_gpu = self._wrap_scroll(GPUPage())

        self._cpu_page = scroll_cpu.widget()
        self._gpu_page = scroll_gpu.widget()

        self.stack.addWidget(scroll_cpu)
        self.stack.addWidget(scroll_gpu)
        root.addWidget(self.stack, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self._on_back)

        self.next_btn = QPushButton("Next: GPU →")
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._on_next)

        btn_row.addWidget(self.back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.next_btn)
        root.addLayout(btn_row)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        return scroll

    def _make_indicator(self, text: str, active: bool) -> QLabel:
        lbl = QLabel(text)
        if active:
            lbl.setStyleSheet(f"""
                font-size: 11px; font-weight: bold;
                color: {PINK}; background: {PINK_DIM};
                border-radius: 6px; padding: 3px 12px;
            """)
        else:
            lbl.setStyleSheet(f"""
                font-size: 11px; color: {TEXT3};
                background: {BG2}; border-radius: 6px;
                padding: 3px 12px;
            """)
        return lbl

    def _set_page(self, page: int):
        self._page = page
        self.stack.setCurrentIndex(page)
        if page == 0:
            self.title.setText("CPU")
            self.subtitle.setText("Confirm your processor for microcode installation.")
            self.next_btn.setText("Next: GPU →")
            self.ind_cpu.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {PINK}; background: {PINK_DIM}; border-radius: 6px; padding: 3px 12px;")
            self.ind_gpu.setStyleSheet(f"font-size: 11px; color: {TEXT3}; background: {BG2}; border-radius: 6px; padding: 3px 12px;")
        else:
            self.title.setText("GPU")
            self.subtitle.setText("Confirm your graphics card for driver installation.")
            self.next_btn.setText("Continue →")
            self.ind_cpu.setStyleSheet(f"font-size: 11px; color: {TEXT3}; background: {BG2}; border-radius: 6px; padding: 3px 12px;")
            self.ind_gpu.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {PINK}; background: {PINK_DIM}; border-radius: 6px; padding: 3px 12px;")

    def _on_back(self):
        if self._page == 1:
            self._set_page(0)
        else:
            self.back.emit()

    def _on_next(self):
        if self._page == 0:
            self._set_page(1)
        else:
            cpu = self._cpu_page.get_selected()
            gpu = self._gpu_page.get_selected()
            self.confirmed.emit(cpu["packages"], gpu["packages"])


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    s = HardwareScreen()
    s.confirmed.connect(lambda cpu, gpu: print(f"CPU: {cpu}\nGPU: {gpu}"))
    s.show()
    sys.exit(app.exec())