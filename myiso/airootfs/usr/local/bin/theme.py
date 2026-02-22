"""
Shared theme, stylesheet, and animated transition helper for ArchInstall.
Design direction: Dark Rose — deep charcoal with hot pink / cherry blossom accents.
"""

from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Qt
from PyQt6.QtGui import QColor

# ── Palette ───────────────────────────────────────────────────────────────────

BG        = "#12111a"       # near-black background
BG2       = "#1a1825"       # card / panel bg
BG3       = "#221f2e"       # hover / active
BORDER    = "#2e2b3d"       # subtle border
PINK      = "#ff6b9d"       # primary accent — hot pink
PINK2     = "#ff8fb8"       # lighter pink hover
ROSE      = "#e8557a"       # deeper rose
PINK_DIM  = "#3d1f2d"       # muted pink bg
TEXT      = "#f0e6f0"       # near-white with warm tint
TEXT2     = "#9e8fa8"       # muted secondary text
TEXT3     = "#5a5068"       # very muted / disabled
GREEN     = "#7edd9a"       # success
YELLOW    = "#f5c97a"       # warning
RED       = "#ff6b6b"       # error / danger

# ── Master stylesheet ─────────────────────────────────────────────────────────

MASTER_STYLE = f"""
/* ── Base ── */
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'IBM Plex Mono', 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {BG2}; width: 6px; border-radius: 3px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 3px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {PINK}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Labels ── */
QLabel {{ background: transparent; }}
QLabel#title {{
    font-size: 26px; font-weight: bold; color: {PINK};
    letter-spacing: 1px;
}}
QLabel#sub   {{ font-size: 12px; color: {TEXT2}; }}
QLabel#sec   {{
    font-size: 11px; font-weight: bold; color: {PINK};
    letter-spacing: 2px; text-transform: uppercase;
    margin-top: 10px;
}}
QLabel#info  {{ font-size: 12px; color: {GREEN}; }}
QLabel#warn  {{ font-size: 12px; color: {YELLOW}; }}
QLabel#err   {{ font-size: 12px; color: {RED}; }}
QLabel#hint  {{ font-size: 11px; color: {TEXT3}; }}
QLabel#ok    {{ font-size: 11px; color: {GREEN}; }}

/* ── Inputs ── */
QLineEdit {{
    background-color: {BG2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: {TEXT};
}}
QLineEdit:focus   {{ border-color: {PINK}; background-color: {BG3}; }}
QLineEdit[valid="true"]  {{ border-color: {GREEN}; }}
QLineEdit[valid="false"] {{ border-color: {RED}; }}

/* ── Lists ── */
QListWidget {{
    background-color: {BG2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 7px;
    color: {TEXT2};
}}
QListWidget::item:selected {{
    background-color: {PINK_DIM};
    color: {PINK};
    border: 1px solid {ROSE};
}}
QListWidget::item:hover {{ background-color: {BG3}; color: {TEXT}; }}

/* ── Radio buttons ── */
QRadioButton {{
    font-size: 13px; color: {TEXT2};
    padding: 9px 12px; border-radius: 8px;
    spacing: 8px;
}}
QRadioButton:checked {{
    color: {PINK}; background-color: {PINK_DIM};
}}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 7px;
    border: 2px solid {BORDER};
    background: {BG2};
}}
QRadioButton::indicator:checked {{
    background: {PINK}; border-color: {PINK};
}}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 6px; background: {BG3}; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {PINK}; width: 18px; height: 18px;
    margin: -6px 0; border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ background: {PINK2}; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ROSE}, stop:1 {PINK});
    border-radius: 3px;
}}

/* ── Progress bar ── */
QProgressBar {{
    border: none; background-color: {BG2};
    border-radius: 5px; height: 8px; text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ROSE}, stop:1 {PINK2});
    border-radius: 5px;
}}

/* ── Text edit (log) ── */
QTextEdit {{
    background-color: {BG2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-size: 11px; color: {TEXT3};
    padding: 10px;
}}

/* ── Buttons ── */
QPushButton {{
    border-radius: 8px; padding: 10px 24px;
    font-size: 13px; font-weight: bold;
    letter-spacing: 0.5px;
}}
QPushButton#primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ROSE}, stop:1 {PINK});
    color: #12111a; border: none;
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {PINK}, stop:1 {PINK2});
}}
QPushButton#primary:disabled {{
    background: {BG3}; color: {TEXT3};
}}
QPushButton#secondary {{
    background: transparent; color: {TEXT3};
    border: 1px solid {BORDER};
}}
QPushButton#secondary:hover {{
    color: {TEXT}; border-color: {TEXT3};
    background: {BG2};
}}
QPushButton#danger {{
    background: {RED}; color: #12111a; border: none;
}}
QPushButton#danger:hover {{ background: #ff8888; }}
"""

# ── Animated page transition ───────────────────────────────────────────────────

def fade_transition(old_widget: QWidget, new_widget: QWidget, duration: int = 220):
    """Fade out old, fade in new. Both must already be in the stack."""

    # Fade out
    fx_out = QGraphicsOpacityEffect(old_widget)
    old_widget.setGraphicsEffect(fx_out)
    anim_out = QPropertyAnimation(fx_out, b"opacity")
    anim_out.setDuration(duration)
    anim_out.setStartValue(1.0)
    anim_out.setEndValue(0.0)
    anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

    # Fade in
    fx_in = QGraphicsOpacityEffect(new_widget)
    new_widget.setGraphicsEffect(fx_in)
    fx_in.setOpacity(0.0)
    anim_in = QPropertyAnimation(fx_in, b"opacity")
    anim_in.setDuration(duration)
    anim_in.setStartValue(0.0)
    anim_in.setEndValue(1.0)
    anim_in.setEasingCurve(QEasingCurve.Type.InCubic)

    group = QParallelAnimationGroup()
    group.addAnimation(anim_out)
    group.addAnimation(anim_in)

    # Keep reference alive
    new_widget._anim_group = group
    group.start()
