#!/usr/bin/env python3
"""
Arch ISO USB Creator - GUI Version with Built-in Theme
Cross-platform bootable USB stick creator with PyQt5 interface
"""

import os
import sys
import json
import hashlib
import platform
import subprocess
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QProgressBar,
        QFileDialog, QMessageBox, QGroupBox, QCheckBox, QComboBox, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QPalette, QColor
except ImportError:
    print("ERROR: PyQt5 is not installed!")
    print("\nInstall it with:")
    print("  sudo pacman -S python-pyqt5")
    print("  or")
    print("  pip install PyQt5 --break-system-packages")
    sys.exit(1)


class DarkTheme:
    """Dark theme color palette - ensures all buttons are visible"""
    BG_DARK = "#1e1e1e"
    BG_MEDIUM = "#252526"
    BG_LIGHT = "#2d2d30"
    BG_LIGHTER = "#3e3e42"
    FG_PRIMARY = "#ffffff"
    FG_SECONDARY = "#cccccc"
    FG_DISABLED = "#858585"
    ACCENT_BLUE = "#0e639c"
    ACCENT_BLUE_HOVER = "#1177bb"
    ACCENT_GREEN = "#0e8a16"
    ACCENT_RED = "#d73a49"
    ACCENT_ORANGE = "#f0ad4e"
    BORDER = "#3f3f46"

    @staticmethod
    def apply_to_app(app):
        """Apply dark theme to the entire application"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(DarkTheme.BG_DARK))
        palette.setColor(QPalette.WindowText, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.Base, QColor(DarkTheme.BG_MEDIUM))
        palette.setColor(QPalette.AlternateBase, QColor(DarkTheme.BG_LIGHT))
        palette.setColor(QPalette.ToolTipBase, QColor(DarkTheme.BG_LIGHTER))
        palette.setColor(QPalette.ToolTipText, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.Text, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.Button, QColor(DarkTheme.BG_LIGHTER))
        palette.setColor(QPalette.ButtonText, QColor(DarkTheme.FG_PRIMARY))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(DarkTheme.ACCENT_BLUE))
        palette.setColor(QPalette.Highlight, QColor(DarkTheme.ACCENT_BLUE))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(DarkTheme.FG_DISABLED))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DarkTheme.FG_DISABLED))

        app.setPalette(palette)

    @staticmethod
    def get_stylesheet():
        """Get the application stylesheet"""
        return f"""
            QMainWindow {{
                background-color: {DarkTheme.BG_DARK};
            }}

            QWidget {{
                background-color: {DarkTheme.BG_DARK};
                color: {DarkTheme.FG_PRIMARY};
                font-size: 10pt;
            }}

            QLabel {{
                color: {DarkTheme.FG_PRIMARY};
                background-color: transparent;
            }}

            QPushButton {{
                background-color: {DarkTheme.BG_LIGHTER};
                color: {DarkTheme.FG_PRIMARY};
                border: 1px solid {DarkTheme.BORDER};
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
                min-height: 35px;
            }}

            QPushButton:hover {{
                background-color: {DarkTheme.BG_LIGHT};
                border: 1px solid {DarkTheme.ACCENT_BLUE};
            }}

            QPushButton:pressed {{
                background-color: {DarkTheme.BG_MEDIUM};
            }}

            QPushButton:disabled {{
                background-color: {DarkTheme.BG_MEDIUM};
                color: {DarkTheme.FG_DISABLED};
                border: 1px solid {DarkTheme.BG_LIGHT};
            }}

            QPushButton#primaryButton {{
                background-color: {DarkTheme.ACCENT_BLUE};
                color: {DarkTheme.FG_PRIMARY};
                border: none;
                min-height: 40px;
            }}

            QPushButton#primaryButton:hover {{
                background-color: {DarkTheme.ACCENT_BLUE_HOVER};
            }}

            QPushButton#successButton {{
                background-color: {DarkTheme.ACCENT_GREEN};
                color: {DarkTheme.FG_PRIMARY};
                border: none;
            }}

            QPushButton#dangerButton {{
                background-color: {DarkTheme.ACCENT_RED};
                color: {DarkTheme.FG_PRIMARY};
                border: none;
            }}

            QLineEdit {{
                background-color: {DarkTheme.BG_MEDIUM};
                color: {DarkTheme.FG_PRIMARY};
                border: 1px solid {DarkTheme.BORDER};
                padding: 8px;
                border-radius: 3px;
            }}

            QLineEdit:focus {{
                border: 1px solid {DarkTheme.ACCENT_BLUE};
            }}

            QTextEdit {{
                background-color: {DarkTheme.BG_MEDIUM};
                color: {DarkTheme.FG_PRIMARY};
                border: 1px solid {DarkTheme.BORDER};
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 8px;
            }}

            QComboBox {{
                background-color: {DarkTheme.BG_MEDIUM};
                color: {DarkTheme.FG_PRIMARY};
                border: 1px solid {DarkTheme.BORDER};
                padding: 8px;
                border-radius: 3px;
            }}

            QComboBox:hover {{
                border: 1px solid {DarkTheme.ACCENT_BLUE};
            }}

            QComboBox::drop-down {{
                border: none;
            }}

            QComboBox QAbstractItemView {{
                background-color: {DarkTheme.BG_MEDIUM};
                color: {DarkTheme.FG_PRIMARY};
                selection-background-color: {DarkTheme.ACCENT_BLUE};
            }}

            QCheckBox {{
                color: {DarkTheme.FG_PRIMARY};
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 1px solid {DarkTheme.BORDER};
                border-radius: 3px;
                background-color: {DarkTheme.BG_MEDIUM};
            }}

            QCheckBox::indicator:checked {{
                background-color: {DarkTheme.ACCENT_BLUE};
                border: 1px solid {DarkTheme.ACCENT_BLUE};
            }}

            QCheckBox::indicator:hover {{
                border: 1px solid {DarkTheme.ACCENT_BLUE};
            }}

            QGroupBox {{
                color: {DarkTheme.FG_SECONDARY};
                border: 1px solid {DarkTheme.BORDER};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {DarkTheme.ACCENT_BLUE};
            }}

            QProgressBar {{
                background-color: {DarkTheme.BG_MEDIUM};
                border: 1px solid {DarkTheme.BORDER};
                border-radius: 3px;
                text-align: center;
                color: {DarkTheme.FG_PRIMARY};
                min-height: 25px;
            }}

            QProgressBar::chunk {{
                background-color: {DarkTheme.ACCENT_BLUE};
                border-radius: 2px;
            }}

            QFrame#separator {{
                background-color: {DarkTheme.BORDER};
            }}
        """


class USBCreatorThread(QThread):
    """Thread for USB creation process"""
    log_signal = pyqtSignal(str, str)  # message, color
    progress_signal = pyqtSignal(int)  # progress percentage
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, repo, device, iso_path, verify):
        super().__init__()
        self.repo = repo
        self.device = device
        self.iso_path = iso_path
        self.verify = verify
        self.running = True

    def log(self, message, level="info"):
        """Emit log message with color"""
        color_map = {
            "info": DarkTheme.FG_SECONDARY,
            "success": DarkTheme.ACCENT_GREEN,
            "error": DarkTheme.ACCENT_RED,
            "warning": DarkTheme.ACCENT_ORANGE
        }
        color = color_map.get(level, DarkTheme.FG_PRIMARY)
        self.log_signal.emit(message, color)

    def run(self):
        """Execute the USB creation process"""
        try:
            self.progress_signal.emit(0)

            # Determine ISO source
            if self.iso_path:
                iso_file = self.iso_path
                self.log(f"Using local ISO: {iso_file}", "info")

                if not os.path.exists(iso_file):
                    self.finished_signal.emit(False, "ISO file not found")
                    return

                self.progress_signal.emit(30)
            else:
                # Download from GitHub
                self.log("Fetching latest release from GitHub...", "info")
                iso_file = self.download_iso()
                if not iso_file:
                    self.finished_signal.emit(False, "Failed to download ISO")
                    return

            self.progress_signal.emit(40)

            # Get ISO size
            iso_size = os.path.getsize(iso_file)
            self.log(f"ISO size: {iso_size / 1073741824:.2f} GB", "info")

            self.progress_signal.emit(50)

            # Create bootable USB
            self.log(f"Writing ISO to {self.device}...", "info")
            if self.create_bootable_usb(iso_file):
                self.progress_signal.emit(100)
                self.log("Bootable USB created successfully!", "success")
                self.finished_signal.emit(True, "USB created successfully!")
            else:
                self.finished_signal.emit(False, "Failed to create bootable USB")

        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.finished_signal.emit(False, str(e))

    def download_iso(self):
        """Download ISO from GitHub"""
        try:
            # Get latest release
            url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            req = Request(url, headers={'User-Agent': 'arch-iso-usb-creator'})

            with urlopen(req) as response:
                release = json.loads(response.read().decode())

            self.log(f"Latest release: {release['name']}", "info")

            # Find ISO asset
            iso_asset = None
            for asset in release['assets']:
                if asset['name'].endswith('.iso'):
                    iso_asset = asset
                    break

            if not iso_asset:
                self.log("No ISO file found in release", "error")
                return None

            iso_name = iso_asset['name']
            iso_size = iso_asset['size']
            iso_url = iso_asset['browser_download_url']

            self.log(f"Downloading: {iso_name} ({iso_size / 1073741824:.2f} GB)", "info")

            # Download with progress
            req = Request(iso_url, headers={'User-Agent': 'arch-iso-usb-creator'})

            with urlopen(req) as response:
                downloaded = 0
                chunk_size = 1024 * 1024  # 1MB

                with open(iso_name, 'wb') as f:
                    while self.running:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Update progress (30-40% range for download)
                        progress = 30 + int((downloaded / iso_size) * 10)
                        self.progress_signal.emit(progress)

                        mb_downloaded = downloaded / 1048576
                        mb_total = iso_size / 1048576
                        self.log(f"Downloaded: {mb_downloaded:.1f}/{mb_total:.1f} MB", "info")

            self.log("Download complete", "success")
            return iso_name

        except Exception as e:
            self.log(f"Download error: {e}", "error")
            return None

    def create_bootable_usb(self, iso_path):
        """Create bootable USB"""
        system = platform.system()

        try:
            if system == "Linux":
                return self.create_bootable_usb_linux(iso_path)
            elif system == "Windows":
                return self.create_bootable_usb_windows(iso_path)
            elif system == "Darwin":
                return self.create_bootable_usb_macos(iso_path)
            else:
                self.log(f"Unsupported OS: {system}", "error")
                return False
        except Exception as e:
            self.log(f"Error creating bootable USB: {e}", "error")
            return False

    def create_bootable_usb_linux(self, iso_path):
        """Create bootable USB on Linux"""
        self.log("Unmounting device...", "info")
        subprocess.run(['sudo', 'umount', f'{self.device}*'],
                      stderr=subprocess.DEVNULL)

        self.log("Writing ISO (this may take several minutes)...", "info")
        self.progress_signal.emit(60)

        # Use pkexec for GUI password prompt, fallback to sudo
        sudo_cmd = 'pkexec'
        if subprocess.run(['which', 'pkexec'], capture_output=True).returncode != 0:
            sudo_cmd = 'sudo'
            self.log("Note: You may need to enter password in terminal", "warning")

        process = subprocess.Popen([
            sudo_cmd, 'dd',
            f'if={iso_path}',
            f'of={self.device}',
            'bs=4M',
            'oflag=sync'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        current_progress = 60
        for line in process.stdout:
            if not self.running:
                process.terminate()
                return False
            self.log(line.strip(), "info")
            current_progress = min(90, current_progress + 1)
            self.progress_signal.emit(current_progress)

        process.wait()

        if process.returncode == 0:
            self.log("Syncing...", "info")
            subprocess.run(['sync'])
            return True
        return False

    def create_bootable_usb_windows(self, iso_path):
        """Create bootable USB on Windows"""
        self.log("Writing ISO...", "info")
        self.progress_signal.emit(60)

        try:
            with open(iso_path, 'rb') as iso_file:
                iso_data = iso_file.read()

            total_size = len(iso_data)

            with open(self.device, 'wb') as device_file:
                chunk_size = 1024 * 1024  # 1MB
                written = 0

                for i in range(0, total_size, chunk_size):
                    if not self.running:
                        return False

                    chunk = iso_data[i:i+chunk_size]
                    device_file.write(chunk)
                    written += len(chunk)

                    progress = 60 + int((written / total_size) * 35)
                    self.progress_signal.emit(progress)

                    mb_written = written / 1048576
                    mb_total = total_size / 1048576
                    self.log(f"Written: {mb_written:.1f}/{mb_total:.1f} MB", "info")

            return True
        except PermissionError:
            self.log("Permission denied. Run as Administrator!", "error")
            return False

    def create_bootable_usb_macos(self, iso_path):
        """Create bootable USB on macOS"""
        self.log("Unmounting disk...", "info")
        subprocess.run(['diskutil', 'unmountDisk', self.device])

        self.log("Writing ISO...", "info")
        self.progress_signal.emit(60)

        # Use osascript for GUI password prompt
        process = subprocess.Popen([
            'osascript', '-e',
            f'do shell script "dd if={iso_path} of={self.device} bs=1m" with administrator privileges'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        current_progress = 60
        for line in process.stdout:
            if not self.running:
                process.terminate()
                return False
            self.log(line.strip(), "info")
            current_progress = min(90, current_progress + 1)
            self.progress_signal.emit(current_progress)

        process.wait()

        if process.returncode == 0:
            self.log("Ejecting disk...", "info")
            subprocess.run(['diskutil', 'eject', self.device])
            return True
        return False

    def stop(self):
        """Stop the process"""
        self.running = False


class USBCreatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.devices = []
        self.init_ui()
        self.scan_devices()

    def check_privileges(self):
        """Check if running with appropriate privileges"""
        system = platform.system()

        if system == "Linux":
            # Check if pkexec is available
            result = subprocess.run(['which', 'pkexec'], capture_output=True)
            if result.returncode != 0:
                # pkexec not available, warn about sudo
                QMessageBox.information(
                    self,
                    "Admin Privileges Required",
                    "⚠️ This application requires administrator privileges to write to USB devices.\n\n"
                    "If prompted, please enter your password in the terminal where you launched this application.\n\n"
                    "Alternatively, install 'pkexec' for graphical password prompts:\n"
                    "  sudo pacman -S polkit"
                )
        elif system == "Windows":
            # Check if running as admin
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    QMessageBox.warning(
                        self,
                        "Administrator Required",
                        "⚠️ This application must be run as Administrator!\n\n"
                        "Please close this window and:\n"
                        "1. Right-click on Command Prompt or PowerShell\n"
                        "2. Select 'Run as administrator'\n"
                        "3. Run: python usb_creator_gui.py"
                    )
            except:
                pass

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Arch ISO USB Creator")
        self.setMinimumSize(900, 750)

        # Check if we need sudo/admin privileges
        self.check_privileges()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("💾 Arch ISO USB Creator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {DarkTheme.ACCENT_BLUE}; padding: 10px;")
        main_layout.addWidget(title_label)

        # Separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        main_layout.addWidget(separator)

        # Source group
        source_group = QGroupBox("ISO Source")
        source_layout = QVBoxLayout()
        source_layout.setSpacing(10)

        # GitHub repo option
        repo_layout = QHBoxLayout()
        self.repo_radio_label = QLabel("GitHub Repository:")
        self.repo_radio_label.setMinimumWidth(140)
        self.repo_edit = QLineEdit("Archey-Dev/Archey-Installer")
        repo_layout.addWidget(self.repo_radio_label)
        repo_layout.addWidget(self.repo_edit)
        source_layout.addLayout(repo_layout)

        # Local ISO option
        iso_layout = QHBoxLayout()
        iso_label = QLabel("Or Local ISO File:")
        iso_label.setMinimumWidth(140)
        self.iso_path_edit = QLineEdit()
        self.iso_path_edit.setPlaceholderText("Leave empty to download from GitHub")
        iso_browse_btn = QPushButton("Browse...")
        iso_browse_btn.clicked.connect(self.browse_iso)
        iso_layout.addWidget(iso_label)
        iso_layout.addWidget(self.iso_path_edit)
        iso_layout.addWidget(iso_browse_btn)
        source_layout.addLayout(iso_layout)

        source_group.setLayout(source_layout)
        main_layout.addWidget(source_group)

        # Device group
        device_group = QGroupBox("Target USB Device")
        device_layout = QVBoxLayout()
        device_layout.setSpacing(10)

        device_select_layout = QHBoxLayout()
        device_label = QLabel("Select Device:")
        device_label.setMinimumWidth(140)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(35)
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.scan_devices)
        device_select_layout.addWidget(device_label)
        device_select_layout.addWidget(self.device_combo)
        device_select_layout.addWidget(refresh_btn)
        device_layout.addLayout(device_select_layout)

        warning_label = QLabel("⚠️  WARNING: All data on the selected device will be ERASED!")
        warning_label.setStyleSheet(f"color: {DarkTheme.ACCENT_RED}; font-weight: bold; padding: 5px;")
        device_layout.addWidget(warning_label)

        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)

        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.verify_checkbox = QCheckBox("Verify checksum after download")
        options_layout.addWidget(self.verify_checkbox)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Log output
        log_label = QLabel("Log:")
        main_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        main_layout.addWidget(self.log_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.create_button = QPushButton("🚀 Create Bootable USB")
        self.create_button.setObjectName("primaryButton")
        self.create_button.setMinimumWidth(180)
        self.create_button.setMinimumHeight(45)
        self.create_button.clicked.connect(self.start_creation)
        button_layout.addWidget(self.create_button)

        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setMinimumHeight(45)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_creation)
        button_layout.addWidget(self.cancel_button)

        self.clear_button = QPushButton("🗑️ Clear Log")
        self.clear_button.setMinimumWidth(100)
        self.clear_button.setMinimumHeight(45)
        self.clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

    def browse_iso(self):
        """Browse for ISO file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select ISO File",
            str(Path.home()),
            "ISO Files (*.iso);;All Files (*)"
        )
        if filename:
            self.iso_path_edit.setText(filename)

    def scan_devices(self):
        """Scan for USB devices"""
        self.append_log("Scanning for USB devices...", "info")
        self.device_combo.clear()
        self.devices = []

        system = platform.system()

        try:
            if system == "Linux":
                result = subprocess.run(['lsblk', '-d', '-o', 'NAME,SIZE,TYPE,TRAN'],
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n')[1:]:
                    if 'usb' in line:
                        parts = line.split()
                        if parts:
                            device = f"/dev/{parts[0]}"
                            size = parts[1] if len(parts) > 1 else "Unknown"
                            self.devices.append(device)
                            self.device_combo.addItem(f"{device} ({size})")

            elif system == "Windows":
                result = subprocess.run(['wmic', 'diskdrive', 'get', 'deviceid,size,caption'],
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n')[1:]:
                    if 'PHYSICALDRIVE' in line.upper():
                        parts = line.strip().split()
                        if parts:
                            for part in parts:
                                if 'PhysicalDrive' in part:
                                    device = f"\\\\.\\{part}"
                                    self.devices.append(device)
                                    self.device_combo.addItem(device)

            elif system == "Darwin":
                result = subprocess.run(['diskutil', 'list'],
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if '/dev/disk' in line and 'external' in line.lower():
                        parts = line.split()
                        device = parts[0]
                        self.devices.append(device)
                        self.device_combo.addItem(device)

            if self.devices:
                self.append_log(f"Found {len(self.devices)} USB device(s)", "success")
            else:
                self.append_log("No USB devices found", "warning")

        except Exception as e:
            self.append_log(f"Error scanning devices: {e}", "error")

    def append_log(self, message, level="info"):
        """Append message to log"""
        color_map = {
            "info": DarkTheme.FG_SECONDARY,
            "success": DarkTheme.ACCENT_GREEN,
            "error": DarkTheme.ACCENT_RED,
            "warning": DarkTheme.ACCENT_ORANGE
        }

        color = color_map.get(level, DarkTheme.FG_PRIMARY)
        formatted = f'<span style="color: {color};">{message}</span>'

        self.log_text.append(formatted)

        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()
        self.append_log("Log cleared", "info")

    def start_creation(self):
        """Start USB creation process"""
        # Validate inputs
        if not self.devices or self.device_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Device", "Please select a USB device")
            return

        device = self.devices[self.device_combo.currentIndex()]
        iso_path = self.iso_path_edit.text().strip()
        repo = self.repo_edit.text().strip()
        verify = self.verify_checkbox.isChecked()

        if not iso_path and not repo:
            QMessageBox.warning(self, "Invalid Input", "Please specify either a GitHub repository or a local ISO file")
            return

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Confirm Action",
            f"⚠️  WARNING: This will ERASE ALL DATA on {device}\n\nAre you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # Update UI
        self.create_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Creating bootable USB...")
        self.clear_log()

        # Start thread
        self.thread = USBCreatorThread(repo, device, iso_path or None, verify)
        self.thread.log_signal.connect(self.append_log)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.creation_finished)
        self.thread.start()

    def cancel_creation(self):
        """Cancel the creation process"""
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Cancel",
                "Are you sure you want to cancel?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.append_log("Cancelling...", "warning")
                self.thread.stop()

    def creation_finished(self, success, message):
        """Handle creation completion"""
        self.create_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if success:
            self.statusBar().showMessage("Completed successfully!")
            QMessageBox.information(
                self,
                "Success",
                "✅ Bootable USB created successfully!\n\nYou can now boot from this USB device."
            )
        else:
            self.statusBar().showMessage("Failed!")
            QMessageBox.critical(
                self,
                "Failed",
                f"❌ Failed to create bootable USB:\n\n{message}"
            )


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Arch ISO USB Creator")
    app.setOrganizationName("ArchISO")

    # Apply dark theme
    DarkTheme.apply_to_app(app)
    app.setStyleSheet(DarkTheme.get_stylesheet())

    # Create and show main window
    window = USBCreatorGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
