#!/usr/bin/env python3
"""
Archey — User setup screen.
"""

import re
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from theme import MASTER_STYLE, PINK, GREEN, RED, TEXT3


class UserScreen(QWidget):
    confirmed = pyqtSignal(str, str, str)
    back      = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(MASTER_STYLE)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 32)
        root.setSpacing(6)

        t = QLabel("User Setup"); t.setObjectName("title")
        s = QLabel("Create your account and set the system hostname.\nDo not forget your Keyboard will change layout.")
        s.setObjectName("sub")
        root.addWidget(t); root.addWidget(s)
        root.addSpacing(8)

        root.addWidget(self._sec("HOSTNAME"))
        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("e.g. Archey-Root")
        self.hostname_input.textChanged.connect(self._validate)
        root.addWidget(self.hostname_input)
        h = QLabel("Letters, numbers and hyphens only.")
        h.setObjectName("hint"); root.addWidget(h)

        root.addWidget(self._sec("USERNAME"))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("e.g. archey_dev")
        self.user_input.textChanged.connect(self._validate)
        root.addWidget(self.user_input)
        u = QLabel("Lowercase letters, numbers and underscores.")
        u.setObjectName("hint"); root.addWidget(u)

        root.addWidget(self._sec("PASSWORD"))
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.textChanged.connect(self._validate)
        root.addWidget(self.pw_input)

        root.addWidget(self._sec("CONFIRM PASSWORD"))
        self.pw2_input = QLineEdit()
        self.pw2_input.setPlaceholderText("Confirm password")
        self.pw2_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw2_input.textChanged.connect(self._validate)
        root.addWidget(self.pw2_input)

        self.pw_status = QLabel("")
        self.pw_status.setObjectName("hint")
        root.addWidget(self.pw_status)

        root.addStretch()

        btn_row = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back.emit)

        self.confirm_btn = QPushButton("Continue →")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(self.back_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.confirm_btn)
        root.addLayout(btn_row)

    def _sec(self, text):
        l = QLabel(text); l.setObjectName("sec")
        return l

    def _validate(self):
        hostname = self.hostname_input.text()
        username = self.user_input.text()
        pw       = self.pw_input.text()
        pw2      = self.pw2_input.text()

        host_ok = bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}$', hostname))
        user_ok = bool(re.match(r'^[a-z_][a-z0-9_]{0,31}$', username))
        pw_ok   = len(pw) >= 4
        match   = pw == pw2 and pw != ""

        self._set_valid(self.hostname_input, host_ok if hostname else None)
        self._set_valid(self.user_input,     user_ok if username else None)
        self._set_valid(self.pw_input,       pw_ok   if pw else None)
        self._set_valid(self.pw2_input,      match   if pw2 else None)

        if not pw:
            self.pw_status.setText("")
        elif not pw_ok:
            self.pw_status.setText("Password must be at least 4 characters")
            self.pw_status.setStyleSheet(f"color: {RED}; font-size: 11px;")
        elif pw2 and not match:
            self.pw_status.setText("Passwords do not match")
            self.pw_status.setStyleSheet(f"color: {RED}; font-size: 11px;")
        elif match:
            self.pw_status.setText("✓ Passwords match")
            self.pw_status.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        else:
            self.pw_status.setText("")

        self.confirm_btn.setEnabled(host_ok and user_ok and pw_ok and match)

    def _set_valid(self, widget, state):
        widget.setProperty("valid", "" if state is None else ("true" if state else "false"))
        widget.setStyle(widget.style())

    def _on_confirm(self):
        self.confirmed.emit(
            self.hostname_input.text(),
            self.user_input.text(),
            self.pw_input.text()
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    s = UserScreen()
    s.confirmed.connect(lambda h, u, p: print(f"host={h} user={u}"))
    s.show()
    sys.exit(app.exec())
