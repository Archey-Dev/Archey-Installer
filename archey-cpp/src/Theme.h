#pragma once
#include <QString>

namespace Theme {

// ── Palette ──────────────────────────────────────────────────────────────────
constexpr auto BG       = "#12111a";
constexpr auto BG2      = "#1a1825";
constexpr auto BG3      = "#221f2e";
constexpr auto BORDER   = "#2e2b3d";
constexpr auto PINK     = "#ff6b9d";
constexpr auto PINK2    = "#ff8fb8";
constexpr auto ROSE     = "#e8557a";
constexpr auto PINK_DIM = "#3d1f2d";
constexpr auto TEXT     = "#f0e6f0";
constexpr auto TEXT2    = "#9e8fa8";
constexpr auto TEXT3    = "#5a5068";
constexpr auto GREEN    = "#7edd9a";
constexpr auto YELLOW   = "#f5c97a";
constexpr auto RED      = "#ff6b6b";

inline QString stylesheet() {
    return QString(R"(
QMainWindow, QWidget {
    background-color: #12111a;
    color: #f0e6f0;
    font-family: 'IBM Plex Mono', 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #1a1825; width: 6px; border-radius: 3px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #2e2b3d; border-radius: 3px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #ff6b9d; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLabel { background: transparent; }
QLabel#title {
    font-size: 26px; font-weight: bold; color: #ff6b9d; letter-spacing: 1px;
}
QLabel#sub   { font-size: 12px; color: #9e8fa8; }
QLabel#sec   { font-size: 11px; font-weight: bold; color: #ff6b9d; letter-spacing: 2px; margin-top: 10px; }
QLabel#info  { font-size: 12px; color: #7edd9a; }
QLabel#warn  { font-size: 12px; color: #f5c97a; }
QLabel#err   { font-size: 12px; color: #ff6b6b; }
QLabel#hint  { font-size: 11px; color: #5a5068; }
QLabel#ok    { font-size: 11px; color: #7edd9a; }

QLineEdit {
    background-color: #1a1825;
    border: 1px solid #2e2b3d;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #f0e6f0;
}
QLineEdit:focus   { border-color: #ff6b9d; background-color: #221f2e; }

QListWidget {
    background-color: #1a1825;
    border: 1px solid #2e2b3d;
    border-radius: 10px;
    padding: 4px;
    outline: none;
}
QListWidget::item { padding: 10px 14px; border-radius: 7px; color: #9e8fa8; }
QListWidget::item:selected {
    background-color: #3d1f2d; color: #ff6b9d; border: 1px solid #e8557a;
}
QListWidget::item:hover { background-color: #221f2e; color: #f0e6f0; }

QRadioButton { font-size: 13px; color: #9e8fa8; padding: 9px 12px; border-radius: 8px; spacing: 8px; }
QRadioButton:checked { color: #ff6b9d; background-color: #3d1f2d; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #2e2b3d; background: #1a1825; }
QRadioButton::indicator:checked { background: #ff6b9d; border-color: #ff6b9d; }

QSlider::groove:horizontal { height: 6px; background: #221f2e; border-radius: 3px; }
QSlider::handle:horizontal { background: #ff6b9d; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { background: #ff8fb8; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #e8557a, stop:1 #ff6b9d);
    border-radius: 3px;
}

QProgressBar {
    border: none; background-color: #1a1825; border-radius: 5px; height: 8px; text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #e8557a, stop:1 #ff8fb8);
    border-radius: 5px;
}

QTextEdit {
    background-color: #1a1825; border: 1px solid #2e2b3d; border-radius: 10px;
    font-size: 11px; color: #5a5068; padding: 10px;
}

QPushButton {
    border-radius: 8px; padding: 10px 24px;
    font-size: 13px; font-weight: bold; letter-spacing: 0.5px;
    min-height: 44px;
}
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #e8557a, stop:1 #ff6b9d);
    color: #12111a; border: none;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff6b9d, stop:1 #ff8fb8);
}
QPushButton#primary:disabled { background: #221f2e; color: #5a5068; }
QPushButton#secondary { background: transparent; color: #5a5068; border: 1px solid #2e2b3d; }
QPushButton#secondary:hover { color: #f0e6f0; border-color: #5a5068; background: #1a1825; }
QPushButton#danger { background: #ff6b6b; color: #12111a; border: none; }
QPushButton#danger:hover { background: #ff8888; }

QCheckBox { font-size: 13px; color: #9e8fa8; padding: 6px; spacing: 8px; }
QCheckBox:checked { color: #ff6b9d; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 2px solid #2e2b3d; background: #1a1825; }
QCheckBox::indicator:checked { background: #ff6b9d; border-color: #ff6b9d; }

QComboBox {
    background: #1a1825; border: 1px solid #2e2b3d; border-radius: 8px;
    padding: 8px 12px; color: #f0e6f0;
}
QComboBox:focus { border-color: #ff6b9d; }
QComboBox QAbstractItemView {
    background: #1a1825; border: 1px solid #2e2b3d; color: #f0e6f0; selection-background-color: #3d1f2d;
}
)");
}


// Inline button styles — use these if objectName stylesheet doesn't apply
inline QString primaryBtn() {
    return "QPushButton {"
           "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e8557a,stop:1 #ff6b9d);"
           "color:#12111a;border:none;border-radius:8px;padding:10px 24px;"
           "font-size:13px;font-weight:bold;min-height:44px;min-width:100px;"
           "}"
           "QPushButton:hover{"
           "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ff6b9d,stop:1 #ff8fb8);"
           "}";
}
inline QString secondaryBtn() {
    return "QPushButton {"
           "background:transparent;color:#9e8fa8;border:1px solid #2e2b3d;"
           "border-radius:8px;padding:10px 24px;font-size:13px;"
           "font-weight:bold;min-height:44px;min-width:80px;"
           "}"
           "QPushButton:hover{color:#f0e6f0;border-color:#5a5068;background:#1a1825;}";
}

} // namespace Theme
