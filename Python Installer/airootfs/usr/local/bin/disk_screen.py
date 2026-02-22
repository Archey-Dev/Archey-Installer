#!/usr/bin/env python3
"""
Disk partitioning screen for Arch Linux GUI installer.
Supports three modes:
  - Dualboot with Windows (shrink NTFS)
  - Use free/unallocated space
  - Wipe entire disk
Requires: PyQt6, parted, lsblk
"""

import subprocess
import json
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QSlider, QFrame, QMessageBox, QButtonGroup, QRadioButton,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from theme import MASTER_STYLE, BG, BG2, BG3, BORDER, PINK, PINK2, ROSE, TEXT, TEXT2, TEXT3, GREEN, YELLOW, RED, PINK_DIM
from PyQt6.QtWidgets import QAbstractItemView


# ── Install modes ─────────────────────────────────────────────────────────────

MODE_DUALBOOT  = "dualboot"   # shrink Windows NTFS
MODE_FREESPACE = "freespace"  # use existing unallocated space
MODE_WIPE      = "wipe"       # erase entire disk


# ── Disk probe worker ─────────────────────────────────────────────────────────

class DiskProbeWorker(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-b", "-o",
                 "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL,MODEL"],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(result.stdout)
            disks = []
            for dev in data.get("blockdevices", []):
                if dev.get("type") != "disk":
                    continue
                disk = {
                    "name":       dev["name"],
                    "size":       int(dev.get("size") or 0),
                    "model":      dev.get("model") or "Unknown",
                    "partitions": []
                }
                for part in dev.get("children", []):
                    disk["partitions"].append({
                        "name":       part["name"],
                        "size":       int(part.get("size") or 0),
                        "fstype":     part.get("fstype") or "",
                        "label":      part.get("label") or "",
                        "mountpoint": part.get("mountpoint") or "",
                    })
                disks.append(disk)
            self.results_ready.emit(disks)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ── Partition bar visualizer ──────────────────────────────────────────────────

from theme import MASTER_STYLE, BG, BG2, BG3, BORDER, PINK, PINK2, ROSE, TEXT, TEXT2, TEXT3, GREEN, YELLOW, RED, PINK_DIM

PART_COLORS = {
    "efi":   QColor("#f5c97a"),   # warm gold
    "ntfs":  QColor("#ff6b9d"),   # pink (Windows)
    "arch":  QColor("#e8557a"),   # rose (Arch)
    "free":  QColor("#2a2535"),   # dark free space
    "other": QColor("#4a3f5c"),   # muted other
}

class PartitionBar(QFrame):
    def __init__(self):
        super().__init__()
        self.segments: list[tuple[int, QColor, str]] = []
        self.setFixedHeight(52)
        self.setMinimumWidth(400)

    def set_segments(self, segments: list[tuple[int, QColor, str]]):
        self.segments = segments
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.setBrush(QColor(BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)

        total = sum(s[0] for s in self.segments)
        if not total:
            painter.end()
            return

        painter.setFont(QFont("JetBrains Mono", 8))
        x = 0
        for i, (size, color, tag) in enumerate(self.segments):
            seg_w = int((size / total) * w)
            # last segment fills remaining pixels
            if i == len(self.segments) - 1:
                seg_w = w - x
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x, 0, seg_w, h)
            if seg_w > 32:
                painter.setPen(QColor(BG))
                painter.drawText(x + 4, 0, seg_w - 8, h,
                                 Qt.AlignmentFlag.AlignVCenter, tag)
            x += seg_w
        painter.end()


# ── Helpers ───────────────────────────────────────────────────────────────────

def human(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

def find_efi(parts):
    for p in parts:
        fs = p.get("fstype","").lower()
        lb = p.get("label","").lower()
        if "efi" in fs or "efi" in lb or "esp" in lb:
            return p
    return None

def find_windows(parts):
    win = None
    for p in parts:
        if p.get("fstype","").lower() == "ntfs":
            if not win or p["size"] > win["size"]:
                win = p
    return win

def free_space(disk):
    used = sum(p["size"] for p in disk["partitions"])
    return max(0, disk["size"] - used)


# ── Main disk screen ──────────────────────────────────────────────────────────

STYLESHEET = MASTER_STYLE  # all styles from theme

class DiskScreen(QWidget):
    confirmed = pyqtSignal(dict, dict, float, str)  # disk, efi, size_gb, mode
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.disks: list[dict] = []
        self.selected_disk = None
        self.efi_partition = None
        self.windows_partition = None
        self._probe_worker = None
        self._mode = MODE_DUALBOOT
        self._build_ui()
        QTimer.singleShot(100, self.probe)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("Arch Installer — Disk Setup")
        self.setMinimumSize(700, 620)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 24)
        root.setSpacing(10)

        # Header
        t = QLabel("Disk Setup"); t.setObjectName("title")
        s = QLabel("Choose how to install Arch Linux on this machine.")
        s.setObjectName("sub")
        root.addWidget(t)
        root.addWidget(s)

        # ── Disk list ──────────────────────────────────────────────────────
        lbl = QLabel("Select a disk"); lbl.setObjectName("sec")
        root.addWidget(lbl)

        self.disk_list = QListWidget()
        self.disk_list.setFixedHeight(110)
        self.disk_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.disk_list.itemSelectionChanged.connect(self._on_disk_select)
        self.disk_list.setStyleSheet("QListWidget { background: #1a1825; border: 1px solid #2e2b3d; border-radius: 10px; padding: 4px; outline: none; } QListWidget::item { padding: 8px 14px; border-radius: 6px; color: #9e8fa8; font-size: 12px; } QListWidget::item:selected { background: #3d1f2d; color: #ff6b9d; } QListWidget::item:hover { background: #221f2e; color: #f0e6f0; }")
        root.addWidget(self.disk_list)

        # ── Partition bar ──────────────────────────────────────────────────
        bar_lbl = QLabel("Partition layout"); bar_lbl.setObjectName("sec")
        root.addWidget(bar_lbl)
        self.part_bar = PartitionBar()
        root.addWidget(self.part_bar)

        # ── Mode picker ────────────────────────────────────────────────────
        mode_lbl = QLabel("Installation mode"); mode_lbl.setObjectName("sec")
        root.addWidget(mode_lbl)

        self.mode_group = QButtonGroup(self)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)

        rb_style = (
            "QRadioButton { color: #9e8fa8; font-size: 13px;"
            " background: #1a1825; border: 1px solid #2e2b3d;"
            " border-radius: 8px; padding: 10px 16px; }}"
            "QRadioButton:checked { color: #ff6b9d; background: #3d1f2d;"
            " border: 2px solid #e8557a; }"
            "QRadioButton:hover { border-color: #e8557a; color: #f0e6f0; }"
            "QRadioButton::indicator { width: 0; height: 0; }"
        )

        self.rb_dual  = QRadioButton("⊞  Dualboot with Windows")
        self.rb_free  = QRadioButton("◉  Use free space")
        self.rb_wipe  = QRadioButton("✕  Wipe entire disk")
        self.rb_dual.setChecked(True)

        for rb in (self.rb_dual, self.rb_free, self.rb_wipe):
            rb.setStyleSheet(rb_style)
            self.mode_group.addButton(rb)
            mode_row.addWidget(rb)
        root.addLayout(mode_row)

        self.rb_dual.toggled.connect(lambda on: on and self._set_mode(MODE_DUALBOOT))
        self.rb_free.toggled.connect(lambda on: on and self._set_mode(MODE_FREESPACE))
        self.rb_wipe.toggled.connect(lambda on: on and self._set_mode(MODE_WIPE))

        # ── Mode detail panel (stacked) ────────────────────────────────────
        self.mode_stack = QStackedWidget()
        self.mode_stack.setFixedHeight(140)
        self.mode_stack.setStyleSheet("QStackedWidget { background: #1a1825; border: 1px solid #2e2b3d; border-radius: 10px; }")

        self.mode_stack.addWidget(self._build_dualboot_panel())   # 0
        self.mode_stack.addWidget(self._build_freespace_panel())  # 1
        self.mode_stack.addWidget(self._build_wipe_panel())       # 2

        root.addWidget(self.mode_stack)

        # ── Detection info ─────────────────────────────────────────────────
        self.detect_label = QLabel("Select a disk to continue.")
        self.detect_label.setObjectName("info")
        self.detect_label.setWordWrap(True)
        root.addWidget(self.detect_label)

        root.addStretch()

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back.emit)

        self.confirm_btn = QPushButton("Confirm & Continue →")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(self.back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        root.addLayout(btn_row)

    def _build_dualboot_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        w.setStyleSheet("background: transparent;")
        v.setContentsMargins(16, 12, 16, 12)

        desc = QLabel("Shrinks your Windows partition to make room for Arch.\nYour Windows install and files are preserved.")
        desc.setObjectName("sub")
        desc.setWordWrap(True)
        v.addWidget(desc)

        slider_row = QHBoxLayout()
        self.dual_slider = QSlider(Qt.Orientation.Horizontal)
        self.dual_slider.setMinimum(10)
        self.dual_slider.setMaximum(200)
        self.dual_slider.setValue(40)
        self.dual_slider.setEnabled(False)
        self.dual_slider.valueChanged.connect(self._on_dual_slider)
        self.dual_val_lbl = QLabel("40 GB")
        self.dual_val_lbl.setFixedWidth(56)
        slider_row.addWidget(self.dual_slider)
        slider_row.addWidget(self.dual_val_lbl)
        v.addLayout(slider_row)

        self.dual_info = QLabel("")
        self.dual_info.setObjectName("sub")
        v.addWidget(self.dual_info)

        warn = QLabel("⚠  Back up Windows data before continuing.")
        warn.setObjectName("warn")
        v.addWidget(warn)
        return w

    def _build_freespace_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        w.setStyleSheet("background: transparent;")
        v.setContentsMargins(16, 12, 16, 12)

        desc = QLabel("Uses already unallocated space on the disk.\nNothing existing will be touched.")
        desc.setObjectName("sub")
        desc.setWordWrap(True)
        v.addWidget(desc)

        slider_row = QHBoxLayout()
        self.free_slider = QSlider(Qt.Orientation.Horizontal)
        self.free_slider.setMinimum(10)
        self.free_slider.setMaximum(200)
        self.free_slider.setValue(40)
        self.free_slider.setEnabled(False)
        self.free_slider.valueChanged.connect(self._on_free_slider)
        self.free_val_lbl = QLabel("40 GB")
        self.free_val_lbl.setFixedWidth(56)
        slider_row.addWidget(self.free_slider)
        slider_row.addWidget(self.free_val_lbl)
        v.addLayout(slider_row)

        self.free_info = QLabel("")
        self.free_info.setObjectName("info")
        v.addWidget(self.free_info)
        return w

    def _build_wipe_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        w.setStyleSheet("background: transparent;")
        v.setContentsMargins(16, 12, 16, 12)

        desc = QLabel("Erases EVERYTHING on the selected disk and installs Arch.\nAll existing partitions, data and operating systems will be lost.")
        desc.setObjectName("danger")
        desc.setWordWrap(True)
        v.addWidget(desc)

        self.wipe_confirm_lbl = QLabel("")
        self.wipe_confirm_lbl.setObjectName("warn")
        self.wipe_confirm_lbl.setWordWrap(True)
        v.addWidget(self.wipe_confirm_lbl)

        v.addStretch()
        return w

    # ── Mode switching ────────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._mode = mode
        idx = {MODE_DUALBOOT: 0, MODE_FREESPACE: 1, MODE_WIPE: 2}[mode]
        self.mode_stack.setCurrentIndex(idx)
        if self.selected_disk:
            self._analyze_disk(self.selected_disk)

    # ── Probing ───────────────────────────────────────────────────────────────

    def probe(self):
        self.disk_list.clear()
        self.detect_label.setText("Scanning disks…")
        self._probe_worker = DiskProbeWorker()
        self._probe_worker.results_ready.connect(self._on_probe_done)
        self._probe_worker.error_occurred.connect(self._on_probe_error)
        self._probe_worker.start()

    def _on_probe_done(self, disks):
        self.disks = disks
        self.detect_label.setText("")
        if not disks:
            self.detect_label.setText("No disks found.")
            return
        for disk in disks:
            lbl = f"/dev/{disk['name']}  —  {human(disk['size'])}  —  {disk['model']}"
            item = QListWidgetItem(lbl)
            item.setData(Qt.ItemDataRole.UserRole, disk)
            self.disk_list.addItem(item)

    def _on_probe_error(self, msg):
        self.detect_label.setText(f"Error: {msg}")

    # ── Disk selection ────────────────────────────────────────────────────────

    def _on_disk_select(self):
        items = self.disk_list.selectedItems()
        if not items:
            return
        self.selected_disk = items[0].data(Qt.ItemDataRole.UserRole)
        self._analyze_disk(self.selected_disk)

    def _analyze_disk(self, disk: dict):
        parts = disk["partitions"]
        self.efi_partition    = find_efi(parts)
        self.windows_partition = find_windows(parts)
        raw_free_gb = free_space(disk) / 1024**3
        total_gb    = disk["size"] / 1024**3

        info_lines = []

        # ── Dualboot ──────────────────────────────────────────────────────
        if self._mode == MODE_DUALBOOT:
            if self.efi_partition:
                info_lines.append(f"✓ EFI: /dev/{self.efi_partition['name']} ({human(self.efi_partition['size'])})")
            else:
                info_lines.append("⚠ No EFI partition found")
            if self.windows_partition:
                info_lines.append(f"✓ Windows: /dev/{self.windows_partition['name']} ({human(self.windows_partition['size'])})")
                win_gb = self.windows_partition["size"] / 1024**3
                # Allow shrinking down to 50% of Windows or 30 GB minimum
                min_win = max(30.0, win_gb * 0.5)
                shrinkable = max(0.0, win_gb - min_win)
                max_gb = int(shrinkable + raw_free_gb)
                max_gb = max(10, min(max_gb, int(total_gb * 0.8)))
                self.dual_slider.setMaximum(max_gb)
                self.dual_slider.setValue(min(40, max_gb))
                self.dual_slider.setEnabled(True)
                self._on_dual_slider(self.dual_slider.value())
            else:
                info_lines.append("⚠ No Windows NTFS partition found — dualboot may not work")
                self.dual_slider.setEnabled(False)

        # ── Free space ────────────────────────────────────────────────────
        elif self._mode == MODE_FREESPACE:
            if raw_free_gb < 10:
                info_lines.append(f"⚠ Only {raw_free_gb:.1f} GB unallocated — not enough for Arch (need ≥10 GB)")
                self.free_slider.setEnabled(False)
                self.confirm_btn.setEnabled(False)
            else:
                info_lines.append(f"✓ {raw_free_gb:.1f} GB unallocated space available")
                max_gb = int(raw_free_gb)
                self.free_slider.setMaximum(max_gb)
                self.free_slider.setValue(min(40, max_gb))
                self.free_slider.setEnabled(True)
                self._on_free_slider(self.free_slider.value())
            if self.efi_partition:
                info_lines.append(f"✓ EFI: /dev/{self.efi_partition['name']}")
            else:
                info_lines.append("⚠ No EFI partition found — one will be created")

        # ── Wipe ──────────────────────────────────────────────────────────
        elif self._mode == MODE_WIPE:
            info_lines.append(f"⚠ ALL data on /dev/{disk['name']} ({human(disk['size'])}) will be erased")
            if self.windows_partition:
                info_lines.append(f"  This includes Windows on /dev/{self.windows_partition['name']}")
            self.wipe_confirm_lbl.setText(
                f"Disk: /dev/{disk['name']}  |  {len(parts)} existing partition(s)  |  {human(disk['size'])} total"
            )

        self.detect_label.setText("\n".join(info_lines))
        self._update_bar()
        self.confirm_btn.setEnabled(True)

    def _update_bar(self):
        if not self.selected_disk:
            return
        parts   = self.selected_disk["partitions"]
        total   = self.selected_disk["size"]
        segs    = []

        if self._mode == MODE_WIPE:
            # Show whole disk as Arch
            segs = [(total, PART_COLORS["arch"], "Arch (full disk)")]
        else:
            for p in parts:
                fs = p.get("fstype","").lower()
                lb = p.get("label","").lower()
                if "efi" in fs or "efi" in lb or "esp" in lb:
                    segs.append((p["size"], PART_COLORS["efi"], "EFI"))
                elif fs == "ntfs":
                    segs.append((p["size"], PART_COLORS["ntfs"], "Windows"))
                else:
                    segs.append((p["size"], PART_COLORS["other"], fs or "?"))

            # Arch allocation
            arch_gb = 0
            if self._mode == MODE_DUALBOOT:
                arch_gb = self.dual_slider.value()
            elif self._mode == MODE_FREESPACE:
                arch_gb = self.free_slider.value()

            if arch_gb:
                segs.append((int(arch_gb * 1024**3), PART_COLORS["arch"], f"Arch ({arch_gb} GB)"))

            # Remaining free
            used = sum(s[0] for s in segs)
            remaining = total - used
            if remaining > 0:
                segs.append((remaining, PART_COLORS["free"], "free"))

        self.part_bar.set_segments(segs)

    # ── Sliders ───────────────────────────────────────────────────────────────

    def _on_dual_slider(self, val):
        self.dual_val_lbl.setText(f"{val} GB")
        if self.selected_disk and self.windows_partition:
            win_gb = self.windows_partition["size"] / 1024**3
            remaining = win_gb - val
            self.dual_info.setText(
                f"Windows will have {remaining:.1f} GB remaining  |  Arch gets {val} GB"
            )
        self._update_bar()

    def _on_free_slider(self, val):
        self.free_val_lbl.setText(f"{val} GB")
        raw_free = free_space(self.selected_disk) / 1024**3 if self.selected_disk else 0
        self.free_info.setText(f"Using {val} GB of {raw_free:.1f} GB available")
        self._update_bar()

    # ── Confirm ───────────────────────────────────────────────────────────────

    def _on_confirm(self):
        if not self.selected_disk:
            return

        disk_name = self.selected_disk["name"]

        if self._mode == MODE_DUALBOOT:
            gb = float(self.dual_slider.value())
            win = f"/dev/{self.windows_partition['name']}" if self.windows_partition else "N/A"
            msg = (
                f"Dualboot install on /dev/{disk_name}\n\n"
                f"  • Windows ({win}) will be shrunk\n"
                f"  • {gb:.0f} GB allocated for Arch\n"
                f"  • Existing EFI partition reused\n\n"
                f"This cannot be undone. Continue?"
            )
            btn = QMessageBox.StandardButton.Yes

        elif self._mode == MODE_FREESPACE:
            gb = float(self.free_slider.value())
            msg = (
                f"Install into free space on /dev/{disk_name}\n\n"
                f"  • {gb:.0f} GB of unallocated space will be used\n"
                f"  • Existing partitions untouched\n\n"
                f"Continue?"
            )
            btn = QMessageBox.StandardButton.Yes

        elif self._mode == MODE_WIPE:
            gb = self.selected_disk["size"] / 1024**3
            msg = (
                f"⚠  WIPE /dev/{disk_name} ({human(self.selected_disk['size'])})\n\n"
                f"ALL existing data will be permanently destroyed.\n"
                f"This includes any operating systems and files on this disk.\n\n"
                f"Are you absolutely sure?"
            )
            btn = QMessageBox.StandardButton.Yes

        reply = QMessageBox.warning(
            self, "Confirm Partitioning", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.confirmed.emit(
                self.selected_disk,
                self.efi_partition or {},
                gb,
                self._mode
            )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen = DiskScreen()
    screen.confirmed.connect(lambda disk, efi, gb, mode: print(
        f"Mode: {mode}  Disk: /dev/{disk['name']}  Size: {gb:.0f} GB"
    ))
    screen.show()
    sys.exit(app.exec())
