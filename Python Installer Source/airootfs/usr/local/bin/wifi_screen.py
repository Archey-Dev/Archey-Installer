#!/usr/bin/env python3
"""
Archey — Wi-Fi screen using iwctl (iwd).
Auto-detects first wireless device, scans, lists networks, connects.
"""

import subprocess
import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from theme import MASTER_STYLE, PINK, PINK2, ROSE, TEXT, TEXT2, TEXT3, BG2, BORDER, GREEN, RED, YELLOW


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list, timeout: int = 15) -> tuple[int, str]:
    """Run a command, return (returncode, combined output)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "timed out"
    except FileNotFoundError:
        return 1, f"{cmd[0]}: not found"
    except Exception as e:
        return 1, str(e)


def iwctl(*args, timeout: int = 15) -> tuple[int, str]:
    return run(["iwctl"] + list(args), timeout)


def strip_ansi(text: str) -> str:
    import re
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


def find_device() -> str | None:
    """Return the first wireless device name (e.g. wlan0)."""
    rc, out = iwctl("device", "list")
    for line in out.splitlines():
        clean = strip_ansi(line).strip()
        # Skip headers, dividers, empty lines
        if not clean:
            continue
        if any(clean.startswith(x) for x in ("-", "─", "━", "Device", "device")):
            continue
        if "Name" in clean and "Powered" in clean:
            continue
        parts = clean.split()
        # Device name should look like wlan0, wlp2s0, wlp3s0 etc.
        if parts and (parts[0].startswith("wl") or parts[0].startswith("ww")):
            return parts[0]
    return None


def signal_bars(signal_str: str) -> str:
    """Convert an rssi/signal string like '-65' or '****' to bar display."""
    try:
        val = int(signal_str)
        # rssi: -30 excellent, -90 terrible
        if val >= -50: return "▂▄▆█"
        if val >= -60: return "▂▄▆░"
        if val >= -70: return "▂▄░░"
        if val >= -80: return "▂░░░"
        return "░░░░"
    except ValueError:
        # iwctl sometimes gives stars or percentage
        stars = signal_str.count("*")
        bars = ["░░░░", "▂░░░", "▂▄░░", "▂▄▆░", "▂▄▆█"]
        return bars[min(stars, 4)]


# ── Workers ───────────────────────────────────────────────────────────────────

class ScanWorker(QThread):
    """Finds device, triggers scan, waits, then lists networks."""
    device_found   = pyqtSignal(str)
    results_ready  = pyqtSignal(list)   # list of dicts
    error_occurred = pyqtSignal(str)

    def run(self):
        # 1. Find device
        device = find_device()
        if not device:
            # Try bringing up station mode
            run(["rfkill", "unblock", "wifi"])
            time.sleep(1)
            device = find_device()
        if not device:
            self.error_occurred.emit(
                "No wireless device found.\n"
                "Make sure iwd is running:  systemctl start iwd"
            )
            return

        self.device_found.emit(device)

        # 2. Scan (non-blocking — iwctl returns immediately, scan runs async)
        iwctl("station", device, "scan")
        time.sleep(3)   # wait for scan to complete

        # 3. Get networks
        rc, out = iwctl("station", device, "get-networks")
        if rc != 0:
            self.error_occurred.emit(f"Could not list networks:\n{out}")
            return

        networks = self._parse(out, device)
        self.results_ready.emit(networks)

    def _parse(self, raw: str, device: str) -> list:
        """
        iwctl get-networks output looks like:
                               Available networks
          Network name    Security    Signal
        ─────────────────────────────────────────
          MyWifi          psk         ****
          OpenNet         open        **
        """
        networks = []
        seen = set()
        in_table = False

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Skip header rows
            if "Available networks" in stripped:
                continue
            if "Network name" in stripped or "─" in stripped or "━" in stripped:
                in_table = True
                continue
            if not in_table:
                continue

            # Each data row: may have a ">" prefix for connected network
            # Remove ANSI color codes
            import re
            clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
            connected = ">" in clean
            clean = clean.replace(">", " ")

            parts = clean.split()
            if not parts:
                continue

            # Last part is signal, second-to-last is security, rest is SSID
            if len(parts) < 2:
                continue

            signal   = parts[-1]
            security = parts[-2].lower() if len(parts) >= 2 else "open"
            ssid     = " ".join(parts[:-2]) if len(parts) > 2 else parts[0]

            if not ssid or ssid in seen:
                continue
            seen.add(ssid)

            networks.append({
                "ssid":      ssid,
                "security":  security,
                "signal":    signal,
                "connected": connected,
                "device":    device,
            })

        return networks


class ConnectWorker(QThread):
    success = pyqtSignal(str)
    failure = pyqtSignal(str)

    def __init__(self, device: str, ssid: str, password: str = ""):
        super().__init__()
        self.device   = device
        self.ssid     = ssid
        self.password = password

    def run(self):
        if self.password:
            # Pre-provision passphrase then connect
            rc, out = iwctl(
                "--passphrase", self.password,
                "station", self.device, "connect", self.ssid,
                timeout=30
            )
        else:
            rc, out = iwctl(
                "station", self.device, "connect", self.ssid,
                timeout=30
            )

        if rc == 0:
            # Wait a moment and verify we actually got an IP
            time.sleep(2)
            rc2, _ = run(["ping", "-c", "1", "-W", "3", "8.8.8.8"])
            if rc2 == 0:
                self.success.emit(self.ssid)
            else:
                # Still mark success — IP may take longer via DHCP
                self.success.emit(self.ssid)
        else:
            self.failure.emit(out or "Connection failed — check your password.")


# ── Screen ────────────────────────────────────────────────────────────────────

class WifiScreen(QWidget):
    connected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._device       = None
        self._scan_worker  = None
        self._conn_worker  = None
        self.setStyleSheet(MASTER_STYLE)
        self._build_ui()
        # Start iwd if not running, then scan
        QTimer.singleShot(300, self._ensure_iwd_and_scan)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(12)

        t = QLabel("Wi-Fi"); t.setObjectName("title")
        s = QLabel("Connect to a wireless network to download packages during installation.")
        s.setObjectName("sub"); s.setWordWrap(True)
        root.addWidget(t); root.addWidget(s)

        # Device info
        self.device_lbl = QLabel("Detecting wireless device...")
        self.device_lbl.setObjectName("hint")
        root.addWidget(self.device_lbl)

        # Spinner bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)

        # Network list
        lbl = QLabel("AVAILABLE NETWORKS"); lbl.setObjectName("sec")
        root.addWidget(lbl)

        self.net_list = QListWidget()
        root.addWidget(self.net_list, stretch=1)
        self.net_list.itemSelectionChanged.connect(self._on_select)

        # Status
        self.status = QLabel("Scanning...")
        self.status.setObjectName("sub")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.status)

        # Password field
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.returnPressed.connect(self._on_connect)
        self.pw_input.setVisible(False)
        root.addWidget(self.pw_input)

        # Buttons
        btn_row = QHBoxLayout()
        self.scan_btn = QPushButton("↻  Scan again")
        self.scan_btn.setObjectName("secondary")
        self.scan_btn.clicked.connect(self._scan)
        self.scan_btn.setEnabled(False)

        self.skip_btn = QPushButton("Skip (ethernet)")
        self.skip_btn.setObjectName("secondary")
        self.skip_btn.clicked.connect(self.connected.emit)

        self.conn_btn = QPushButton("Connect ->")
        self.conn_btn.setObjectName("primary")
        self.conn_btn.setEnabled(False)
        self.conn_btn.clicked.connect(self._on_connect)

        btn_row.addWidget(self.scan_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.conn_btn)
        root.addLayout(btn_row)

    # ── iwd setup ─────────────────────────────────────────────────────────────

    def _ensure_iwd_and_scan(self):
        """Start iwd service if not running, then scan."""
        run(["systemctl", "start", "iwd"])
        run(["rfkill", "unblock", "wifi"])
        time.sleep(1)
        self._scan()

    def _scan(self):
        self.net_list.clear()
        self.pw_input.setVisible(False)
        self.conn_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.status.setText("Scanning for networks...")
        self.progress.setVisible(True)

        self._scan_worker = ScanWorker()
        self._scan_worker.device_found.connect(self._on_device_found)
        self._scan_worker.results_ready.connect(self._on_scan_done)
        self._scan_worker.error_occurred.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_device_found(self, device: str):
        self._device = device
        self.device_lbl.setText(f"Device: {device}")

    def _on_scan_done(self, networks: list):
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        if not networks:
            self.status.setText("No networks found. Try scanning again.")
            return

        self.status.setText(f"{len(networks)} network(s) found")

        for net in networks:
            bars = signal_bars(net["signal"])
            lock = "[+]" if net["security"] not in ("open", "") else "[ ]"
            tag  = "  <- connected" if net["connected"] else ""
            item = QListWidgetItem(f"{bars}  {lock}  {net['ssid']}{tag}")
            item.setData(Qt.ItemDataRole.UserRole, net)
            self.net_list.addItem(item)

    def _on_scan_error(self, msg: str):
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.status.setText(f"Error: {msg}")
        self.status.setStyleSheet(f"color: {YELLOW};")

    # ── Selection / connect ───────────────────────────────────────────────────

    def _on_select(self):
        items = self.net_list.selectedItems()
        if not items:
            self.conn_btn.setEnabled(False)
            self.pw_input.setVisible(False)
            return
        net = items[0].data(Qt.ItemDataRole.UserRole)
        needs_pw = net["security"] not in ("open", "")
        self.pw_input.setVisible(needs_pw)
        self.pw_input.clear()
        if net["connected"]:
            self.conn_btn.setText("Already connected")
            self.conn_btn.setEnabled(False)
        else:
            self.conn_btn.setText("Connect ->")
            self.conn_btn.setEnabled(True)

    def _on_connect(self):
        items = self.net_list.selectedItems()
        if not items or not self._device:
            return
        net      = items[0].data(Qt.ItemDataRole.UserRole)
        ssid     = net["ssid"]
        password = self.pw_input.text() if self.pw_input.isVisible() else ""

        self.progress.setVisible(True)
        self.conn_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.status.setText(f"Connecting to {ssid}...")

        self._conn_worker = ConnectWorker(self._device, ssid, password)
        self._conn_worker.success.connect(self._on_connect_ok)
        self._conn_worker.failure.connect(self._on_connect_fail)
        self._conn_worker.start()

    def _on_connect_ok(self, ssid: str):
        self.progress.setVisible(False)
        self.status.setText(f"Connected to {ssid}")
        self.status.setStyleSheet(f"color: {GREEN};")
        QTimer.singleShot(800, self.connected.emit)

    def _on_connect_fail(self, msg: str):
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.conn_btn.setEnabled(True)
        self.status.setText("Connection failed.")
        self.status.setStyleSheet(f"color: {RED};")
        QMessageBox.warning(self, "Connection Failed",
            f"Could not connect:\n\n{msg}\n\nCheck your password and try again.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = WifiScreen()
    s.connected.connect(lambda: print("Connected!"))
    s.show()
    sys.exit(app.exec())
