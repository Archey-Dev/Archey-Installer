#!/usr/bin/env python3
"""
Archey — Package search screen.
Syncs pacman db then searches via pacman -Ss.
"""

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget,
    QListWidgetItem, QFrame, QSplitter, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor
from theme import (MASTER_STYLE, PINK, PINK_DIM, ROSE, BG, BG2, BG3,
                   BORDER, TEXT, TEXT2, TEXT3, GREEN, YELLOW)


# ── DB sync worker ────────────────────────────────────────────────────────────

FALLBACK_MIRRORLIST = """
# Archey fallback mirrorlist
Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch
Server = https://mirror.rackspace.com/archlinux/$repo/os/$arch
Server = https://mirrors.kernel.org/archlinux/$repo/os/$arch
Server = https://mirrors.mit.edu/archlinux/$repo/os/$arch
Server = https://www.mirrorservice.org/sites/ftp.archlinux.org/$repo/os/$arch
Server = https://mirror.selfnet.de/archlinux/$repo/os/$arch
Server = https://mirrors.ircam.fr/pub/archlinux/$repo/os/$arch
Server = https://mirror.nl.leaseweb.net/archlinux/$repo/os/$arch
"""

class SyncWorker(QThread):
    done   = pyqtSignal()
    error  = pyqtSignal(str)
    status = pyqtSignal(str)

    def run(self):
        # Step 1: Ensure mirrorlist has servers
        self.status.emit("Checking mirrorlist…")
        try:
            with open("/etc/pacman.d/mirrorlist") as f:
                current = f.read()
            if not any(l.startswith("Server") for l in current.splitlines()):
                with open("/etc/pacman.d/mirrorlist", "w") as f:
                    f.write(FALLBACK_MIRRORLIST)
        except Exception:
            try:
                with open("/etc/pacman.d/mirrorlist", "w") as f:
                    f.write(FALLBACK_MIRRORLIST)
            except Exception:
                pass

        # Step 2: Reflector (non-fatal, short timeout)
        self.status.emit("Finding fastest mirrors…")
        try:
            subprocess.run(
                ["reflector", "--latest", "10", "--sort", "rate",
                 "--connection-timeout", "3", "--download-timeout", "3",
                 "--save", "/etc/pacman.d/mirrorlist"],
                capture_output=True, text=True, timeout=45
            )
        except Exception:
            pass

        # Step 3: Init keyring only if needed
        self.status.emit("Checking keyring…")
        try:
            result = subprocess.run(
                ["pacman-key", "--list-keys"],
                capture_output=True, timeout=10
            )
            if result.returncode != 0:
                self.status.emit("Initialising keyring (this may take a minute)…")
                subprocess.run(["pacman-key", "--init"],
                               capture_output=True, timeout=120)
                subprocess.run(["pacman-key", "--populate", "archlinux"],
                               capture_output=True, timeout=120)
        except Exception:
            pass

        # Step 4: Sync databases
        self.status.emit("Syncing package databases…")
        try:
            result = subprocess.run(
                ["pacman", "-Sy", "--noconfirm"],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0:
                self.error.emit(result.stdout + result.stderr)
            else:
                self.done.emit()
        except subprocess.TimeoutExpired:
            self.error.emit("Database sync timed out — check your internet connection.")
        except FileNotFoundError:
            self.error.emit("pacman not found.")
        except Exception as e:
            self.error.emit(str(e))


# ── Search worker ─────────────────────────────────────────────────────────────

class SearchWorker(QThread):
    results_ready  = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            result = subprocess.run(
                ["pacman", "-Ss", self.query],
                capture_output=True, text=True, timeout=20
            )
            # pacman -Ss returns exit 1 if no results — that's fine
            self.results_ready.emit(self._parse(result.stdout))
        except subprocess.TimeoutExpired:
            self.error_occurred.emit("Search timed out.")
        except FileNotFoundError:
            self.error_occurred.emit("pacman not found.")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _parse(self, raw: str) -> list:
        packages = []
        lines = raw.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            # Package header line is NOT indented and contains repo/name
            if line and not line[0].isspace() and "/" in line:
                parts = line.split()
                if not parts:
                    i += 1
                    continue
                repo_name = parts[0]
                version   = parts[1] if len(parts) > 1 else ""
                installed = len(parts) > 2 and "[installed]" in line
                repo, _, name = repo_name.partition("/")
                desc = ""
                # Description is next line, indented with spaces
                if i + 1 < len(lines) and lines[i + 1] and lines[i + 1][0].isspace():
                    desc = lines[i + 1].strip()
                    i += 1
                packages.append({
                    "name": name, "repo": repo,
                    "version": version, "desc": desc,
                    "installed": installed,
                })
            i += 1
        return packages[:100]


# ── Main screen ───────────────────────────────────────────────────────────────

class PackagesScreen(QWidget):
    confirmed = pyqtSignal(list)
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._selected: dict[str, dict] = {}
        self._search_worker = None
        self._sync_worker   = None
        self._db_synced     = False
        self._search_timer  = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._build_ui()
        # Sync db as soon as screen loads
        QTimer.singleShot(200, self._sync_db)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(10)

        t = QLabel("Package Search"); t.setObjectName("title")
        s = QLabel("Search the full Arch repository and pick packages to install.")
        s.setObjectName("sub")
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(4)

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search packages...  e.g. neovim, discord, docker")
        self.search_input.setFixedHeight(42)
        self.search_input.setEnabled(False)
        self.search_input.textChanged.connect(self._on_search_changed)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.setFixedHeight(42)
        self.clear_btn.clicked.connect(self._clear_search)

        search_row.addWidget(self.search_input, stretch=1)
        search_row.addWidget(self.clear_btn)
        root.addLayout(search_row)

        # Sync spinner + status
        sync_row = QHBoxLayout()
        self._sync_spinner = QProgressBar()
        self._sync_spinner.setRange(0, 0)
        self._sync_spinner.setFixedHeight(4)
        self._sync_spinner.setFixedWidth(120)
        self._sync_spinner.setTextVisible(False)
        sync_row.addWidget(self._sync_spinner)

        self.status_lbl = QLabel("Syncing package database (pacman -Sy)...")
        self.status_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")
        sync_row.addWidget(self.status_lbl, stretch=1)
        root.addLayout(sync_row)

        # Splitter: results | selected
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; width: 1px; }}")

        # Left — results
        left = QWidget(); left.setStyleSheet("background: transparent;")
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,8,0); lv.setSpacing(6)
        res_lbl = QLabel("RESULTS"); res_lbl.setObjectName("sec")
        lv.addWidget(res_lbl)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background: {BG2}; border: 1px solid {BORDER};
                border-radius: 10px; padding: 4px; outline: none;
            }}
            QListWidget::item {{
                padding: 6px 12px; border-radius: 6px;
                color: {TEXT2}; font-size: 12px;
            }}
            QListWidget::item:selected {{ background: {PINK_DIM}; color: {PINK}; }}
            QListWidget::item:hover {{ background: {BG3}; color: {TEXT}; }}
        """)
        self.results_list.itemDoubleClicked.connect(self._add_selected)
        lv.addWidget(self.results_list, stretch=1)

        # Description panel
        self.desc_lbl = QLabel("")
        self.desc_lbl.setObjectName("hint")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFixedHeight(36)
        self.results_list.currentItemChanged.connect(self._on_result_hover)
        lv.addWidget(self.desc_lbl)

        add_btn = QPushButton("Add ->")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_selected)
        lv.addWidget(add_btn)

        # Right — selected
        right = QWidget(); right.setStyleSheet("background: transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(8,0,0,0); rv.setSpacing(6)
        sel_lbl = QLabel("SELECTED"); sel_lbl.setObjectName("sec")
        rv.addWidget(sel_lbl)

        self.selected_list = QListWidget()
        self.selected_list.setStyleSheet(f"""
            QListWidget {{
                background: {BG2}; border: 1px solid {BORDER};
                border-radius: 10px; padding: 4px; outline: none;
            }}
            QListWidget::item {{
                padding: 6px 12px; border-radius: 6px; color: {TEXT};
            }}
            QListWidget::item:selected {{ background: {PINK_DIM}; color: {PINK}; }}
            QListWidget::item:hover {{ background: {BG3}; }}
        """)
        rv.addWidget(self.selected_list, stretch=1)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("secondary")
        remove_btn.clicked.connect(self._remove_selected)
        rv.addWidget(remove_btn)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([600, 280])
        root.addWidget(splitter, stretch=1)

        self.count_lbl = QLabel("0 packages selected")
        self.count_lbl.setObjectName("info")
        root.addWidget(self.count_lbl)

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

    # ── DB sync ───────────────────────────────────────────────────────────────

    def _sync_db(self):
        self._sync_spinner.setVisible(True)
        self.status_lbl.setText("Syncing package database...")
        self.status_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")
        self._sync_worker = SyncWorker()
        self._sync_worker.done.connect(self._on_sync_done)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.status.connect(lambda msg: (
            self.status_lbl.setText(msg),
            self.status_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")
        ))
        self._sync_worker.start()

    def _on_sync_done(self):
        self._db_synced = True
        self.search_input.setEnabled(True)
        self.search_input.setFocus()
        self.status_lbl.setText("Database synced — type to search")
        self.status_lbl.setStyleSheet(f"color: {GREEN}; font-size: 12px;")
        self._sync_spinner.setVisible(False)

    def _on_sync_error(self, msg: str):
        self._db_synced = True
        self.search_input.setEnabled(True)
        self._sync_spinner.setVisible(False)
        self.status_lbl.setText(f"Sync failed: {msg[:80]}. Search may be limited.")
        self.status_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        if len(text.strip()) < 2:
            self.results_list.clear()
            self.desc_lbl.setText("")
            self.status_lbl.setText("Type at least 2 characters.")
            self.status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
            return
        self._search_timer.start(400)

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.status_lbl.setText(f"Searching for '{query}'...")
        self.status_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        self.results_list.clear()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker.wait()
        self._search_worker = SearchWorker(query)
        self._search_worker.results_ready.connect(self._on_results)
        self._search_worker.error_occurred.connect(self._on_search_error)
        self._search_worker.start()

    def _on_results(self, packages: list):
        self.results_list.clear()
        if not packages:
            self.status_lbl.setText("No results found.")
            self.status_lbl.setStyleSheet(f"color: {TEXT3}; font-size: 12px;")
            return
        n = len(packages)
        self.status_lbl.setText(
            f"{n} result(s)  —  double-click or press Add to select"
        )
        self.status_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        for pkg in packages:
            tag = " [installed]" if pkg["installed"] else ""
            sel = " [+]" if pkg["name"] in self._selected else ""
            text = f"{pkg['repo']}/{pkg['name']}  {pkg['version']}{tag}{sel}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, pkg)
            if pkg["name"] in self._selected:
                item.setForeground(QColor(PINK))
            self.results_list.addItem(item)

    def _on_search_error(self, msg: str):
        self.status_lbl.setText(f"Error: {msg}")
        self.status_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px;")

    def _on_result_hover(self, current, _):
        if current:
            pkg = current.data(Qt.ItemDataRole.UserRole)
            self.desc_lbl.setText(pkg.get("desc", "") if pkg else "")

    def _clear_search(self):
        self.search_input.clear()
        self.results_list.clear()
        self.desc_lbl.setText("")
        self.status_lbl.setText("Ready — type to search")
        self.status_lbl.setStyleSheet(f"color: {GREEN}; font-size: 12px;")

    # ── Selection ─────────────────────────────────────────────────────────────

    def _add_selected(self):
        items = self.results_list.selectedItems()
        if not items:
            return
        for item in items:
            pkg = item.data(Qt.ItemDataRole.UserRole)
            if pkg and pkg["name"] not in self._selected:
                self._selected[pkg["name"]] = pkg
                li = QListWidgetItem(
                    f"{pkg['name']}  ({pkg['repo']})  {pkg['version']}"
                )
                li.setData(Qt.ItemDataRole.UserRole, pkg)
                self.selected_list.addItem(li)
        self._update_count()
        # Refresh results to show [+] markers
        current_pkgs = [
            self.results_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.results_list.count())
        ]
        self._on_results(current_pkgs)

    def _remove_selected(self):
        items = self.selected_list.selectedItems()
        if not items:
            return
        for item in items:
            pkg = item.data(Qt.ItemDataRole.UserRole)
            if pkg:
                self._selected.pop(pkg["name"], None)
            self.selected_list.takeItem(self.selected_list.row(item))
        self._update_count()

    def _update_count(self):
        n = len(self._selected)
        self.count_lbl.setText(
            f"{n} package(s) selected" if n else "0 packages selected"
        )

    def _on_confirm(self):
        self.confirmed.emit(list(self._selected.keys()))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = PackagesScreen()
    s.confirmed.connect(lambda pkgs: print(f"Selected: {pkgs}"))
    s.show()
    sys.exit(app.exec())
