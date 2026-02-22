#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Archey — Install progress screen.
"""

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit
)
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QFont, QTextCursor
from theme import MASTER_STYLE, PINK, GREEN, RED, TEXT, TEXT2, TEXT3, BG2, BORDER
from install_backend import InstallWorker



# ── Rotating ✦ spinner ────────────────────────────────────────────────────────

class SpinnerWidget(QWidget):
    """Draws a 4-pointed star shape that visibly rotates using QPainter paths."""

    def __init__(self, size: int = 36, parent=None):
        super().__init__(parent)
        self._angle      = 0.0
        self._done_color = None
        self.setFixedSize(size, size)

        self._timer = QTimer()
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._done_color = None
        self._timer.start()

    def stop_ok(self):
        self._timer.stop()
        self._angle = 0
        self._done_color = "#7edd9a"
        self.update()

    def stop_fail(self):
        self._timer.stop()
        self._angle = 0
        self._done_color = "#ff6b6b"
        self.update()

    def _tick(self):
        self._angle = (self._angle + 3.0) % 360
        self.update()

    def paintEvent(self, event):
        import math
        from PyQt6.QtGui import QPainterPath

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        color  = self._done_color if self._done_color else "#ff6b9d"

        painter.translate(cx, cy)
        painter.rotate(self._angle)

        # Build a 4-pointed star path
        # Outer radius (spike tips) and inner radius (waist between spikes)
        R = w * 0.44   # outer
        r = w * 0.10   # inner
        points = 4
        path = QPainterPath()

        for i in range(points * 2):
            angle_rad = math.radians(i * 180 / points - 90)
            radius    = R if i % 2 == 0 else r
            x = math.cos(angle_rad) * radius
            y = math.sin(angle_rad) * radius
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
        painter.end()


class InstallScreen(QWidget):
    finished = pyqtSignal()
    failed   = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._spinner = SpinnerWidget(size=36)

        self.title = QLabel("Installing Arch Linux…")
        self.title.setObjectName("title")

        title_row.addWidget(self._spinner)
        title_row.addWidget(self.title)
        root.addLayout(title_row)

        self.status = QLabel("Preparing…")
        self.status.setObjectName("sub")
        root.addWidget(self.status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        root.addWidget(self.bar)

        self.pct_label = QLabel("0%")
        self.pct_label.setObjectName("hint")
        root.addWidget(self.pct_label)

        log_lbl = QLabel("INSTALLATION LOG"); log_lbl.setObjectName("sec")
        root.addWidget(log_lbl)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("JetBrains Mono", 10))
        root.addWidget(self.log, stretch=1)

        btn_row = QHBoxLayout()
        self.reboot_btn = QPushButton("Reboot Now")
        self.reboot_btn.setObjectName("primary")
        self.reboot_btn.setVisible(False)
        self.reboot_btn.clicked.connect(lambda: subprocess.run(["reboot"]))

        self.close_btn = QPushButton("Exit Installer")
        self.close_btn.setObjectName("danger")
        self.close_btn.setVisible(False)
        self.close_btn.clicked.connect(lambda: self.failed.emit("User cancelled after error"))

        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)
        btn_row.addWidget(self.reboot_btn)
        root.addLayout(btn_row)

    def start(self, state):
        self._spinner.start()
        self._worker = InstallWorker(state)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.start()

    def _on_progress(self, msg, pct):
        self.status.setText(msg)
        self.bar.setValue(pct)
        self.pct_label.setText(f"{pct}%")

    def _on_log(self, line):
        self.log.append(line)
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log.setTextCursor(cursor)

    def _on_success(self):
        self._spinner.stop_ok()
        self.title.setText("Installation Complete! ✦")
        self.title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {PINK}; letter-spacing: 1px;")
        self.status.setText("Arch Linux has been installed. Remove the USB and reboot.")
        self.bar.setValue(100)
        self.pct_label.setText("100%")
        self.reboot_btn.setVisible(True)
        self.finished.emit()

    def _on_failure(self, error):
        self._spinner.stop_fail()
        self.title.setText("Installation Failed")
        self.title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {RED}; letter-spacing: 1px;")
        self.status.setText(f"Error: {error}")
        self._on_log(f"\n❌ FATAL ERROR:\n{error}")
        self.close_btn.setVisible(True)
        self.failed.emit(error)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = InstallScreen()
    s.show()
    sys.exit(app.exec())
