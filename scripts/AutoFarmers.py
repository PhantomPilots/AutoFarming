# =============================================================================
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                           🆓 FREE SOFTWARE 🆓                           ║
# ║                                                                          ║
# ║  The AutoFarmers core is FREE and open source. Optional compiled        ║
# ║  extensions may be distributed under separate license terms.           ║
# ║                                                                          ║
# ║  This software is provided "as is" without warranty of any kind.        ║
# ║  Use at your own risk.                                                   ║
# ║                                                                          ║
# ║  Core license: MIT License                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# =============================================================================

# AutoFarmers GUI (PyQt5)
# Dropdown + stacked pages for all farmer scripts, with argument fields, terminal output, and process control.

import codecs
import contextlib
import ctypes
import ctypes.wintypes
import datetime
import hashlib
import json
import math
import os
import random
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field

_DEVTEST_RUNNER_FLAG = "--devtest-runner"
if sys.argv[1:2] == [_DEVTEST_RUNNER_FLAG]:
    from development import main as _devtest_main

    raise SystemExit(_devtest_main(sys.argv[2:]))

from PyQt5.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QRegularExpression,
    QStringListModel,
    Qt,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    QByteArray,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QRegularExpressionValidator,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtSvg import QSvgRenderer

from utilities.app_config import (
    APP_CONFIG_DEFAULTS,
    config,
    get_pause_flag_path,
    load_full_config_dict,
    save_config_updates,
    test_ntfy_connection,
)
from utilities.compiled_extensions import merge_compiled_extensions
from utilities.extension_secrets import load_suite_license_key
from utilities.image_assets import (
    GameVersion,
    get_saved_game_version,
    normalize_game_version,
)
from utilities.logging_utils import remove_expired_logged_images
from utilities.reward_sets import GUILD_BOSS_REWARDS, INDURA_REWARDS, RewardSet

_COMPILED_EXTENSION_RUNNER_FLAG = "--compiled-extension-runner"
if sys.argv[1:2] == [_COMPILED_EXTENSION_RUNNER_FLAG]:
    from compiled_extension_runner import main as _compiled_extension_runner_main

    raise SystemExit(_compiled_extension_runner_main(sys.argv[2:]))

# Free software message to display in GUI
FREE_SOFTWARE_MESSAGE = """=====================================================================
                              FREE SOFTWARE

  The AutoFarmers core is FREE and open source. Optional compiled
  extensions may be distributed under separate license terms.

  This software is provided "as is" without warranty of any kind.
  Use at your own risk.

  Core license: MIT License
=====================================================================

"""

_HALLOWEEN_PUMPKIN = r"""
          __
        _/  \_
   .-'``  ||  ``'-.
  /    /\    /\    \
 |    /__\  /__\    |
 |        /\        |
 |  \^^^^^^^^^^^^/  |
  \  `\/\/\/\/\/`  /
   '-.__________.-'
""".strip("\n").split("\n")

INK_CYAN = "#0093D6"
INK_MAGENTA = "#D6006F"
INK_YELLOW = "#F5C400"
INK_VIOLET = "#5B4EA2"
INK_ORANGE = "#F08300"
INK_SLATE = "#6E6C66"

C_DARK = {
    "bg": "#0f0f17",
    "rail": "#171724",
    "panel": "#171724",
    "panel2": "#1e1e2e",
    "panel3": "#1a1a2e",
    "field": "#0f0f17",
    "border": "#252535",
    "border2": "#2e2e45",
    "accent": "#2DB0F0",
    "accent_light": "#6CCBF7",
    "running": "#21B874",
    "running_hover": "#2FCB85",
    "running_pressed": "#17945C",
    "warning": "#E8B21E",
    "error": "#F0554A",
    "blue": "#2DB0F0",
    "text": "#EEEDE6",
    "dim": "#C4C2BA",
    "muted": "#96948C",
    "dark": "#64625C",
    "darker": "#252535",
    "term_bg": "#16161e",
    "term_text": "#E4E2DA",
    "term_rule": "#5E5C57",
    "tile_bg": "#171724",
    "tile_hover": "#1e1e2e",
    "btn_sec_bg": "transparent",
    "btn_sec_text": "#EEEDE6",
    "home_ink": "#EEEDE6",
    "on_home": "#0f0f17",
}

C_LIGHT = {
    "bg": "#F4F3EE",
    "rail": "#E8E6DE",
    "panel": "#FBFAF7",
    "panel2": "#ECEAE3",
    "panel3": "#EFEDE7",
    "field": "#FFFFFF",
    "border": "#D9D6CB",
    "border2": "#C2BEB1",
    "accent": "#0093D6",
    "accent_light": "#006A9C",
    "running": "#00995A",
    "running_hover": "#00AD66",
    "running_pressed": "#007D4A",
    "warning": "#B07800",
    "error": "#D8352A",
    "blue": "#0093D6",
    "text": "#16161A",
    "dim": "#3F3F46",
    "muted": "#66645E",
    "dark": "#9A978E",
    "darker": "#E2DFD6",
    "term_bg": "#16161e",
    "term_text": "#E4E2DA",
    "term_rule": "#6E6C66",
    "tile_bg": "#FBFAF7",
    "tile_hover": "#FFFFFF",
    "btn_sec_bg": "transparent",
    "btn_sec_text": "#16161A",
    "home_ink": "#1e1e2e",
    "on_home": "#F4F3EE",
}

_WORDMARK_ACCENT_DARK = "#8b5cf6"
_WORDMARK_ACCENT_LIGHT = "#3B82F6"
_WORDMARK_TEXT_DARK = "#e2e8f0"
_WORDMARK_TEXT_LIGHT = "#1A2A44"

C_HALLOWEEN = {
    "bg": "#120C18",
    "rail": "#1A1123",
    "panel": "#1F1529",
    "panel2": "#2A1C38",
    "panel3": "#24182F",
    "field": "#120C18",
    "border": "#33233F",
    "border2": "#45305A",
    "accent": "#FF7A1A",
    "accent_light": "#FFA559",
    "running": "#7ED957",
    "running_hover": "#95E472",
    "running_pressed": "#5FB83C",
    "warning": "#FFB627",
    "error": "#E5384F",
    "blue": "#9B5DE5",
    "text": "#F3E9DC",
    "dim": "#D2C3B4",
    "muted": "#A493AC",
    "dark": "#6B5878",
    "darker": "#33233F",
    "term_bg": "#0B0710",
    "term_text": "#EADFCD",
    "term_rule": "#6B5878",
    "tile_bg": "#1F1529",
    "tile_hover": "#2A1C38",
    "btn_sec_bg": "transparent",
    "btn_sec_text": "#F3E9DC",
    "home_ink": "#FF7A1A",
    "on_home": "#120C18",
}
_HALLOWEEN_INKS = {
    "INK_CYAN": "#3DDC97",
    "INK_MAGENTA": "#9B5DE5",
    "INK_YELLOW": "#FFB627",
    "INK_VIOLET": "#E5384F",
    "INK_ORANGE": "#FF9F43",
    "INK_SLATE": "#6B5878",
}

UI_FONT_FAMILY = "Consolas"
UI_FONT = f"{UI_FONT_FAMILY}, 'Cascadia Mono', monospace"
MONO_FONT = "Consolas, 'Cascadia Mono', monospace"

_ICON_PATHS = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9v12h13V9"/><path d="M10 21v-6h4v6"/>',
    "back": '<path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/>',
    "chevron": '<path d="M9 6l6 6-6 6"/>',
    "play": '<path d="M7 4.5v15l12-7.5z" fill="{c}" stroke="none"/>',
    "resize": '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    "clear": '<path d="M4 7h16"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M6 7l1 13h10l1-13"/>'
    '<path d="M9 7V4h6v3"/>',
    "settings": '<path d="M4 6h9"/><path d="M19 6h1"/><path d="M4 12h3"/><path d="M13 12h7"/><path d="M4 18h11"/>'
    '<circle cx="16" cy="6" r="2.5"/><circle cx="10" cy="12" r="2.5"/><circle cx="18" cy="18" r="2.5"/>',
    "flask": '<path d="M9 3h6"/><path d="M10 3v6.5L4.6 18.8A1.5 1.5 0 0 0 5.9 21h12.2a1.5 1.5 0 0 0 1.3-2.2L14 9.5V3"/>'
    '<path d="M7.5 15h9"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.6v.2"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.6 6.6 0 0 0 10.5 10.5z"/>',
    "paw": '<circle cx="6.5" cy="10" r="1.8"/><circle cx="10" cy="5.8" r="1.8"/><circle cx="14" cy="5.8" r="1.8"/>'
    '<circle cx="17.5" cy="10" r="1.8"/><path d="M8 17.2c0-2.8 1.8-5 4-5s4 2.2 4 5c0 1.5-1.1 2.6-2.5 2.6-.7 0-1-.4-1.5-.4'
    's-.8.4-1.5.4C9.1 19.8 8 18.7 8 17.2z"/>',
    "horns": '<path d="M5 3c0 3.6 1.6 5.8 4 6.8"/><path d="M19 3c0 3.6-1.6 5.8-4 6.8"/><circle cx="12" cy="14.5" r="6"/>'
    '<path d="M9.8 13.6h.01"/><path d="M14.2 13.6h.01"/><path d="M10 17.2c1.2.8 2.8.8 4 0"/>',
    "crown": '<path d="M3.5 8.5l4.2 3.8L12 5l4.3 7.3 4.2-3.8-1.8 10H5.3z"/><path d="M5.5 21h13"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M8 3v4"/><path d="M16 3v4"/>'
    '<path d="M3.5 10h17"/><path d="M9 15.2l2 2 4-4"/>',
    "key": '<circle cx="8" cy="15.5" r="4"/><path d="M10.9 12.6L19 4.5"/><path d="M16 7.5l2.2 2.2"/>'
    '<path d="M13.6 9.9l2 2"/>',
    "grid": '<rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/>'
    '<rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/>',
    "star": '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.2 1 5.8L12 16.9l-5.2 2.8 1-5.8-4.3-4.2 5.9-.8z"/>',
    "star_fill": '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.2 1 5.8L12 16.9l-5.2 2.8 1-5.8-4.3-4.2 5.9-.8z" fill="{c}"/>',
    "gift": '<rect x="3.5" y="8" width="17" height="4" rx="1"/><path d="M5 12v8.5h14V12"/><path d="M12 8v12.5"/>'
    '<path d="M12 8C10.6 4.6 7 4.4 7 6.5 7 7.6 9 8 12 8z"/><path d="M12 8c1.4-3.4 5-3.6 5-1.5 0 1.1-2 1.5-5 1.5z"/>',
    "pumpkin": '<path d="M12 7c-.6-2.2.6-3.8 2.6-4.3"/><ellipse cx="12" cy="14" rx="8.5" ry="6.5"/>'
    '<path d="M12 7.5c-2.2 0-3.6 2.9-3.6 6.5s1.4 6.5 3.6 6.5 3.6-2.9 3.6-6.5-1.4-6.5-3.6-6.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2"/><path d="M12 19.5v2"/><path d="M2.5 12h2"/>'
    '<path d="M19.5 12h2"/><path d="M5.3 5.3l1.4 1.4"/><path d="M17.3 17.3l1.4 1.4"/><path d="M5.3 18.7l1.4-1.4"/>'
    '<path d="M17.3 6.7l1.4-1.4"/>',
}


def _cobweb_pixmap(size: int, color: str) -> QPixmap:
    spokes = "".join(f'<path d="M64 0L{x} {y}"/>' for x, y in ((0, 0), (8, 30), (22, 50), (40, 62), (64, 64)))
    rings = (
        '<path d="M52 0Q54 6 59 8Q60 12 64 12"/>'
        '<path d="M38 0Q41 11 49 15Q51 22 57 24Q60 27 64 27"/>'
        '<path d="M22 0Q27 16 38 22Q41 33 50 37Q55 42 64 43"/>'
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" stroke="{color}"'
        f' stroke-width="1" stroke-linecap="round">{spokes}{rings}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return pixmap


def svg_icon(name: str, color: str, size: int = 16) -> QIcon:
    body = _ICON_PATHS[name].replace("{c}", color)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}"'
        f' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scale = 2
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def _relative_luminance(hex_color: str) -> float:
    color = QColor(hex_color)

    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(color.redF()) + 0.7152 * channel(color.greenF()) + 0.0722 * channel(color.blueF())


def _on_ink(hex_color: str) -> str:
    lum = _relative_luminance(hex_color)
    ink_lum = _relative_luminance("#16161A")
    contrast_white = 1.05 / (lum + 0.05)
    contrast_ink = (lum + 0.05) / (ink_lum + 0.05)
    return "#16161A" if contrast_ink >= contrast_white else "#FFFFFF"


def _tint(hex_color: str, alpha: float) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()},{color.green()},{color.blue()},{alpha})"


# Theme persistence
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_DIR = os.path.join(_BASE_DIR, "config")

os.makedirs(_CONFIG_DIR, exist_ok=True)

_THEME_FILE = os.path.join(_CONFIG_DIR, ".theme")


def _load_theme() -> str:
    try:
        with open(_THEME_FILE) as _f:
            return _f.read().strip()
    except Exception:
        return "dark"


def _save_theme(name: str):
    with open(_THEME_FILE, "w") as _f:
        _f.write(name)


def _restart_application() -> bool:
    if getattr(sys, "frozen", False):
        program = sys.executable
        args = sys.argv[1:]
    else:
        program = sys.executable
        entrypoint = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else os.path.abspath(__file__)
        args = [entrypoint] + sys.argv[1:]

    started = QProcess.startDetached(program, args, _BASE_DIR)
    if isinstance(started, tuple):
        return started[0]
    return bool(started)


_ACTIVE_THEME = _load_theme()
_HALLOWEEN = _ACTIVE_THEME == "halloween"
C = C_HALLOWEEN if _HALLOWEEN else C_LIGHT if _ACTIVE_THEME == "light" else C_DARK
_WORDMARK_ACCENT = _WORDMARK_ACCENT_LIGHT if _ACTIVE_THEME == "light" else _WORDMARK_ACCENT_DARK
_WORDMARK_TEXT = _WORDMARK_TEXT_LIGHT if _ACTIVE_THEME == "light" else _WORDMARK_TEXT_DARK
if _HALLOWEEN:
    globals().update(_HALLOWEEN_INKS)
    _WORDMARK_ACCENT = C_HALLOWEEN["accent"]
    _WORDMARK_TEXT = C_HALLOWEEN["text"]


# Action Button Styles
def _action_btn(base: str, hover: str, pressed: str, color: str = "white") -> str:
    return (
        f"QPushButton {{ background-color: {base}; color: {color}; font-family: {UI_FONT};"
        f" font-size: 13px; font-weight: 700; padding: 9px 10px; border: none; border-radius: 8px; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:pressed {{ background-color: {pressed}; }}"
        f"QPushButton:disabled {{ background-color: {C['panel2']}; color: {C['dark']}; }}"
    )


def _outline_btn(color: str) -> str:
    return (
        f"QPushButton {{ background: transparent; color: {color}; font-family: {UI_FONT};"
        f" font-size: 13px; font-weight: 700; padding: 8px 10px; border: 2px solid {color}; border-radius: 8px; }}"
        f"QPushButton:hover {{ background: {color}; color: {C['bg']}; }}"
        f"QPushButton:pressed {{ background: {color}; color: {C['bg']}; }}"
        f"QPushButton:disabled {{ color: {C['dark']}; border-color: {C['border']}; background: transparent; }}"
    )


def _quiet_btn() -> str:
    return (
        f"QPushButton {{ background: transparent; color: {C['dim']}; font-family: {UI_FONT};"
        f" font-size: 13px; font-weight: 700; padding: 6px 10px; border: 1px solid transparent; border-radius: 8px; }}"
        f"QPushButton:hover {{ border-color: {C['border2']}; color: {C['text']}; background: {C['panel']}; }}"
        f"QPushButton:pressed {{ background: {C['panel2']}; }}"
        f"QPushButton:disabled {{ color: {C['dark']}; }}"
    )


BTN_START = _action_btn(C["running"], C["running_hover"], C["running_pressed"])
BTN_STOP = _outline_btn(C["error"])
BTN_PAUSE = _outline_btn(C["warning"])
BTN_RESIZE = _quiet_btn()
BTN_CLEAR = _quiet_btn()

_DEVTEST_BUTTON_COLORS = (C["panel"], C["panel2"], C["darker"])
BTN_DEVTEST = (
    f"QPushButton {{ background-color: {_DEVTEST_BUTTON_COLORS[0]}; color: {C['text']};"
    f" font-family: {UI_FONT}; font-weight: 700;"
    f" padding: 7px 12px; border: 1px solid {C['border2']}; border-radius: 8px; }}"
    f"QPushButton:hover {{ background-color: {_DEVTEST_BUTTON_COLORS[1]}; border-color: {C['text']}; }}"
    f"QPushButton:pressed {{ background-color: {_DEVTEST_BUTTON_COLORS[2]}; }}"
    f"QPushButton:focus {{ border-color: {C['accent']}; }}"
    f"QPushButton:disabled {{ background-color: {C['panel2']}; color: {C['dark']};"
    f" border-color: {C['border']}; }}"
)

_GUI_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gui_images")


def _make_stylesheet() -> str:
    check_icon = os.path.join(_GUI_IMAGES_DIR, "check.svg").replace("\\", "/")
    return f"""
QWidget {{
    background-color: {C['bg']};
    color: {C['text']};
    font-family: {UI_FONT};
    font-size: 13px;
    selection-background-color: {INK_CYAN};
    selection-color: #16161A;
}}
QToolTip {{
    background: {C['text']};
    color: {C['bg']};
    border: none;
    padding: 6px 8px;
    font-family: {UI_FONT};
    font-size: 12px;
}}
QScrollArea, QAbstractScrollArea {{
    background-color: {C['bg']};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {C['bg']};
}}
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {C['field']};
    border: 1px solid {C['border2']};
    border-radius: 8px;
    color: {C['text']};
    padding: 6px 9px;
    font-size: 13px;
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {C['dark']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {C['accent']};
    padding: 5px 8px;
}}
QLineEdit:disabled {{ color: {C['dark']}; background: {C['panel2']}; }}
QComboBox {{
    background-color: {C['field']};
    border: 1px solid {C['border2']};
    border-radius: 8px;
    color: {C['text']};
    padding: 6px 9px;
    font-size: 13px;
}}
QComboBox:hover {{ border-color: {C['dark']}; }}
QComboBox:focus {{ border-color: {C['accent']}; }}
QComboBox:disabled {{ color: {C['dark']}; background: {C['panel2']}; }}
QComboBox::drop-down {{ border: none; background: transparent; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {C['field']};
    border: 1px solid {C['border2']};
    color: {C['text']};
    selection-background-color: {INK_CYAN};
    selection-color: #16161A;
    outline: none;
    padding: 2px;
}}
QCheckBox {{
    color: {C['text']};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox:disabled {{ color: {C['dark']}; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 2px solid {C['dark']};
    border-radius: 4px;
    background: {C['field']};
}}
QCheckBox::indicator:hover {{ border-color: {C['text']}; }}
QCheckBox::indicator:checked {{
    background: {INK_CYAN};
    border-color: {INK_CYAN};
    image: url({check_icon});
}}
QListWidget {{
    background: {C['field']};
    border: 1px solid {C['border2']};
    border-radius: 8px;
    color: {C['text']};
    font-size: 13px;
}}
QListWidget::item:selected {{
    background: {INK_CYAN};
    color: #16161A;
}}
QListWidget::item:hover {{ background: {C['panel2']}; }}
QGroupBox {{
    border: 1px solid {C['border']};
    border-radius: 8px;
    margin-top: 16px;
    font-size: 13px;
    font-weight: 700;
    color: {C['text']};
    padding: 10px 8px 8px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: -1px;
    padding: 0 6px;
    color: {C['text']};
    background-color: {C['bg']};
}}
QLabel {{ color: {C['text']}; background: transparent; }}
QPushButton {{
    border: 1px solid {C['border2']};
    border-radius: 8px;
    padding: 7px 14px;
    color: {C['text']};
    background: transparent;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton:hover {{ border-color: {C['text']}; background: {C['panel']}; }}
QPushButton:pressed {{ background: {C['panel2']}; }}
QPushButton:focus {{ border-color: {C['accent']}; }}
QPushButton:disabled {{ color: {C['dark']}; border-color: {C['border']}; }}
QProgressBar {{ background: {C['border']}; border: none; border-radius: 0; }}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {C['border2']};
    border-radius: 3px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['dark']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0; background: none;
}}
QScrollBar:horizontal {{ height: 0; background: none; }}
QTextEdit {{
    background: {C['term_bg']};
    color: {C['term_text']};
    border: none;
    font-family: {MONO_FONT};
    font-size: 13px;
    selection-background-color: {INK_CYAN};
    selection-color: #16161A;
}}
QMessageBox QLabel {{ font-size: 13px; }}
"""


APP_STYLESHEET = _make_stylesheet()

# Farmer requirements displayed in the GUI.
REQUIREMENTS = {
    "Demon Farmer": """
<p>If multiple demons are selected, the bot will rotate between them every 2h.</p>
    """,
    "Bird Floor 4": """
<p><strong>Requirements:</strong><br>
• Any team, but best: Thor, G Tyr, Xion, Merlin/Milim Hel</p>
    """,
    "Demonic Beast Rotation": """
<p><strong>Requirements:</strong><br>
• Select Bird, Deer, and/or Dogs<br>
• Runs floors 1-3 once for each selected Demonic Beast, then returns to the Tavern<br>
• Enable Repeat Rotation Indefinitely to loop through the selection until stopped</p>
    """,
    "Deer Farmer": """
<p><strong>Requirements:</strong><br>
• Green Jorm, Thor, Red Freyr, Green Tyr/Green Hel<br>
• NO SKULD</p>
    """,
    "Deer Floor 4": """
<p><strong>Requirements:</strong><br>
• Green Jorm, Thor, Red Freyr, Green Tyr/Green Hel<br>
• <strong>IMPORTANT</strong> (whale mode <strong>off</strong>): The bot is built around finishing <strong>Phase 1 in 3</strong> player turns.
Tune your gear so you can guarantee that.<br>
• NO SKULD</p>
    """,
    "Deer Floor 4 Whale": """
<p><strong>Requirements (Whale mode):</strong><br>
• Same team as normal Deer Floor 4 — <em>not</em> the removed floors 1-3 whale comp<br>
• Targets finishing <strong>Phase 1 in 1</strong> player turn<br>
• Tune your gear/CC to support the aggressive opener<br>
• <strong>IMPORTANT</strong>: NO SKULD</p>
    """,
    "Dogs Floor 4": """
<p><strong>Requirements:</strong><br>
• Escalin, Lillia/Cusack/Roxy(recommended), Nasiens, Thonar</p>
    """,
    "Dogs Floor 4 Whale": """
<p><strong>Whale mode</strong> (consider this a "beefy acc/units only"):<br>
• Team: Escalin, DK Meli + Relic, OG B Gowther + Relic, Nasiens<br>
• Links: Escalin > Roxy LR, DK Meli > Sabunak, OG B Gow > R Tarm, Nasi > NOT Esca UR<br>
• Esca/Meli ATK Crit<br>
• NB: Gowther MUST BE ATK DEF with a super set (14.5%+ all around)<br>
• NB2: Nasi MUST BE HP DEF with 15% DEF rolls AND Orb and Belt MUST NOT HAVE A SINGLE HP ROLL. Put UC pieces.
• NB3: Escalin must be on slot 3 or 4.
</p>
    """,
    "Dogs Farmer": """
<p><strong>Requirements:</strong><br>
• Any team works</p>
    """,
    "Snake Farmer": """
<p><strong>Requirements:</strong><br>
• Old Mael/Tristan, LR Liz, Freyja with relic, Red Marg</p>
    """,
    "Rat Farmer": """
<p><strong>Requirements:</strong><br>
• Red Jorm, LR Liz, Blue Valenti, King-Diane/EscaMerlin<br>
• If using King-Diane, place them to the very right</p>
    """,
    "Snake Whale": """
<p><strong>Requirements:</strong><br>
• 16M+ CC • 6th Constellation (5th ok)<br>
• Atk/Crit gear 14.5%+ (HP/Def for Nasiens)<br>
• Team: Jinwoo, Nasiens, Cha Hae-In, Urek<br>
• Links: Roxy on Jinwoo, UR Escanor on Nasiens, Tarm on Cha, Sab on Urek<br>
• All relics + Cha must have lowest HP</p>
    """,
    "Guild Boss Farmer": """
<p><strong>Requirements:</strong><br>
• Start the bot from within the fight itself<br>
• Nasiens, Sigurd, SJW, Light Escanor (this order)<br>
• Sariel link on SJW and Mael link on Light Escanor</p>
    """,
    "Demon King Farmer": """
<p><strong>Hard</strong><br>
• Team A: Skuld (att/crit), any 3 boosters<br>
• Team B: Anything (not used)</p>
<p><strong>Hell</strong><br>
• Team A: DK Meli, Cusack, Green Gelda, Green Melascula<br>
• Team B: Skuld, Red Freyr, Red Skadi, Blue Matrona</p>
<p><strong>Important:</strong> <em>Use Hell mode only to farm the SSR card</em></p>
    """,
    "Reroll Constellation": """
<p><strong>Requirements:</strong><br>
• Start from after having already rerolled the attribute you want at least once</p>
    """,
    "Accounts Farmer": """
<p>This bot is for people who pilot multiple accounts.<br>
In <code>config\\accounts.yaml</code>, fill the fields with the sync and passwords of each account.
The <code>name</code> field can be any account identifier.
The bot will then rotate through the multiple accounts by closing and re-opening the game.</p>
<strong></p>Requirement:</strong><br>
In the Netmarble Launcher, take a screenshot of the <code>"Run Game"</code> button, and replace
the file <code>run_game.png</code> by it.
</p>
    """,
    "Gold Farmer": """
<p><strong>Requirements:</strong><br>
• If you use skip tickets, make sure to have the <code>"Auto Use Settings"</code> option checked.</p>
    """,
    "Auto Clear Farmer": """
<p>This Farmer will just spend as many skip tickets as you specify on any activity that allows so.</p>
    """,
    "Daily Quests Farmer": """
<p><strong>Requirements:</strong><br>
• START runs daily quests immediately from the standard daily mission flow<br>
• Start from the tavern/tasks context<br>
• Daily PVP can be enabled or disabled with the checkbox above</p>
    """,
}

# Maps base farmer names to whale-mode display overrides.
WHALE_MODE_CONFIG = {
    "Deer Floor 4": {"requirements_key": "Deer Floor 4 Whale", "image": "deer_floor_4.png"},
    "Dogs Floor 4": {"requirements_key": "Dogs Floor 4 Whale", "image": "dogs_whale.png"},
    "Snake Farmer": {"requirements_key": "Snake Whale", "image": "snake_whale_farmer.png"},
}

FARMER_IMAGES = {
    "Demon Farmer": "demon_farmer.jpg",
    "Demonic Beast Rotation": "db_rotation_farmer.jpg",
    "Bird Farmer": "bird_farmer.jpg",
    "Bird Floor 4": "bird_floor_4.jpeg",
    "Deer Farmer": "deer_farmer.png",
    "Deer Floor 4": "deer_floor_4.png",
    "Dogs Farmer": "dogs_farmer.jpeg",
    "Dogs Floor 4": "dogs_floor_4.jpeg",
    "Tower Trials": "tower_trials_farmer.jpg",
    "Snake Farmer": "snake_farmer.png",
    "Rat Farmer": "rat_farmer.jpg",
    "Final Boss": "final_boss.png",
    "Legendary Boss": "legendary_boss.png",
    "Accounts Farmer": "accounts_farmer.jpg",
    "Daily Quests Farmer": "daily_farmer.png",
    "Reroll Constellation": "reroll_constellation_whale.jpg",
    "SA Coin Dungeon Farmer": "sa_coin_farmer.png",
    "Guild Boss Farmer": "guild_boss_farmer.jpg",
    "Demon King Farmer": "dk_farmer.jpg",
    "Boss Battle Farmer": "boss_battle_farmer.png",
    "Gold Farmer": "gold_farmer.jpg",
    "Auto Clear Farmer": "autoticket_farmer.jpg",
}


def get_farmer_display_content(farmer_name: str, whale_enabled: bool = False) -> tuple[str, str]:
    """Return the requirements key and image filename for the current farmer display state."""
    requirements_key = farmer_name
    image_filename = FARMER_IMAGES.get(farmer_name)

    if whale_enabled:
        whale_config = WHALE_MODE_CONFIG.get(farmer_name)
        if whale_config:
            requirements_key = whale_config["requirements_key"]
            image_filename = whale_config["image"]

    return requirements_key, image_filename


def get_farmer_image_path(farmer: dict, image_filename=None) -> str | None:
    """Return the normalized image path for a built-in or compiled farmer."""
    if image_filename is None and farmer.get("compiled_extension"):
        return farmer.get("image_path")
    if image_filename is None:
        image_filename = FARMER_IMAGES.get(farmer["name"])
    if image_filename is None:
        return None
    return os.path.join(_GUI_IMAGES_DIR, image_filename)


# Farmer script definitions (argument structure)
DAILY_PVP_ARG = {
    "name": "--daily-pvp",
    "false_name": "--no-daily-pvp",
    "label": "Daily PVP",
    "type": "checkbox",
    "default": True,
}


FARMERS = [
    {
        "name": "Demon Farmer",
        "script": "DemonFarmer.py",
        "image_log_subdirs": ["demons"],
        "args": [
            {
                "name": "--demons-to-farm",
                "label": "Demons to Farm",
                "type": "multiselect",
                "choices": ["og_demon", "bell_demon", "red_demon", "gray_demon", "crimson_demon"],
                "labels": ["OG Demon", "Bell Demon", "Red Demon", "Gray Demon", "Crimson Demon"],
                "default": ["og_demon"],
            },
            {"name": "--time-to-sleep", "label": "Wait before Accept (s)", "type": "text", "default": "9.3"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Guild Boss Farmer",
        "script": "GuildBossFarmer.py",
        "args": [
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Bird Farmer",
        "script": "BirdFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Bird Floor 4",
        "script": "BirdFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Deer Farmer",
        "script": "DeerFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Deer Floor 4",
        "script": "DeerFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Dogs Farmer",
        "script": "DogsFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Dogs Floor 4",
        "script": "DogsFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Snake Farmer",
        "script": "SnakeFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Rat Farmer",
        "script": "RatFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Demonic Beast Rotation",
        "script": "DemonicBeastRotationFarmer.py",
        "args": [
            {
                "name": "--beasts-to-farm",
                "label": "Beasts to Farm",
                "type": "multiselect",
                "choices": ["bird", "deer", "dogs"],
                "labels": ["Bird", "Deer", "Dogs"],
                "default": ["bird", "deer", "dogs"],
            },
            {
                "name": "--repeat-rotation",
                "label": "Repeat Rotation Indefinitely",
                "type": "checkbox",
                "default": False,
            },
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Demon King Farmer",
        "script": "DemonKingFarmer.py",
        "args": [
            {
                "name": "--dk-diff",
                "label": "Difficulty",
                "type": "dropdown",
                "choices": ["hard", "hell"],
                "default": "hard",
            },
            {"name": "--num-clears", "label": "Num clears", "type": "text", "default": "10"},
        ],
    },
    {
        "name": "Final Boss",
        "script": "FinalBossFarmer.py",
        "args": [
            {
                "name": "--difficulty",
                "label": "Difficulty",
                "type": "dropdown",
                "choices": ["hard", "extreme", "hell", "challenge"],
                "default": "hell",
            },
            {"name": "--clears", "label": "Clears", "type": "text", "default": "20"},
        ],
    },
    {
        "name": "Gold Farmer",
        "script": "GoldFarmer.py",
        "args": [
            {"name": "--use-skip-tickets", "label": "Use skip tickets", "type": "checkbox", "default": False},
            {
                "name": "--max-skip-tickets-to-use",
                "label": "Max skip tickets to use",
                "type": "text",
                "default": "inf",
            },
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Legendary Boss",
        "script": "LegendaryBossFarmer.py",
        "args": [
            {
                "name": "--difficulty",
                "label": "Difficulty",
                "type": "dropdown",
                "choices": ["extreme", "hell", "challenge"],
                "default": "hell",
            },
            {"name": "--clears", "label": "Clears", "type": "text", "default": "20"},
        ],
    },
    {
        "name": "SA Coin Dungeon Farmer",
        "script": "SADungeonFarmer.py",
        "image_log_subdirs": ["sa_images"],
        "args": [
            {
                "name": "--min-chest-type",
                "label": "Min chest type",
                "type": "dropdown",
                "choices": ["bronze", "silver", "gold"],
                "default": "bronze",
            },
            {"name": "--chest-detection-count", "label": "Chest Detection Retry Count", "type": "text", "default": "3"},
        ],
    },
    {
        "name": "Daily Quests Farmer",
        "script": "DailyQuestsFarmer.py",
        "args": [
            DAILY_PVP_ARG,
        ],
    },
    {
        "name": "Accounts Farmer",
        "script": "AccountsFarmer.py",
        "args": [
            # {"name": "--do-weeklies", "label": "Do Weeklies", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Reroll Constellation",
        "script": "RerollConstellation.py",
        "args": [{"name": "--max-rerolls", "label": "Max rerolls", "type": "text", "default": "50"}],
    },
    {
        "name": "Boss Battle Farmer",
        "script": "BossBattleFarmer.py",
        "args": [],
    },
    {
        "name": "Auto Clear Farmer",
        "script": "AutoClearFarmer.py",
        "args": [{"name": "--max-tickets", "label": "Max tickets", "type": "text", "default": "50"}],
    },
]

FARMERS, _COMPILED_EXTENSION_WARNINGS = merge_compiled_extensions(FARMERS, os.path.join(_BASE_DIR, "vendor"))
for _extension_warning in _COMPILED_EXTENSION_WARNINGS:
    print(f"[WARNING] {_extension_warning}", file=sys.stderr)

_UPTIME_CYCLE_SECS = 12 * 3600  # Session uptime bar resets every 12 hours
_WAIT_BEFORE_ACCEPT_CONFIG_KEYS = {
    "DemonFarmer.py": "demon_wait_before_accept_seconds",
    "indura_farmer": "indura_wait_before_accept_seconds",
}


def _valid_wait_before_accept(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(seconds) and seconds >= 0


@dataclass(frozen=True)
class FarmerStatusSnapshot:
    display_name: str
    is_running: bool
    is_paused: bool
    process_id: int
    session_clears: int
    session_pots: int
    session_losses: int
    session_max_clears: int | None
    session_start_time: float | None
    last_clear_time: datetime.datetime | None
    session_rewards: dict = field(default_factory=dict)  # item key -> total this session
    last_rewards: dict = field(default_factory=dict)  # item key -> count of the latest run
    reward_runs: int = 0  # runs whose rewards were read


_REWARDS_MARKER = "[REWARDS]"
# Farmers whose '[REWARDS]' output is shown in a rewards panel, with the rewards they can read
REWARD_SETS: dict[str, RewardSet] = {
    "Indura Farmer": INDURA_REWARDS,
    "Guild Boss Farmer": GUILD_BOSS_REWARDS,
}


class FarmerController(QObject):
    running_changed = pyqtSignal(bool, int)
    paused_changed = pyqtSignal(bool)
    output_appended = pyqtSignal(str)
    output_reset = pyqtSignal()
    session_progress_changed = pyqtSignal()
    status_snapshot_changed = pyqtSignal(object)
    arg_values_changed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    devtest_busy_changed = pyqtSignal(bool)
    rewards_changed = pyqtSignal()

    def __init__(self, farmer_def: dict, password_supplier=None, parent=None):
        super().__init__(parent)
        self.farmer = farmer_def
        self._password_supplier = password_supplier
        self.process = None
        self.output_lines: list[str] = []
        self.paused = False
        self.devtest_busy = False
        self._session_clears = 0
        self._session_pots = 0
        self._session_losses = 0
        self._session_max_clears = None
        self._session_start_time = None
        self._pause_start_time = None
        self._last_clear_time = None
        self._session_rewards: dict[str, int] = {}
        self._last_rewards: dict[str, int] = {}
        self._reward_runs = 0
        self._process_exit_expected = False
        self.ended_on_its_own = False
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_session_progress)
        self._output_timer = QTimer(self)
        self._output_timer.timeout.connect(self.check_output)
        self._arg_values = self._build_default_arg_values()

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.state() == QProcess.Running

    @property
    def is_paused(self) -> bool:
        return self.paused

    @property
    def session_clears(self) -> int:
        return self._session_clears

    @property
    def session_max_clears(self) -> int | None:
        return self._session_max_clears

    @property
    def session_start_time(self) -> float | None:
        return self._session_start_time

    @property
    def last_clear_time(self) -> datetime.datetime | None:
        return self._last_clear_time

    @property
    def process_id(self) -> int:
        if self.process is None:
            return 0
        return int(self.process.processId())

    def get_status_snapshot(self) -> FarmerStatusSnapshot:
        return FarmerStatusSnapshot(
            display_name=self.farmer["name"],
            is_running=self.is_running,
            is_paused=self.is_paused,
            process_id=self.process_id,
            session_clears=self._session_clears,
            session_pots=self._session_pots,
            session_losses=self._session_losses,
            session_max_clears=self._session_max_clears,
            session_start_time=self._session_start_time,
            last_clear_time=self._last_clear_time,
            session_rewards=dict(self._session_rewards),
            last_rewards=dict(self._last_rewards),
            reward_runs=self._reward_runs,
        )

    def get_arg_values(self) -> dict[str, object]:
        values = {}
        for arg in self.farmer["args"]:
            value = self._arg_values.get(arg["name"])
            if isinstance(value, list):
                values[arg["name"]] = list(value)
            else:
                values[arg["name"]] = value
        return values

    def set_arg_value(self, arg_name: str, value):
        if isinstance(value, list):
            normalized = list(value)
        else:
            normalized = value
        current = self._arg_values.get(arg_name)
        if current == normalized:
            return
        self._arg_values[arg_name] = normalized
        self.arg_values_changed.emit(self.get_arg_values())

    def start(self, arg_values: dict[str, object]):
        if self._blocked_by_devtest():
            return
        if self.process is not None:
            return

        availability_error = self.farmer.get("availability_error")
        if availability_error:
            message = f"[ERROR] {self.farmer['name']} is unavailable: {availability_error}\n"
            self._append_output(message)
            self.error_occurred.emit(availability_error)
            return

        for name, value in arg_values.items():
            self.set_arg_value(name, value)

        for arg in self.farmer["args"]:
            if arg["type"] == "text" and "choices" in arg:
                value = str(self._arg_values.get(arg["name"], ""))
                if value not in arg["choices"]:
                    choices = arg["choices"]
                    options = choices[0] if len(choices) == 1 else (
                        " or ".join(choices) if len(choices) == 2 else ", ".join(choices[:-1]) + f", or {choices[-1]}"
                    )
                    self._append_output(f"[ERROR] Enter {options} for {arg['label']}.\n")
                    return

        wait_save_failed = False
        wait_config_key = self._wait_before_accept_config_key()
        if wait_config_key:
            wait_value = str(self._arg_values.get("--time-to-sleep", "")).strip()
            if not _valid_wait_before_accept(wait_value):
                self._append_output("[ERROR] Enter a wait time of 0 or more seconds.\n")
                return
            try:
                save_config_updates({wait_config_key: wait_value})
                config.reload()
            except Exception:
                wait_save_failed = True

        log_subdirs = list(self.farmer.get("image_log_subdirs", ()))
        if self.farmer["name"] in REWARD_SETS:
            log_subdirs.append(REWARD_SETS[self.farmer["name"]].log_subdir)
        remove_expired_logged_images(log_subdirs)
        self.resize_window()

        args = self._build_cli_args()
        extension_secrets = self._build_extension_secrets()
        display_args = self._build_display_args(args)
        game_version = get_saved_game_version()

        if self.farmer.get("compiled_extension"):
            script_path = os.path.join(_BASE_DIR, "compiled_extension_runner.py")
            is_bundled_launcher = (
                getattr(sys, "frozen", False) or os.path.basename(sys.executable).lower() == "main.exe"
            )
            if is_bundled_launcher:
                process_args = [
                    _COMPILED_EXTENSION_RUNNER_FLAG,
                    "--bundle",
                    self.farmer["bundle_dir"],
                    "--",
                ] + args
                display_process_args = [
                    _COMPILED_EXTENSION_RUNNER_FLAG,
                    "--bundle",
                    self.farmer["bundle_dir"],
                    "--",
                ] + display_args
            else:
                process_args = ["-u", script_path, "--bundle", self.farmer["bundle_dir"], "--"] + args
                display_process_args = [
                    "-u",
                    script_path,
                    "--bundle",
                    self.farmer["bundle_dir"],
                    "--",
                ] + display_args
        else:
            script_path = os.path.join(_BASE_DIR, self.farmer["script"])
            process_args = ["-u", script_path] + args
            display_process_args = ["-u", script_path] + display_args

        self.process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        if self.farmer.get("compiled_extension"):
            env.insert("AUTOFARMERS_ROOT", os.path.dirname(_BASE_DIR))
            env.insert("AUTOFARMERS_EXTENSION_DIR", self.farmer["bundle_dir"])
            if extension_secrets:
                env.insert(
                    "AUTOFARMERS_EXTENSION_SECRETS",
                    json.dumps(extension_secrets, separators=(",", ":")),
                )
        self.process.setProcessEnvironment(env)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.process_finished)

        self.output_lines = []
        self.output_reset.emit()
        if wait_save_failed:
            self._append_output("[WARNING] Could not save the wait time. Starting with this value anyway.\n")

        self._session_clears = 0
        self._session_pots = 0
        self._session_losses = 0
        self._session_start_time = time.monotonic()
        self._last_clear_time = None
        self._pause_start_time = None
        self.paused = False
        self._session_max_clears = self._read_target_clears()
        self._process_exit_expected = False
        self._uptime_timer.start(1000)
        self.session_progress_changed.emit()
        self.rewards_changed.emit()

        self.process.start(sys.executable, process_args)
        self._clear_secret_args()
        self._cleanup_pause_flag()
        self._append_output(
            f"<color=#10b981>Started {self.farmer['name']} for {game_version.display_name} with:\n"
            f"{' '.join([sys.executable] + display_process_args)}\n</color>"
        )
        self._output_timer.start(100)
        self.running_changed.emit(True, self.process.processId())
        self.paused_changed.emit(False)
        self._emit_status_snapshot()

    def stop(self):
        self.ended_on_its_own = False
        if self.process is not None:
            self._process_exit_expected = True
            self._cleanup_pause_flag()
            proc = self.process
            self.process = None
            try:
                self._output_timer.stop()
                proc.kill()
            except Exception:
                pass
            proc.deleteLater()
        self._after_stop()
        self._append_output("\nProcess stopped.\n")
        self.running_changed.emit(False, 0)
        self._emit_status_snapshot()

    def toggle_pause(self):
        if self.process is None or self.process.state() != QProcess.Running:
            return

        if self.paused and self._blocked_by_devtest():
            return

        pid = self.process.processId()
        flag_path = get_pause_flag_path(pid)

        if not self.paused:
            try:
                with open(flag_path, "w") as f:
                    f.write("")
                self.paused = True
                self._pause_start_time = time.monotonic()
                self._uptime_timer.stop()
                self._append_output(f"<color=#f59e0b>[PAUSED] Created pause flag at {flag_path}\n</color>")
                self.paused_changed.emit(True)
                self._emit_status_snapshot()
            except Exception as e:
                self._append_output(f"[ERROR] Failed to create pause flag: {e}\n")
                self.error_occurred.emit(str(e))
        else:
            try:
                self.resize_window()
                if os.path.exists(flag_path):
                    os.remove(flag_path)
                self.paused = False
                if self._pause_start_time is not None and self._session_start_time is not None:
                    self._session_start_time += time.monotonic() - self._pause_start_time
                    self._pause_start_time = None
                self._uptime_timer.start(1000)
                self._append_output("<color=#10b981>[RESUMED] Removed pause flag\n</color>")
                self.paused_changed.emit(False)
                self.session_progress_changed.emit()
                self._emit_status_snapshot()
            except Exception as e:
                self._append_output(f"[ERROR] Failed to remove pause flag: {e}\n")
                self.error_occurred.emit(str(e))

    def clear_output(self):
        self.output_lines = []
        self.output_reset.emit()
        if self._session_start_time is not None:
            self._session_start_time = time.monotonic()
            self.session_progress_changed.emit()
        self._append_output("\nOutput cleared.\n")

    def resize_window(self):
        if self._blocked_by_devtest():
            return
        from utilities.capture_window import capture_window, resize_7ds_window

        if resize_7ds_window(width=538, height=921):
            try:
                screenshot, _ = capture_window()
                screenshot_shape = screenshot.shape[:2]
                self._append_output(
                    f"[SUCCESS] 7DS window resized successfully! Screenshot shape: {screenshot_shape}\n"
                )
            except Exception as e:
                self._append_output(f"[SUCCESS] 7DS window resized successfully! (could not read shape: {e})\n")
        else:
            self._append_output("[WARNING] Failed to resize 7DS window. Continuing with current window size...\n")
        time.sleep(0.5)

    def set_devtest_busy(self, busy: bool):
        self.devtest_busy = busy
        self.devtest_busy_changed.emit(busy)

    def _blocked_by_devtest(self) -> bool:
        if not self.devtest_busy:
            return False
        self._append_output("Close the DevTest image window or click Stop in DevTest first.\n")
        return True

    def handle_stdout(self):
        if self.process is None:
            return
        lines = []
        while self.process.canReadLine():
            lines.append(bytes(self.process.readLine()).decode("utf-8", errors="replace"))
        if lines:
            self._append_output("".join(lines))

    def process_finished(self):
        proc = self.sender()
        if proc is not None:
            proc.deleteLater()
        expected_stop = self._process_exit_expected
        self._process_exit_expected = False
        self._cleanup_pause_flag()
        self._output_timer.stop()
        self.process = None
        self._after_stop()
        if not expected_stop:
            self.ended_on_its_own = True
            self._append_output("\nFarmer stopped.\n")
            self.running_changed.emit(False, 0)
        self._emit_status_snapshot()

    def check_output(self):
        if self.process is None:
            return
        if self.process.bytesAvailable() > 0:
            self.handle_stdout()

    def _wait_before_accept_config_key(self) -> str | None:
        farmer_id = self.farmer.get("extension_id") or self.farmer.get("script")
        return _WAIT_BEFORE_ACCEPT_CONFIG_KEYS.get(farmer_id)

    def _build_default_arg_values(self) -> dict[str, object]:
        values = {}
        persisted_suite_key = load_suite_license_key() if self.farmer.get("license") else ""
        license_key_argument = (self.farmer.get("license") or {}).get("key_argument")
        wait_config_key = self._wait_before_accept_config_key()
        saved_wait = load_full_config_dict().get(wait_config_key) if wait_config_key else None
        for arg in self.farmer["args"]:
            default = arg.get("default")
            if arg["type"] == "secret" and arg["name"] == license_key_argument:
                values[arg["name"]] = persisted_suite_key
            elif arg["name"] == "--time-to-sleep" and wait_config_key and _valid_wait_before_accept(saved_wait):
                values[arg["name"]] = str(saved_wait).strip()
            elif arg["type"] == "multiselect":
                values[arg["name"]] = list(default or [])
            elif arg["type"] == "checkbox":
                values[arg["name"]] = bool(default)
            elif default is None:
                values[arg["name"]] = ""
            else:
                values[arg["name"]] = default
        return values

    def _read_target_clears(self) -> int | None:
        for arg in self.farmer["args"]:
            if arg["name"] in ("--clears", "--num-clears") and arg["type"] == "text":
                val = str(self._arg_values.get(arg["name"], "")).strip()
                if val and val.lower() != "inf":
                    try:
                        return int(val)
                    except ValueError:
                        return None
                return None
        return None

    def _build_cli_args(self) -> list[str]:
        args = []
        for arg in self.farmer["args"]:
            value = self._arg_values.get(arg["name"])
            if arg["type"] == "secret":
                continue
            if arg["type"] == "dropdown":
                if value:
                    args.extend([arg["name"], str(value)])
            elif arg["type"] == "checkbox":
                if value:
                    args.append(arg["name"])
                elif arg.get("false_name"):
                    args.append(arg["false_name"])
            elif arg["type"] == "multiselect":
                selected = [str(item) for item in (value or []) if str(item)]
                if selected:
                    args.extend([arg["name"]] + selected)
            elif value:
                args.extend([arg["name"], str(value)])
        if self.farmer.get("accepts_game_password") or self.farmer.get("script") in PASSWORD_CLI_SCRIPTS:
            pw = ""
            if self._password_supplier:
                try:
                    pw = self._password_supplier() or ""
                except Exception:
                    pw = ""
            pw = (pw or "").strip()
            if not pw:
                data = load_full_config_dict()
                raw = data.get("game_password", APP_CONFIG_DEFAULTS["game_password"])
                if raw is None or str(raw).strip() == "":
                    raw = data.get("default_game_password")
                pw = ("" if raw is None else str(raw)).strip()
            if pw:
                args.extend(["--password", pw])
        return args

    def _build_extension_secrets(self) -> dict[str, str]:
        if not self.farmer.get("compiled_extension"):
            return {}
        secrets = {}
        for arg in self.farmer["args"]:
            if arg["type"] != "secret":
                continue
            value = self._arg_values.get(arg["name"])
            if value:
                secrets[arg["name"]] = str(value)
        return secrets

    def _clear_secret_args(self):
        changed = False
        license_key_argument = (self.farmer.get("license") or {}).get("key_argument")
        for arg in self.farmer["args"]:
            if (
                arg["type"] == "secret"
                and arg["name"] != license_key_argument
                and self._arg_values.get(arg["name"])
            ):
                self._arg_values[arg["name"]] = ""
                changed = True
        if changed:
            self.arg_values_changed.emit(self.get_arg_values())

    def _build_display_args(self, args: list[str]) -> list[str]:
        display_args = []
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if arg.lower() in ("--password", "-p") and i + 1 < len(args):
                display_args.extend((arg, "*" * len(args[i + 1])))
                skip_next = True
            else:
                display_args.append(arg)
        return display_args

    def _append_output(self, text: str):
        _HIDDEN_MARKERS = {"[CLEAR]", "[POT]", "[LOSS]"}
        new_lines = []
        for line in text.splitlines(True):
            marker = line.strip()
            if marker.startswith(_REWARDS_MARKER):
                if self._session_start_time is not None:
                    self._on_rewards_detected(marker[len(_REWARDS_MARKER) :])
            elif marker not in _HIDDEN_MARKERS:
                new_lines.append(line)
            elif self._session_start_time is not None:
                if marker == "[CLEAR]":
                    self._on_clear_detected()
                elif marker == "[POT]":
                    self._session_pots += 1
                    self.session_progress_changed.emit()
                else:
                    self._session_losses += 1
                    self.session_progress_changed.emit()
        self.output_lines.extend(new_lines)
        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-1000:]
        if new_lines:
            self.output_appended.emit("".join(new_lines))

    def _on_clear_detected(self):
        self._session_clears += 1
        self._last_clear_time = datetime.datetime.now()
        self.session_progress_changed.emit()
        self._emit_status_snapshot()

    def _on_rewards_detected(self, payload: str):
        try:
            rewards = {str(k): int(v) for k, v in json.loads(payload).items()}
        except (ValueError, TypeError, AttributeError):
            return
        self._last_rewards = rewards
        self._reward_runs += 1
        for key, count in rewards.items():
            self._session_rewards[key] = self._session_rewards.get(key, 0) + count
        self.rewards_changed.emit()

    def _update_session_progress(self):
        if self._session_start_time is None:
            return
        self.session_progress_changed.emit()
        self._emit_status_snapshot()

    def _cleanup_pause_flag(self):
        if self.process is None:
            return
        pid = self.process.processId()
        if pid <= 0:
            return
        flag_path = get_pause_flag_path(pid)
        if os.path.exists(flag_path):
            try:
                os.remove(flag_path)
            except OSError:
                pass

    def _after_stop(self):
        self._output_timer.stop()
        self._uptime_timer.stop()
        self.paused = False
        self._pause_start_time = None
        self.paused_changed.emit(False)
        self.session_progress_changed.emit()

    def _emit_status_snapshot(self):
        self.status_snapshot_changed.emit(self.get_status_snapshot())


# Farmer scripts that accept --password / -p (must match argparse in each script).
PASSWORD_CLI_SCRIPTS = frozenset(
    {
        "BirdFarmer.py",
        "BirdFloor4Farmer.py",
        "DeerFarmer.py",
        "DeerFloor4Farmer.py",
        "DailyQuestsFarmer.py",
        "DemonicBeastRotationFarmer.py",
        "DogsFarmer.py",
        "DogsFloor4Farmer.py",
        "DemonFarmer.py",
        "GuildBossFarmer.py",
        "GoldFarmer.py",
        "RatFarmer.py",
        "SnakeFarmer.py",
    }
)


class AboutTab(QWidget):
    update_started = pyqtSignal()
    update_finished = pyqtSignal()
    _MAX_UPDATE_MESSAGE_CHARS = 1000
    _MAX_CHANGED_AREAS_SHOWN = 6
    _UPDATE_AREA_PATTERNS = (
        ("Compiled Extensions", ("scripts/vendor/", "private_sources/", ".gitmodules")),
        ("Dogs Floor 4", ("dogsfloor4farmer.py", "dogs_floor4", "dogs_floor_4")),
        ("Bird Floor 4", ("birdfloor4farmer.py", "bird_floor4", "bird_floor_4")),
        ("Deer Floor 4", ("deerfloor4farmer.py", "deer_floor4", "deer_floor_4")),
        ("Demon King Farmer", ("demonkingfarmer.py", "demon_king", "dk_")),
        ("Guild Boss Farmer", ("guildbossfarmer.py", "guild_boss")),
        ("Final Boss Farmer", ("finalbossfarmer.py", "final_boss")),
        ("Legendary Boss Farmer", ("legendarybossfarmer.py", "legendary_boss")),
        ("Boss Battle Farmer", ("bossbattlefarmer.py", "boss_battle")),
        ("SA Coin Dungeon Farmer", ("sadungeonfarmer.py", "sa_dungeon", "sa_coin")),
        ("Tower Trials", ("towertrialsfarmer.py", "tower_trials")),
        ("Reroll Constellation", ("rerollconstellation.py", "reroll_constellation")),
        ("Accounts Farmer", ("accountsfarmer.py", "accounts_farming", "accounts.yaml")),
        ("Daily Quests Farmer", ("dailyquestsfarmer.py", "daily_farming", "/dailies/")),
        ("Equipment Farmer", ("equipmentfarmer.py", "equipment")),
        ("Demon Farmer", ("demonfarmer.py", "demon_farming", "demons/")),
        ("Dogs Farmer", ("dogsfarmer.py", "dogs_farming", "dogs_fighter", "dogs_fighting", "/dogs/")),
        ("Deer Farmer", ("deerfarmer.py", "deer_farming", "deer_fighter", "deer_fighting", "/deer/")),
        ("Bird Farmer", ("birdfarmer.py", "bird_farming", "bird_fighter", "/bird")),
        (
            "Snake Farmer",
            ("snakefarmer.py", "snake_farming", "snake_fighter", "snake_fighting", "snake_whale", "/snake/"),
        ),
        ("Rat Farmer", ("ratfarmer.py", "rat_farming", "rat_fighter", "rat_fighting", "rat_utilities", "/rat/")),
        ("Gold Farmer", ("goldfarmer.py", "gold_farming", "gold_dungeon", "gold_card")),
        ("Vision Images", ("vision_images.py",)),
        ("Vision", ("vision.py", "pattern_match_strategies.py", "feature_extractors.py")),
        ("GUI", ("autofarmers.py", "gui_images/")),
        ("Configuration", ("scripts/config/", ".yaml")),
        ("Dependencies", ("requirements.txt",)),
        ("Utilities", ("scripts/utilities/",)),
        ("Images", ("scripts/images/",)),
        ("Documentation", ("readme", ".md")),
    )

    def __init__(self, restart_safe_supplier=None, parent=None, update_allowed_supplier=None):
        super().__init__(parent)
        self.update_process = None
        self.updating = False
        self.repo_root = os.path.dirname(os.path.dirname(__file__))
        self.gui_file_path = os.path.abspath(__file__)
        self.requirements_file_path = os.path.join(self.repo_root, "requirements.txt")
        self._restart_safe_supplier = restart_safe_supplier or (lambda: True)
        self._update_allowed_supplier = update_allowed_supplier or (lambda: True)
        self._pre_update_gui_hash = None
        self._pre_update_requirements_hash = None
        self._pending_gui_changed = False
        self._pending_extension_changed = False
        self._capture_process_output = False
        self._process_output = bytearray()
        self._last_process_output = ""
        self._pre_update_head = None
        self._post_update_head = None
        self._latest_update_message = ""
        self._update_count = 0
        self._changed_update_areas = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 20)

        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)

        # Main title
        title = QLabel("AutoFarmers — 7DS Grand Cross")
        title.setFont(QFont("Consolas", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title)

        # Tagline
        tagline = QLabel("Automate the grind. Save your time.")
        tagline.setFont(QFont("Consolas", 12))
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet(f"color: {C['muted']}; font-style: italic;")
        title_layout.addWidget(tagline)

        layout.addLayout(title_layout)

        # Hero image
        self.load_hero_image(layout)

        # Action buttons
        self.create_action_buttons(layout)

        # Description section
        self.create_description_section(layout)

        # Status line
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {C['muted']}; font-size: 14px;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)

    def load_hero_image(self, layout):
        """Load and display the hero image"""
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet(f"border: 1px solid {C['border']}; background: {C['panel2']}; border-radius: 8px;")

        # Try to load the GUI image from readme_images
        image_paths = [
            os.path.join(_GUI_IMAGES_DIR, "main_gui.png"),
        ]

        image_loaded = False
        for image_path in image_paths:
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale to match the widescreen aspect ratio of main_gui.png (16:9)
                    scaled_pixmap = pixmap.scaled(640, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label.setPixmap(scaled_pixmap)
                    img_label.setFixedSize(scaled_pixmap.size())
                    image_loaded = True
                    break

        if not image_loaded:
            img_label.setText("AutoFarmers GUI\n(Image not found)")
            img_label.setFixedSize(640, 360)
            img_label.setStyleSheet(
                f"border: 1px solid {C['border']}; background: {C['panel2']}; color: {C['dark']}; border-radius: 8px; font-size: 13px;"
            )

        # Center the image
        img_layout = QHBoxLayout()
        img_layout.addStretch(1)
        img_layout.addWidget(img_label)
        img_layout.addStretch(1)
        layout.addLayout(img_layout)

    def create_action_buttons(self, layout):
        """Create the action buttons row"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        # Center the buttons
        btn_layout.addStretch(1)

        # Update button (primary)
        self.update_btn = QPushButton("UPDATE")
        self.update_btn.setStyleSheet(
            BTN_START.replace(C["running"], C["text"]).replace("color: white", f"color: {C['bg']}")
        )
        self.update_btn.clicked.connect(self.on_update_clicked)
        btn_layout.addWidget(self.update_btn)

        # GitHub button
        github_btn = QPushButton("GitHub")
        github_btn.setStyleSheet(BTN_DEVTEST)
        github_btn.clicked.connect(lambda: self.open_url("https://github.com/PhantomPilots/AutoFarming"))
        btn_layout.addWidget(github_btn)

        # Discord button
        discord_btn = QPushButton("Discord")
        discord_btn.setStyleSheet(BTN_DEVTEST)
        discord_btn.clicked.connect(lambda: self.open_url("https://discord.gg/En2Wm6a5RV"))
        btn_layout.addWidget(discord_btn)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

    def create_description_section(self, layout):
        """Create the description section"""
        # Main description
        desc_label = QLabel()
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft)
        desc_label.setText("""
<h3>AutoFarmers for 7DS Grand Cross</h3>
<p>Automate your farming in Seven Deadly Sins: Grand Cross with this collection of specialized bots.</p>
        """)
        desc_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        layout.addWidget(desc_label)

        # Available Farmers and Requirements in two columns
        farmers_req_layout = QHBoxLayout()

        # Left column - Available Farmers
        farmers_label = QLabel()
        farmers_label.setWordWrap(True)
        farmers_label.setAlignment(Qt.AlignTop)
        farmers_label.setText("""
<p><strong>Available Farmers:</strong><br>
• Demon, Bird, Deer, Snake, Dogs farming<br>
• Final Boss and boss battle farming<br>
• Account management and daily quests<br>
• Equipment farming and constellation rerolls</p>
        """)
        farmers_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        farmers_req_layout.addWidget(farmers_label)

        # Right column - Requirements
        req_label = QLabel()
        req_label.setWordWrap(True)
        req_label.setAlignment(Qt.AlignTop)
        req_label.setText("""
<p><strong>Requirements:</strong><br>
• Official 7DS PC Beta Client<br>
• Portrait mode (disable landscape)<br>
• Game set to English<br>
• Disable all game notifications</p>
        """)
        req_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        farmers_req_layout.addWidget(req_label)

        layout.addLayout(farmers_req_layout)

        # Call to action
        cta_label = QLabel()
        cta_label.setWordWrap(True)
        cta_label.setAlignment(Qt.AlignCenter)
        cta_label.setText(
            "<p><em>Open a farmer tab to set it up and run it. Questions? Our Discord community can help.</em></p>"
        )
        cta_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4; font-style: italic;")
        layout.addWidget(cta_label)

    def on_update_clicked(self):
        """Handle update button click - run git stash then git pull"""
        if self.updating:
            return  # Already updating
        if not self._update_allowed_supplier():
            self.status_label.setText("Close the DevTest image window or click Stop in DevTest first.")
            return

        # Start the update process
        self.updating = True
        self.update_btn.setEnabled(False)
        self.update_started.emit()
        self._reset_update_summary()
        self.status_label.setText("Checking which version you have...")

        self.run_process("git", ["rev-parse", "HEAD"], self.after_pre_update_head, capture_output=True)

    def open_url(self, url: str):
        """Open URL in default browser"""
        try:
            QDesktopServices.openUrl(QUrl(url))
            if "github" in url.lower():
                self.status_label.setText("Opening GitHub repository...")
            elif "discord" in url.lower():
                self.status_label.setText("Opening Discord invite...")
            else:
                self.status_label.setText(f"🌐 Opening {url}...")

            # Clear status after 2 seconds
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
        except Exception as e:
            self.status_label.setText("Couldn't open the link. Please try again.")

    def after_pre_update_head(self, exit_code):
        """Capture the current revision before applying updates."""
        if exit_code == 0:
            self._pre_update_head = self._last_process_output.strip()

        self.status_label.setText("Preparing your update...")
        self.run_process("git", ["stash"], self.after_stash)

    def after_stash(self, exit_code):
        """Handle completion of git stash command"""
        if exit_code != 0:
            self._start_update_recovery()
            return

        # Stash successful, now run git pull
        self._pre_update_gui_hash = self._compute_file_hash(self.gui_file_path)
        self._pre_update_requirements_hash = self._compute_file_hash(self.requirements_file_path)
        self.status_label.setText("Downloading the update...")
        self.run_process("git", ["pull"], self.after_pull)

    def after_pull(self, exit_code):
        """Handle completion of git pull command"""
        if exit_code != 0:
            self._start_update_recovery()
            return

        self._start_post_update_summary()

    def _start_update_recovery(self):
        """Fetch fresh remote state before attempting a destructive recovery."""
        if self._pre_update_gui_hash is None:
            self._pre_update_gui_hash = self._compute_file_hash(self.gui_file_path)
            self._pre_update_requirements_hash = self._compute_file_hash(self.requirements_file_path)

        self.status_label.setText("The update didn't finish. Trying again...")
        self.run_process("git", ["fetch", "--prune"], self.after_recovery_fetch)

    def after_recovery_fetch(self, exit_code):
        """Resolve the configured upstream only after its remote state is fresh."""
        if exit_code != 0:
            self._fail_update_recovery("Couldn't download the update. Check your connection and try again.")
            return

        self.run_process(
            "git",
            ["rev-parse", "--verify", "@{upstream}^{commit}"],
            self.after_recovery_upstream_resolution,
            capture_output=True,
        )

    def after_recovery_upstream_resolution(self, exit_code):
        """Prefer the branch upstream, falling back to origin's default branch."""
        if exit_code == 0 and self._reset_to_recovery_commit(self._last_process_output):
            return

        self.run_process(
            "git",
            ["rev-parse", "--verify", "origin/HEAD^{commit}"],
            self.after_recovery_origin_head_resolution,
            capture_output=True,
        )

    def after_recovery_origin_head_resolution(self, exit_code):
        """Reset to origin/HEAD when the current branch has no configured upstream."""
        if exit_code == 0 and self._reset_to_recovery_commit(self._last_process_output):
            return

        self._fail_update_recovery("Couldn't find the update. Please try again.")

    def _reset_to_recovery_commit(self, output):
        """Validate a resolved commit ID and start the destructive reset."""
        commit = output.strip()
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", commit):
            return False

        self.status_label.setText("The update didn't finish. Trying again...")
        self.run_process("git", ["reset", "--hard", commit], self.after_recovery_reset)
        return True

    def after_recovery_reset(self, exit_code):
        """Resume the normal post-update workflow after a successful reset."""
        if exit_code != 0:
            self._fail_update_recovery(
                "Couldn't finish the update. Close other apps using AutoFarmers and try again."
            )
            return

        self._start_post_update_summary()

    def _fail_update_recovery(self, message):
        """Finish a failed recovery while keeping its actionable status visible."""
        self.status_label.setText(f"{message}")
        self._finish_update(clear_status=False)

    def _start_post_update_summary(self):
        """Enter the shared post-pull/reset summary workflow."""
        self.status_label.setText("Checking what changed...")
        self.run_process("git", ["rev-parse", "HEAD"], self.after_post_update_head, capture_output=True)

    def after_post_update_head(self, exit_code):
        """Capture the updated revision and gather a short user-facing summary."""
        if exit_code != 0:
            self._handle_post_pull_completion()
            return

        self._post_update_head = self._last_process_output.strip()
        if not self._pre_update_head or self._pre_update_head == self._post_update_head:
            self._handle_post_pull_completion()
            return

        revision_range = f"{self._pre_update_head}..{self._post_update_head}"
        self.run_process("git", ["rev-list", "--count", revision_range], self.after_update_count, capture_output=True)

    def after_update_count(self, exit_code):
        """Capture how many updates were included."""
        if exit_code == 0:
            try:
                self._update_count = int(self._last_process_output.strip())
            except ValueError:
                self._update_count = 0

        if not self._pre_update_head or not self._post_update_head:
            self._handle_post_pull_completion()
            return

        revision_range = f"{self._pre_update_head}..{self._post_update_head}"
        self.run_process(
            "git",
            ["log", "-1", "--pretty=format:%B", revision_range],
            self.after_latest_update_message,
            capture_output=True,
        )

    def after_latest_update_message(self, exit_code):
        """Capture the latest update message, bounded for a compact popup."""
        if exit_code == 0:
            self._latest_update_message = self._truncate_update_message(self._last_process_output.strip())

        if not self._pre_update_head or not self._post_update_head:
            self._handle_post_pull_completion()
            return

        revision_range = f"{self._pre_update_head}..{self._post_update_head}"
        self.run_process(
            "git",
            ["diff", "--name-only", revision_range],
            self.after_changed_update_files,
            capture_output=True,
        )

    def after_changed_update_files(self, exit_code):
        """Capture the user-facing areas touched by this update."""
        if exit_code == 0:
            changed_paths = [path.strip() for path in self._last_process_output.splitlines() if path.strip()]
            self._changed_update_areas = self._classify_changed_update_areas(changed_paths)
            self._pending_extension_changed = any(
                path.replace("\\", "/").lower().startswith("scripts/vendor/")
                or path.replace("\\", "/").lower().startswith("private_sources/")
                or path.replace("\\", "/").lower() == ".gitmodules"
                for path in changed_paths
            )

        self._handle_post_pull_completion()

    def after_requirements_install(self, exit_code):
        """Handle completion of the requirements install step."""
        if exit_code != 0:
            self.status_label.setText(
                "Couldn't install the update. Please try again."
            )
            self._finish_update(clear_status=False)
            return

        self._complete_restart_decision()

    def run_process(self, program, args, on_finished, capture_output=False):
        """Run an external command in the repo root directory."""
        if self.update_process is not None:
            return  # Already running a command

        self._capture_process_output = capture_output
        self._process_output = bytearray()
        self._last_process_output = ""
        self.update_process = QProcess(self)
        self.update_process.setWorkingDirectory(self.repo_root)
        self.update_process.setProcessChannelMode(QProcess.MergedChannels)

        # Connect signals
        self.update_process.finished.connect(
            lambda exit_code, exit_status: self.on_git_finished(exit_code, on_finished)
        )
        self.update_process.readyReadStandardOutput.connect(self.on_git_output)

        # Start the command
        self.update_process.start(program, args)

        if not self.update_process.waitForStarted(3000):
            self.status_label.setText(f"Failed to start {program}")
            self.update_process = None
            self._capture_process_output = False
            self._process_output = bytearray()
            self._finish_update()

    def on_git_output(self):
        """Handle command output, capturing only when a caller needs it."""
        if self.update_process is not None:
            output = self.update_process.readAllStandardOutput()
            if self._capture_process_output:
                self._process_output.extend(bytes(output))

    def on_git_finished(self, exit_code, callback):
        """Handle git command completion"""
        if self.update_process is not None and self._capture_process_output:
            self._process_output.extend(bytes(self.update_process.readAllStandardOutput()))
            self._last_process_output = self._process_output.decode(errors="replace")
        self.update_process = None
        self._capture_process_output = False
        self._process_output = bytearray()
        callback(exit_code)

    def _compute_file_hash(self, path):
        """Return a file hash, or None if the file can't be read."""
        try:
            hasher = hashlib.sha256()
            with open(path, "rb") as file_obj:
                for chunk in iter(lambda: file_obj.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None

    def _reset_update_summary(self):
        """Clear per-run update summary data."""
        self._pre_update_head = None
        self._post_update_head = None
        self._latest_update_message = ""
        self._update_count = 0
        self._changed_update_areas = []
        self._pending_extension_changed = False

    def _truncate_update_message(self, message):
        """Keep verbose update messages from creating oversized dialogs."""
        if len(message) <= self._MAX_UPDATE_MESSAGE_CHARS:
            return message
        return message[: self._MAX_UPDATE_MESSAGE_CHARS].rstrip() + "..."

    def _classify_changed_update_areas(self, changed_paths):
        """Group changed files into user-facing update areas."""
        areas = []
        seen = set()
        for path in changed_paths:
            area = self._classify_update_area(path)
            if area in seen:
                continue
            seen.add(area)
            areas.append(area)
        return areas

    def _classify_update_area(self, path):
        normalized_path = path.replace("\\", "/").lower()
        for area, patterns in self._UPDATE_AREA_PATTERNS:
            if any(pattern in normalized_path for pattern in patterns):
                return area
        return "Other"

    def _show_update_summary_dialog(self):
        """Show a compact summary for successful updates."""
        if not self._latest_update_message and self._update_count <= 0:
            return

        parts = ["What changed most recently:"]
        parts.append(self._latest_update_message or "No short description was available for this download.")

        if self._changed_update_areas:
            parts.append("")
            parts.append("Changed areas:")
            visible_areas = self._changed_update_areas[: self._MAX_CHANGED_AREAS_SHOWN]
            parts.extend(f"• {area}" for area in visible_areas)
            hidden_area_count = len(self._changed_update_areas) - len(visible_areas)
            if hidden_area_count > 0:
                plural = "" if hidden_area_count == 1 else "s"
                parts.append(f"• {hidden_area_count} more area{plural}")

        if self._update_count > 0:
            parts.append("")
            update_word = "update" if self._update_count == 1 else "updates"
            parts.append(f"This download contains {self._update_count} {update_word}.")

        QMessageBox.information(self, "You're up to date", "\n".join(parts))

    def _handle_post_pull_completion(self):
        """Handle post-pull decisions, including requirements install and restart."""
        post_update_gui_hash = self._compute_file_hash(self.gui_file_path)
        post_update_requirements_hash = self._compute_file_hash(self.requirements_file_path)
        self._pending_gui_changed = (
            self._pre_update_gui_hash is not None
            and post_update_gui_hash is not None
            and self._pre_update_gui_hash != post_update_gui_hash
        )
        requirements_changed = (
            self._pre_update_requirements_hash is not None
            and post_update_requirements_hash is not None
            and self._pre_update_requirements_hash != post_update_requirements_hash
        )

        if requirements_changed:
            self.status_label.setText("Installing the update...")
            self.run_process(
                sys.executable,
                ["-m", "pip", "install", "-r", self.requirements_file_path],
                self.after_requirements_install,
            )
            return

        self._complete_restart_decision()

    def _complete_restart_decision(self):
        """Decide whether the update should trigger a GUI restart."""
        self._show_update_summary_dialog()

        restart_required = self._pending_gui_changed or self._pending_extension_changed
        if not restart_required:
            self.status_label.setText("Update complete")
            self._finish_update()
            return

        if not self._restart_safe_supplier():
            self.status_label.setText("Update ready. Restart AutoFarmers to use it.")
            self._finish_update(clear_status=False)
            return

        self.status_label.setText("Update complete. Restarting AutoFarmers...")
        self._finish_update(clear_status=False)
        if not _restart_application():
            self.status_label.setText("Update complete. Please reopen AutoFarmers.")
            return
        QApplication.instance().quit()

    def _finish_update(self, clear_status=True):
        """Reset update UI state and optionally clear the status after a delay."""
        self.updating = False
        self.update_btn.setEnabled(True)
        self._pre_update_gui_hash = None
        self._pre_update_requirements_hash = None
        self._pending_gui_changed = False
        self._pending_extension_changed = False
        self._reset_update_summary()
        self.update_finished.emit()
        if clear_status:
            QTimer.singleShot(5000, lambda: self.status_label.setText(""))


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.reload_from_disk()

    def init_ui(self):
        self.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(14)

        intro = QLabel(
            "<strong>Settings</strong> — fill in what you need, then click <strong>Save</strong>. "
            "<strong>Load saved</strong> puts back whatever was last saved (drops unsaved edits)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        ntfy_group = QGroupBox("Phone notifications")
        ntfy_outer = QVBoxLayout()
        help_ntfy = QLabel(
            "Install the free ntfy app on your phone and create a topic. "
            "Type the <em>same</em> topic name here. Leave blank to turn phone alerts off. "
            "Pick something long and random so only you get the messages."
        )
        help_ntfy.setWordWrap(True)
        help_ntfy.setStyleSheet(f"color: {C['muted']};")
        ntfy_outer.addWidget(help_ntfy)

        topic_row = QHBoxLayout()
        topic_row.addWidget(QLabel("Topic:"))
        self.topic_edit = QLineEdit()
        self.topic_edit.setPlaceholderText("e.g. 7ds_farmer_myname_abc123")
        topic_row.addWidget(self.topic_edit)
        ntfy_outer.addLayout(topic_row)

        ntfy_btn_row = QHBoxLayout()
        ntfy_open_btn = QPushButton("Open ntfy (get the app)")
        ntfy_open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://ntfy.sh/")))
        self.test_notif_btn = QPushButton("Send test notification")
        self.test_notif_btn.clicked.connect(self.on_test_notification)
        ntfy_btn_row.addWidget(ntfy_open_btn)
        ntfy_btn_row.addWidget(self.test_notif_btn)
        ntfy_btn_row.addStretch(1)
        ntfy_outer.addLayout(ntfy_btn_row)
        ntfy_group.setLayout(ntfy_outer)
        layout.addWidget(ntfy_group)

        stuck_group = QGroupBox("If the bot seems stuck")
        stuck_form = QFormLayout()

        self.stuck_spin = QSpinBox()
        self.stuck_spin.setRange(0, 1440)
        self.stuck_spin.setSuffix(" min")
        stuck_form.addRow("How long before warning you:", self.stuck_spin)
        stuck_hint = QLabel("0 = off (no stuck warnings).")
        stuck_hint.setWordWrap(True)
        stuck_hint.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
        stuck_form.addRow("", stuck_hint)

        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setRange(0, 120)
        self.cooldown_spin.setSuffix(" min")
        stuck_form.addRow("Space between repeat warnings:", self.cooldown_spin)
        cd_hint = QLabel("Won't ping faster than about every 30 seconds.")
        cd_hint.setWordWrap(True)
        cd_hint.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
        stuck_form.addRow("", cd_hint)

        self.max_notif_spin = QSpinBox()
        self.max_notif_spin.setRange(0, 50)
        stuck_form.addRow("Max warnings per stuck episode:", self.max_notif_spin)
        max_hint = QLabel("0 = no warnings for that episode.")
        max_hint.setWordWrap(True)
        max_hint.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
        stuck_form.addRow("", max_hint)

        stuck_group.setLayout(stuck_form)
        layout.addWidget(stuck_group)

        daily_group = QGroupBox("Daily schedule")
        daily_form = QFormLayout()
        self.check_in_hour_spin = QSpinBox()
        self.check_in_hour_spin.setRange(0, 23)
        self.check_in_hour_spin.setSuffix(":00 PT")
        daily_form.addRow("Daily check-in time:", self.check_in_hour_spin)
        daily_hint = QLabel("Uses a 24-hour clock in Pacific Time.")
        daily_hint.setWordWrap(True)
        daily_hint.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
        daily_form.addRow("", daily_hint)
        daily_group.setLayout(daily_form)
        layout.addWidget(daily_group)

        pwd_group = QGroupBox("Game login")
        pwd_outer = QVBoxLayout()
        pwd_help = QLabel(
            "If the game logs you out, the bot can try to sign back in using this password. "
            "Leave the password blank if you don't want that. "
            "After a logout, the bot waits the number of minutes below before it tries to log in."
        )
        pwd_help.setWordWrap(True)
        pwd_help.setStyleSheet(f"color: {C['muted']};")
        pwd_outer.addWidget(pwd_help)
        pwd_row = QHBoxLayout()
        pwd_row.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Same as in the game (optional)")
        pwd_row.addWidget(self.password_edit)
        pwd_outer.addLayout(pwd_row)
        login_wait_form = QFormLayout()
        self.login_wait_spin = QSpinBox()
        self.login_wait_spin.setRange(1, 1440)
        self.login_wait_spin.setSuffix(" min")
        login_wait_form.addRow("Minutes to wait after logout before login:", self.login_wait_spin)
        pwd_outer.addLayout(login_wait_form)
        pwd_group.setLayout(pwd_outer)
        layout.addWidget(pwd_group)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet(
            f"background-color: {C['running']}; color: white; font-weight: bold; padding: 7px 20px; border: none; border-radius: 6px;"
        )
        self.save_btn.clicked.connect(self.on_save)
        self.reload_btn = QPushButton("Load saved")
        self.reload_btn.setStyleSheet(
            f"background-color: {C['darker']}; color: {C['text']}; font-weight: bold; padding: 7px 20px; border: none; border-radius: 6px;"
        )
        self.reload_btn.clicked.connect(self.reload_from_disk)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.reload_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        footnote = QLabel("Already running a farmer? Stop it and press Start again so it picks up new settings.")
        footnote.setWordWrap(True)
        footnote.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
        layout.addWidget(footnote)
        layout.addStretch(1)

    @staticmethod
    def _int_from_data(data: dict, key: str) -> int:
        raw = data.get(key, APP_CONFIG_DEFAULTS[key])
        try:
            return int(raw)
        except (TypeError, ValueError):
            return int(APP_CONFIG_DEFAULTS[key])

    def reload_from_disk(self):
        config.reload()
        data = load_full_config_dict()
        topic = data.get("ntfy_private_channel")
        self.topic_edit.setText("" if topic is None else str(topic))
        self.stuck_spin.setValue(self._int_from_data(data, "stuck_timeout_minutes"))
        self.cooldown_spin.setValue(self._int_from_data(data, "notification_cooldown_minutes"))
        self.max_notif_spin.setValue(self._int_from_data(data, "max_notifications_per_incident"))
        self.check_in_hour_spin.setValue(self._int_from_data(data, "check_in_hour"))
        pw = data.get("game_password", APP_CONFIG_DEFAULTS["game_password"])
        if pw is None or str(pw).strip() == "":
            legacy = data.get("default_game_password")
            if legacy is not None and str(legacy).strip() != "":
                pw = legacy
        self.password_edit.setText("" if pw is None else str(pw))
        self.login_wait_spin.setValue(self._int_from_data(data, "minutes_to_wait_before_login"))
        self.status_label.setText("Loaded saved settings.")
        self.status_label.setStyleSheet(f"color: {C['muted']};")

    def on_save(self):
        try:
            stripped_pwd = self.password_edit.text().strip()
            self.password_edit.setText(stripped_pwd)
            save_config_updates(
                {
                    "ntfy_private_channel": self.topic_edit.text().strip(),
                    "stuck_timeout_minutes": self.stuck_spin.value(),
                    "notification_cooldown_minutes": self.cooldown_spin.value(),
                    "max_notifications_per_incident": self.max_notif_spin.value(),
                    "check_in_hour": self.check_in_hour_spin.value(),
                    "game_password": stripped_pwd,
                    "minutes_to_wait_before_login": self.login_wait_spin.value(),
                }
            )
            config.reload()
            self.status_label.setText("Saved.")
            self.status_label.setStyleSheet(f"color: {C['running']};")
            QTimer.singleShot(5000, lambda: self.status_label.setText(""))
        except Exception as e:
            self.status_label.setText(f"Save failed: {e}")
            self.status_label.setStyleSheet(f"color: {C['error']};")

    def on_test_notification(self):
        config.reload()
        ok, msg = test_ntfy_connection()
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {C['running'] if ok else C['error']};")


class DevTestController(QObject):
    """Own the one-shot child and its temporary image independently of page navigation."""

    busy_changed = pyqtSignal(bool)
    output_appended = pyqtSignal(str)
    image_changed = pyqtSignal()
    vision_names_changed = pyqtSignal(list)

    def __init__(self, can_start_supplier, parent=None):
        super().__init__(parent)
        self._can_start_supplier = can_start_supplier
        self.process = None
        self.last_image = None
        self._temporary_images = None
        self._sequence = 0
        self._output_path = None
        self._stopping = False
        self._decoder = None
        self.vision_names = []
        self.catalog_process = None
        self._catalog_started = False
        self._shutting_down = False

    def _new_process(self):
        process = QProcess(self)
        process.setWorkingDirectory(_BASE_DIR)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        process.setProcessEnvironment(env)
        return process

    @staticmethod
    def _launch_args(cli_args):
        bundled = getattr(sys, "frozen", False) or os.path.basename(sys.executable).lower() == "main.exe"
        prefix = [_DEVTEST_RUNNER_FLAG] if bundled else ["-u", os.path.join(_BASE_DIR, "development.py")]
        return prefix + list(cli_args)

    def load_vision_names(self):
        if self._catalog_started or self._shutting_down:
            return
        self._catalog_started = True
        process = self._new_process()
        self.catalog_process = process
        process.finished.connect(lambda code, status, p=process: self._catalog_finished(p, code, status))
        process.errorOccurred.connect(lambda error, p=process: self._catalog_error(p, error))
        process.start(sys.executable, self._launch_args(["list-visions"]))

    def _catalog_error(self, process, error):
        if process is self.catalog_process and error == QProcess.FailedToStart:
            self._catalog_finished(process, -1, QProcess.CrashExit)

    def _catalog_finished(self, process, code, status):
        if process is not self.catalog_process:
            return
        try:
            if status != QProcess.NormalExit or code != 0:
                raise ValueError("Catalogue process failed")
            payload = json.loads(bytes(process.readAllStandardOutput()).decode("utf-8"))
            names, warnings = payload["names"], payload["warnings"]
            if not isinstance(names, list) or not isinstance(warnings, list) or any(
                not isinstance(name, str) or not name.isidentifier() or name.startswith("_") for name in names
            ) or any(not isinstance(warning, str) for warning in warnings):
                raise ValueError("Invalid vision catalogue")
            if not self._shutting_down:
                self.vision_names = sorted(set(names))
                self.vision_names_changed.emit(self.vision_names)
                for warning in warnings:
                    self.output_appended.emit(warning + "\n")
        except (ValueError, KeyError, TypeError, UnicodeError):
            if not self._shutting_down:
                self.output_appended.emit("Could not load vision suggestions. You can still enter a name.\n")
        finally:
            self.catalog_process = None
            process.deleteLater()

    @property
    def is_busy(self):
        return self.process is not None

    def start(self, action, args=()):
        if self.is_busy:
            return
        if not self._can_start_supplier():
            self.output_appended.emit("Pause or stop all Farmers and finish any update before using DevTest.\n")
            return
        try:
            if self._temporary_images is None:
                self._temporary_images = tempfile.TemporaryDirectory(prefix="autofarmers_devtest_")
            self._sequence += 1
            self._output_path = os.path.join(self._temporary_images.name, f"preview_{self._sequence}.png")
        except OSError as exc:
            self.output_appended.emit(f"Could not prepare a temporary image: {exc}\n")
            return
        cli_args = [action, *args, "--output", self._output_path]
        process = self._new_process()
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(lambda p=process: self._read_output(p))
        process.finished.connect(lambda code, status, p=process: self._finished(p, code, status))
        process.errorOccurred.connect(lambda error, p=process: self._process_error(p, error))
        self.process = process
        self._stopping = False
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.output_appended.emit(f"\nStarting {action.replace('-', ' ')}...\n")
        self.busy_changed.emit(True)
        process.start(sys.executable, self._launch_args(cli_args))

    def _read_output(self, process, *, final=False):
        if process is not self.process:
            return
        output = self._decoder.decode(bytes(process.readAllStandardOutput()), final=final)
        if output:
            self.output_appended.emit(output)

    def _finished(self, process, code, status):
        if process is not self.process:
            return
        self._read_output(process, final=True)
        if self._stopping:
            self.output_appended.emit("Stopped.\n")
        elif status == QProcess.NormalExit and code == 0 and os.path.isfile(self._output_path):
            if self.last_image:
                with contextlib.suppress(OSError):
                    os.remove(self.last_image)
            self.last_image = self._output_path
            self.output_appended.emit("Image ready. Enter a folder and filename, then click Save image.\n")
        elif status == QProcess.NormalExit and code == 2:
            self.output_appended.emit("No new image was saved.\n")
        else:
            self.output_appended.emit("The tool could not finish. Check the messages above and try again.\n")
        if self._output_path != self.last_image and os.path.isfile(self._output_path):
            with contextlib.suppress(OSError):
                os.remove(self._output_path)
        self.process = None
        process.deleteLater()
        self.busy_changed.emit(False)
        self.image_changed.emit()

    def _process_error(self, process, error):
        if process is self.process and error == QProcess.FailedToStart:
            self.output_appended.emit(f"Could not start the tool: {process.errorString()}\n")
            self._finished(process, -1, QProcess.CrashExit)

    def stop(self):
        if self.process is not None:
            self._stopping = True
            self.process.kill()

    def shutdown(self):
        self._shutting_down = True
        if self.catalog_process is not None:
            process = self.catalog_process
            self.catalog_process = None
            with contextlib.suppress(TypeError, RuntimeError):
                process.finished.disconnect()
                process.errorOccurred.disconnect()
            process.kill()
            process.waitForFinished(1000)
        if self.process is not None:
            process = self.process
            self.stop()
            process.waitForFinished(1000)
        if self._temporary_images is not None:
            self._temporary_images.cleanup()
            self._temporary_images = None
        self.last_image = None


class DevTestTab(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setStyleSheet(BTN_DEVTEST)
        self.run_buttons = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)
        intro = QLabel("Choose a tool below. The game resizes before each capture. Pause or stop your Farmers first.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        tool_grid = QGridLayout()
        tool_grid.setColumnStretch(0, 1)
        tool_grid.setColumnStretch(1, 1)
        tool_grid.setSpacing(12)
        layout.addLayout(tool_grid)

        vision_group = QGroupBox("Screenshot testing")
        vision_form = QFormLayout(vision_group)
        self.vision_edit = QLineEdit()
        self.vision_edit.setPlaceholderText("Vision name, e.g. startbutton (without vio.)")
        self.vision_model = QStringListModel(controller.vision_names, self)
        self.vision_completer = QCompleter(self.vision_model, self)
        self.vision_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.vision_completer.setFilterMode(Qt.MatchStartsWith)
        self.vision_completer.popup().setStyleSheet(
            f"QListView {{ background: {C['panel2']}; color: {C['text']};"
            f" border: 1px solid {C['border2']}; outline: none;"
            f" selection-background-color: {_DEVTEST_BUTTON_COLORS[1]}; selection-color: {C['text']}; }}"
            "QListView::item { padding: 4px 8px; }"
        )
        self.vision_edit.setCompleter(self.vision_completer)
        controller.vision_names_changed.connect(self.vision_model.setStringList)
        vision_form.addRow("Vision name:", self.vision_edit)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 1)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setValue(0.7)
        vision_form.addRow("Threshold:", self.threshold_spin)
        vision_form.addRow(self._run_button("Test screenshot", self._test_screenshot))
        tool_grid.addWidget(vision_group, 0, 0)

        hand_group = QGroupBox("Cards")
        hand_row = QHBoxLayout(hand_group)
        hand_row.addWidget(QLabel("Units:"))
        self.units_combo = QComboBox()
        self.units_combo.addItems(["3", "4"])
        self.units_combo.setCurrentText("4")
        hand_row.addWidget(self.units_combo)
        hand_row.addWidget(self._run_button("Capture hand", lambda: self._capture_cards("capture-hand")))
        hand_row.addWidget(self._run_button("Show card types", lambda: self._capture_cards("card-types")))
        hand_row.addStretch(1)
        tool_grid.addWidget(hand_group, 1, 0)

        image_group = QGroupBox("Images and coordinates")
        image_row = QVBoxLayout(image_group)
        for label, action in (
            ("Determine coordinates", "coordinates"),
            ("Crop picker", "crop"),
        ):
            image_row.addWidget(self._run_button(label, lambda _checked=False, a=action: self.controller.start(a)))
        tool_grid.addWidget(image_group, 0, 1)

        save_group = QGroupBox("Save the last image")
        save_form = QFormLayout(save_group)
        folder_row = QHBoxLayout()
        saved = load_full_config_dict().get("devtest_save_directory", "")
        self._remembered_folder = saved if isinstance(saved, str) else ""
        self.folder_edit = QLineEdit(self._remembered_folder)
        self.folder_edit.setPlaceholderText("Choose a folder — remembered next time")
        self.folder_edit.editingFinished.connect(self._remember_folder)
        folder_row.addWidget(self.folder_edit, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        save_form.addRow("Save folder:", folder_row)
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("e.g. hand.png — filename stays only for this session")
        save_form.addRow("Filename:", self.filename_edit)
        self.save_btn = QPushButton("Save image")
        self.save_btn.clicked.connect(self.save_image)
        save_form.addRow(self.save_btn)
        save_hint = QLabel("Close the image window to enable saving. Enter a name; .png is added if needed.")
        save_hint.setWordWrap(True)
        save_form.addRow(save_hint)
        tool_grid.addWidget(save_group, 1, 1)

        controls = QHBoxLayout()
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(controller.stop)
        controls.addWidget(self.stop_btn)
        clear_btn = QPushButton("Clear")
        controls.addWidget(clear_btn)
        controls.addStretch(1)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        controls.addWidget(self.status_label)
        layout.addLayout(controls)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMinimumHeight(160)
        self.terminal.document().setMaximumBlockCount(5000)
        self.terminal.setFont(QFont("Consolas", 10))
        self.terminal.setStyleSheet(f"background: {C['term_bg']}; color: {C['term_text']};")
        layout.addWidget(self.terminal, 1)
        clear_btn.clicked.connect(self.terminal.clear)
        controller.output_appended.connect(self.append_terminal)
        controller.busy_changed.connect(self.refresh_controls)
        controller.image_changed.connect(self.refresh_controls)
        self.append_terminal("Ready. Image windows close with Escape or their close button.\n")
        self.refresh_controls()
        QTimer.singleShot(0, controller.load_vision_names)

    def _run_button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        self.run_buttons.append(button)
        return button

    def refresh_controls(self, *_args):
        busy = self.controller.is_busy
        allowed = not busy and self.controller._can_start_supplier()
        for button in self.run_buttons:
            button.setEnabled(allowed)
        self.stop_btn.setEnabled(busy)
        self.save_btn.setEnabled(not busy and self.controller.last_image is not None)
        if busy:
            self.status_label.setText("Tool running…")
        elif allowed:
            self.status_label.setText("Ready")
        else:
            self.status_label.setText("Pause or stop your Farmers and finish any update first.")

    def append_terminal(self, text):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def _test_screenshot(self):
        name = self.vision_edit.text().strip()
        self.controller.start("screenshot-test", [f"--vision={name}", "--threshold", str(self.threshold_spin.value())])

    def _capture_cards(self, action):
        self.controller.start(action, ["--units", self.units_combo.currentText()])

    def _remember_folder(self):
        raw = self.folder_edit.text().strip()
        folder = os.path.abspath(os.path.expandvars(os.path.expanduser(raw))) if raw else ""
        self.folder_edit.setText(folder)
        if folder == self._remembered_folder:
            return folder
        try:
            save_config_updates({"devtest_save_directory": folder})
            config.reload()
            self._remembered_folder = folder
        except Exception as exc:
            self.append_terminal(f"Could not remember the folder. You can still save your image: {exc}\n")
        return folder

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a save folder", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            self._remember_folder()

    @staticmethod
    def png_filename(value):
        filename = value.strip()
        if not filename or re.search(r'[<>:"/\\|?*\x00-\x1f]', filename) or filename.endswith((".", " ")):
            raise ValueError("Enter a filename without folders or special characters, such as 'hand.png'.")
        stem, extension = os.path.splitext(filename)
        if extension and extension.lower() != ".png":
            raise ValueError("Use a .png filename, such as 'hand.png'.")
        reserved = {"CON", "PRN", "AUX", "NUL"}
        reserved.update(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10))
        if not stem or stem.upper().split(".")[0] in reserved:
            raise ValueError("Choose another filename, such as 'hand.png'.")
        return filename if extension else filename + ".png"

    def save_image(self):
        if self.controller.is_busy or not self.controller.last_image:
            return
        temporary_path = None
        try:
            folder = self._remember_folder()
            if not folder:
                raise ValueError("Choose a save folder first.")
            filename = self.png_filename(self.filename_edit.text())
            destination = os.path.join(folder, filename)
            if os.path.exists(destination):
                answer = QMessageBox.question(
                    self, "Replace image?", f"'{filename}' already exists. Replace it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    self.append_terminal("Image save cancelled.\n")
                    return
            os.makedirs(folder, exist_ok=True)
            descriptor, temporary_path = tempfile.mkstemp(prefix=".devtest_", suffix=".png", dir=folder)
            os.close(descriptor)
            shutil.copyfile(self.controller.last_image, temporary_path)
            os.replace(temporary_path, destination)
            temporary_path = None
            self.filename_edit.setText(filename)
            self.append_terminal(f"Image saved: {destination}\n")
        except (OSError, ValueError) as exc:
            self.append_terminal(f"Could not save the image: {exc}\n")
        finally:
            if temporary_path is not None:
                with contextlib.suppress(OSError):
                    os.remove(temporary_path)


class FarmerTab(QWidget):
    _COLOR_TAG_RE = re.compile(r"<color=([^>]+)>(.*?)</color>", re.IGNORECASE | re.DOTALL)
    _LINE_COLOR_RULES = [
        (re.compile(r"error|failed|exception|traceback|critical", re.I), "#F0554A"),
        (re.compile(r"\bwarn(ing)?\b", re.I), "#E8B21E"),
        (re.compile(r"success|complet|finished|victory|cleared|✓|✅", re.I), "#21B874"),
        (re.compile(r"\b(info|start|launch|connect|running)\b", re.I), "#4DBDF2"),
        (re.compile(r"^\s*[>=\-#]{3,}"), "#6E6C66"),
    ]
    _LEFT_W = 380
    _IMAGE_W = 340

    def __init__(self, farmer, controller, parent=None, accent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.controller = controller
        self.accent = accent or INK_CYAN
        self._syncing_arg_widgets = False
        self.sa_chest_warning_label = None
        self._default_fmt = QTextCharFormat()
        self._default_fmt.setForeground(QColor(C["term_text"]))
        self.init_ui()
        self.controller.output_reset.connect(self._on_output_reset)
        self.controller.output_appended.connect(self.append_terminal)
        self.controller.running_changed.connect(self._on_running_changed)
        self.controller.paused_changed.connect(self._on_paused_changed)
        self.controller.devtest_busy_changed.connect(self._refresh_action_buttons)
        self.controller.session_progress_changed.connect(self._refresh_session_progress)
        self.controller.arg_values_changed.connect(self._sync_arg_widgets)
        self.controller.status_snapshot_changed.connect(self._on_status_snapshot_changed)
        self._sync_from_controller()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        left = QWidget()
        left.setFixedWidth(self._LEFT_W)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }}")
        left_body = QWidget()
        left_body.setLayout(self._build_left_panel())
        left_scroll.setWidget(left_body)
        left_lay.addWidget(left_scroll, 1)
        left_lay.addWidget(self._build_run_controls())
        layout.addWidget(left)

        rule = QFrame()
        rule.setFixedWidth(1)
        rule.setStyleSheet(f"background: {C['border']}; border: none;")
        layout.addWidget(rule)

        right = QWidget()
        right.setLayout(self._build_right_panel())
        layout.addWidget(right, 1)
        self._append_welcome()

    def _fit_requirements(self):
        if self.req_label is None or self._req_scroll is None:
            return
        width = self._LEFT_W - 40 - 2
        needed = self.req_label.heightForWidth(width)
        self._req_scroll.setFixedHeight(max(40, min(200, needed + 4)))

    def _section_heading(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {C['text']};")
        return lbl

    def _build_left_panel(self):
        panel = QVBoxLayout()
        panel.setContentsMargins(20, 20, 20, 20)
        panel.setSpacing(0)

        self.image_size = (self._IMAGE_W, self._IMAGE_W * 9 // 18)
        self.image_label = QLabel("No image for this Farmer")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            f"border: 1px solid {C['border']}; background: {C['panel2']}; color: {C['muted']}; border-radius: 8px;"
        )
        self.image_label.setFixedSize(*self.image_size)
        self.load_farmer_image()
        panel.addWidget(self.image_label, 0, Qt.AlignLeft)
        panel.addSpacing(18)

        self.req_label = None
        self._req_scroll = None
        extension_requirements = self.farmer.get("requirements_html", "")
        availability_error = self.farmer.get("availability_error")
        if availability_error:
            extension_requirements = (
                f"<p><strong>Unavailable:</strong> {availability_error}</p>" + extension_requirements
            )
        if self.farmer["name"] in REQUIREMENTS or self.farmer["name"] in WHALE_MODE_CONFIG or extension_requirements:
            box = QFrame()
            box.setObjectName("teamBox")
            box.setStyleSheet(
                f"QFrame#teamBox {{ border: 1px solid {C['border2']}; border-radius: 8px; background: {C['panel']}; }}"
            )
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(0, 0, 0, 0)
            box_lay.setSpacing(0)
            box_title = QLabel("Team & requirements")
            box_title.setStyleSheet(
                f"background: {self.accent}; color: {_on_ink(self.accent)}; font-size: 12px; font-weight: 700;"
                " padding: 5px 12px; border: none; border-top-left-radius: 7px; border-top-right-radius: 7px;"
            )
            box_lay.addWidget(box_title)

            self.req_label = QLabel()
            self.req_label.setWordWrap(True)
            self.req_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.req_label.setTextFormat(Qt.RichText)
            self.req_label.setText(extension_requirements or REQUIREMENTS.get(self.farmer["name"], ""))
            self.req_label.setStyleSheet(
                f"font-size: 13px; color: {C['text']}; background: transparent; padding: 8px 12px 10px 12px;"
                " border: none;"
            )
            req_scroll = QScrollArea()
            req_scroll.setWidget(self.req_label)
            req_scroll.setWidgetResizable(True)
            req_scroll.setMaximumHeight(200)
            req_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            req_scroll.setStyleSheet(
                f"QScrollArea {{ background: {C['panel']}; border: none; }}"
                f"QScrollArea > QWidget > QWidget {{ background: {C['panel']}; }}"
            )
            box_lay.addWidget(req_scroll)
            self._req_scroll = req_scroll
            self._fit_requirements()
            panel.addWidget(box)
            panel.addSpacing(22)

        if self.farmer["args"]:
            panel.addWidget(self._section_heading("Settings"))
            panel.addSpacing(10)
            args_layout = QFormLayout()
            args_layout.setContentsMargins(0, 0, 0, 0)
            args_layout.setHorizontalSpacing(14)
            args_layout.setVerticalSpacing(10)
            args_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            args_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            self.arg_widgets = {}
            for arg in self.farmer["args"]:
                if arg["type"] == "dropdown":
                    widget = QComboBox()
                    widget.addItems(arg["choices"])
                    widget.setCurrentText(arg["default"])
                elif arg["type"] == "checkbox":
                    widget = QCheckBox()
                    widget.setChecked(arg.get("default", False))
                elif arg["type"] == "multiselect":
                    widget = QFrame()
                    widget.setObjectName("multiSelect")
                    widget.setStyleSheet(
                        f"QFrame#multiSelect {{ border: 1px solid {C['border2']}; border-radius: 8px;"
                        f" background: {C['field']}; }}"
                    )
                    _vbox = QVBoxLayout(widget)
                    _vbox.setContentsMargins(10, 8, 10, 8)
                    _vbox.setSpacing(6)
                    widget._checkboxes = []
                    _labels = arg.get("labels") or []
                    for idx, choice in enumerate(arg["choices"]):
                        label = _labels[idx] if idx < len(_labels) else choice
                        cb = QCheckBox(label)
                        cb.setStyleSheet("background: transparent;")
                        cb.setProperty("value", choice)
                        cb.setChecked(choice in arg.get("default", []))
                        _vbox.addWidget(cb)
                        widget._checkboxes.append(cb)
                else:
                    widget = QLineEdit()
                    widget.setText(arg["default"])
                    if arg["type"] == "text" and "choices" in arg:
                        choices_pattern = "|".join(re.escape(choice) for choice in arg["choices"])
                        widget.setValidator(QRegularExpressionValidator(QRegularExpression(f"(?:{choices_pattern})")))
                    if arg["type"] == "secret":
                        widget.setEchoMode(QLineEdit.Password)
                self.arg_widgets[arg["name"]] = widget
                row_label = QLabel(arg["label"])
                row_label.setWordWrap(True)
                row_label.setFixedWidth(118)
                row_label.setStyleSheet(f"color: {C['dim']}; font-size: 13px;")
                args_layout.addRow(row_label, widget)
                self._bind_arg_widget(arg, widget)

                if self.farmer["name"] == "SA Coin Dungeon Farmer" and arg["name"] == "--min-chest-type":
                    widget.currentTextChanged.connect(self.update_sa_chest_warning)
                if arg["name"] == "--whale":
                    widget.stateChanged.connect(self._refresh_whale_mode)
            panel.addLayout(args_layout)

            if self.farmer["name"] == "SA Coin Dungeon Farmer":
                self.sa_chest_warning_label = QLabel()
                self.sa_chest_warning_label.setWordWrap(True)
                self.sa_chest_warning_label.setStyleSheet(
                    f"font-size: 13px; color: {C['text']}; border: 1px solid {C['error']};"
                    f" border-radius: 8px; padding: 8px 10px; background: {_tint(C['error'], 0.10)};"
                )
                self.sa_chest_warning_label.hide()
                panel.addSpacing(10)
                panel.addWidget(self.sa_chest_warning_label)
                self.update_sa_chest_warning(self.arg_widgets["--min-chest-type"].currentText())
            panel.addSpacing(22)
        else:
            self.arg_widgets = {}

        panel.addStretch(1)
        return panel

    def _build_run_controls(self):
        footer = QFrame()
        footer.setObjectName("runFooter")
        footer.setStyleSheet(
            f"QFrame#runFooter {{ background: {C['bg']}; border: none; border-top: 1px solid {C['border']}; }}"
        )
        lay = QVBoxLayout(footer)
        lay.setContentsMargins(20, 14, 20, 12)
        lay.setSpacing(0)
        availability_error = self.farmer.get("availability_error")
        self.start_btn = QPushButton("  START")
        self.start_btn.setIcon(svg_icon("play", "#FFFFFF", 14))
        self.start_btn.setMinimumHeight(46)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(BTN_START)
        self.start_btn.clicked.connect(self._on_start_clicked)
        if availability_error:
            self.start_btn.setEnabled(False)
            self.start_btn.setToolTip(availability_error)
        lay.addWidget(self.start_btn)
        lay.addSpacing(8)

        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setStyleSheet(BTN_PAUSE)
        self.pause_btn.setMinimumHeight(38)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet(BTN_STOP)
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        run_row.addWidget(self.pause_btn)
        run_row.addWidget(self.stop_btn)
        lay.addLayout(run_row)
        lay.addSpacing(6)

        self.resize_btn = QPushButton("  Resize game window")
        self.resize_btn.setIcon(svg_icon("resize", C["dim"], 14))
        self.resize_btn.setStyleSheet(BTN_RESIZE)
        self.resize_btn.setToolTip("Resize the 7DS window to 538×921 so the Farmer can see it.")
        self.resize_btn.clicked.connect(self._on_resize_clicked)
        self.clear_btn = QPushButton("  Clear output")
        self.clear_btn.setIcon(svg_icon("clear", C["dim"], 14))
        self.clear_btn.setStyleSheet(BTN_CLEAR)
        self.clear_btn.setToolTip("Clear the terminal. The Farmer keeps running.")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        utility_row = QHBoxLayout()
        utility_row.setSpacing(4)
        utility_row.addWidget(self.resize_btn)
        utility_row.addStretch(1)
        utility_row.addWidget(self.clear_btn)
        lay.addLayout(utility_row)

        return footer

    def _build_right_panel(self):
        panel = QVBoxLayout()
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setSpacing(0)


        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.document().setMaximumBlockCount(1001)
        _term_font = QFont("Consolas")
        _term_font.setPixelSize(14)
        self.terminal.document().setDefaultFont(_term_font)
        self._default_fmt.setFont(_term_font)
        self.terminal.setStyleSheet(
            f"QTextEdit {{ background: {C['term_bg']}; color: {C['term_text']}; border: none;"
            f" padding: 14px 18px 12px 18px; font-family: {MONO_FONT}; font-size: 13px; }}"
            "QScrollBar::handle:vertical { background: #34343B; }"
            "QScrollBar::handle:vertical:hover { background: #4A4A52; }"
        )
        panel.addWidget(self.terminal, 1)
        panel.addWidget(self._build_session_progress())
        return panel

    def _build_session_progress(self):
        """Widget shown below the terminal with session stats."""
        container = QFrame()
        container.setStyleSheet(f"background: {C['panel2']}; border-top: 1px solid {C['border2']}; border-radius: 5px;")
        outer = QHBoxLayout(container)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(0)

        def section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size: 13px; font-weight: 700; color: {C['muted']};"
                " letter-spacing: 2px; background: transparent; border: none;"
            )
            return lbl

        def make_row(parent_lay, key_text, value_text="--"):
            row = QHBoxLayout()
            row.setSpacing(4)
            key = QLabel(key_text)
            key.setStyleSheet(f"color: {C['dim']}; font-size: 13px; background: transparent; border: none;")
            val = QLabel(value_text)
            val.setStyleSheet(
                f"color: {C['text']}; font-size: 13px; font-weight: 600;" " background: transparent; border: none;"
            )
            val.setAlignment(Qt.AlignRight)
            row.addWidget(key)
            row.addStretch()
            row.addWidget(val)
            parent_lay.addLayout(row)
            return val

        def make_bar_metric(parent_lay, key_text, value_text="--", bar_max=100, bar_color=None):
            val = make_row(parent_lay, key_text, value_text)
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setMaximum(bar_max)
            bar.setValue(0)
            chunk_color = bar_color or C["accent"]
            bar.setStyleSheet(
                f"QProgressBar {{ background: {C['border']}; border: none; border-radius: 2px; }}"
                f"QProgressBar::chunk {{ background: {chunk_color}; border-radius: 2px; }}"
            )
            parent_lay.addWidget(bar)
            parent_lay.addSpacing(4)
            return val, bar

        # Left — Clears
        left_lay = QVBoxLayout()
        left_lay.setSpacing(0)
        left_lay.setContentsMargins(0, 0, 20, 0)
        left_lay.addWidget(section_label("CLEARS"))
        left_lay.addSpacing(4)
        left_lay.addStretch()
        self._sp_clears_lbl, self._sp_clears_bar = make_bar_metric(
            left_lay, "Clears", "0", bar_max=100, bar_color=C["accent"]
        )
        left_lay.addStretch()
        self._sp_pots_lbl, self._sp_pots_bar = make_bar_metric(left_lay, "Stamina Pots", "0", bar_color=C["warning"])
        left_lay.addStretch()
        self._sp_uptime_lbl, self._sp_uptime_bar = make_bar_metric(
            left_lay, "Uptime", "00:00:00", bar_max=_UPTIME_CYCLE_SECS, bar_color=C["blue"]
        )
        left_lay.addStretch()

        # Vertical separator
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet(f"background: {C['border']}; border: none;")

        # Right — Info
        right_lay = QVBoxLayout()
        right_lay.setSpacing(2)
        right_lay.setContentsMargins(20, 0, 0, 0)
        right_lay.addWidget(section_label("INFO"))
        right_lay.addSpacing(4)
        self._sp_last_clear_lbl = make_row(right_lay, "Last clear", "--")
        self._sp_farming_lbl = make_row(right_lay, "Farming", self.farmer["name"])
        right_lay.addSpacing(4)
        self._sp_wins_lbl = make_row(right_lay, "Wins", "0")
        self._sp_wins_lbl.setStyleSheet(
            f"color: {C['running']}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        self._sp_loss_lbl = make_row(right_lay, "Loss", "0")
        self._sp_loss_lbl.setStyleSheet(
            f"color: {C['error']}; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        self._sp_total_lbl = make_row(right_lay, "Total Runs", "0")
        self._sp_winrate_lbl, self._sp_winrate_bar = make_bar_metric(
            right_lay, "Win Rate", "0%", bar_max=100, bar_color=C["running"]
        )
        right_lay.addStretch()

        outer.addLayout(left_lay, 2)
        outer.addWidget(vline)
        outer.addLayout(right_lay, 1)
        return container

    def update_sa_chest_warning(self, chest_type):
        if self.sa_chest_warning_label is None:
            return

        normalized_type = (chest_type or "").strip().lower()

        if normalized_type == "silver":
            self.sa_chest_warning_label.setText(
                "Warning: Selecting silver minimum can take a long time.\n"
                "5% silver + 2% gold: ~15 retries per chest on average.\n"
                "Estimated ~12-13 minutes per chest."
            )
            self.sa_chest_warning_label.show()
            return

        if normalized_type == "gold":
            self.sa_chest_warning_label.setText(
                "Warning: Selecting gold minimum is extremely time-consuming.\n"
                "2% gold: ~50 retries per chest on average.\n"
                "Estimated ~40 minutes per chest."
            )
            self.sa_chest_warning_label.show()
            return

        self.sa_chest_warning_label.hide()

    def get_arg_values(self):
        values = {}
        for arg in self.farmer["args"]:
            widget = self.arg_widgets[arg["name"]]
            if arg["type"] == "dropdown":
                values[arg["name"]] = widget.currentText()
            elif arg["type"] == "checkbox":
                values[arg["name"]] = widget.isChecked()
            elif arg["type"] == "multiselect":
                values[arg["name"]] = [cb.property("value") for cb in widget._checkboxes if cb.isChecked()]
            else:
                values[arg["name"]] = widget.text()
        return values

    def _on_start_clicked(self):
        self.controller.start(self.get_arg_values())
        if _HALLOWEEN and self.controller.process is not None:
            self._append_pumpkin()

    def _on_stop_clicked(self):
        self.controller.stop()

    def _on_pause_clicked(self):
        self.controller.toggle_pause()

    def _on_resize_clicked(self):
        self.controller.resize_window()

    def _on_clear_clicked(self):
        self.controller.clear_output()

    def _bind_arg_widget(self, arg, widget):
        name = arg["name"]
        if arg["type"] == "dropdown":
            widget.currentTextChanged.connect(lambda value, n=name: self.controller.set_arg_value(n, value))
        elif arg["type"] == "checkbox":
            widget.toggled.connect(lambda value, n=name: self.controller.set_arg_value(n, value))
        elif arg["type"] == "multiselect":
            for checkbox in widget._checkboxes:
                checkbox.toggled.connect(
                    lambda _checked, n=name, frame=widget: self.controller.set_arg_value(
                        n, [cb.property("value") for cb in frame._checkboxes if cb.isChecked()]
                    )
                )
        else:
            widget.textChanged.connect(lambda value, n=name: self.controller.set_arg_value(n, value))

    def _sync_arg_widgets(self, values):
        self._syncing_arg_widgets = True
        try:
            for arg in self.farmer["args"]:
                name = arg["name"]
                widget = self.arg_widgets.get(name)
                if widget is None:
                    continue
                value = values.get(name)
                if arg["type"] == "dropdown":
                    widget.blockSignals(True)
                    widget.setCurrentText("" if value is None else str(value))
                    widget.blockSignals(False)
                elif arg["type"] == "checkbox":
                    widget.blockSignals(True)
                    widget.setChecked(bool(value))
                    widget.blockSignals(False)
                elif arg["type"] == "multiselect":
                    selected = set(value or [])
                    for checkbox in widget._checkboxes:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(checkbox.property("value") in selected)
                        checkbox.blockSignals(False)
                else:
                    widget.blockSignals(True)
                    widget.setText("" if value is None else str(value))
                    widget.blockSignals(False)
        finally:
            self._syncing_arg_widgets = False
        if self.farmer["name"] == "SA Coin Dungeon Farmer" and "--min-chest-type" in self.arg_widgets:
            self.update_sa_chest_warning(self.arg_widgets["--min-chest-type"].currentText())
        self._refresh_whale_mode()

    def _append_welcome(self):
        self._append_terminal_centered(FREE_SOFTWARE_MESSAGE)

    def _append_pumpkin(self):
        width = max(len(line) for line in _HALLOWEEN_PUMPKIN)
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        center = QTextBlockFormat()
        center.setAlignment(Qt.AlignCenter)
        if self.terminal.document().isEmpty():
            cursor.setBlockFormat(center)
        else:
            cursor.insertBlock(center)
        for i, line in enumerate(_HALLOWEEN_PUMPKIN):
            fmt = QTextCharFormat(self._default_fmt)
            fmt.setForeground(QColor(C["running"] if i < 2 else C["accent"]))
            if i:
                cursor.insertBlock(center)
            cursor.insertText(line.ljust(width).replace(" ", "\u00a0"), fmt)
        greet = QTextCharFormat(self._default_fmt)
        greet.setForeground(QColor(C["accent"]))
        greet.setFontWeight(QFont.Bold)
        cursor.insertBlock(center)
        cursor.insertBlock(center)
        cursor.insertText("Happy Farming!", greet)
        left = QTextBlockFormat()
        left.setBottomMargin(1)
        cursor.insertBlock(left)
        cursor.insertBlock(left)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def _append_terminal_centered(self, text):
        """Insert text centered in the terminal (used for the initial welcome message)."""
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(Qt.AlignCenter)
        first = True
        for line in text.splitlines():
            if first:
                cursor.setBlockFormat(block_fmt)
                first = False
            else:
                cursor.insertBlock(block_fmt)
            cursor.insertText(line.strip(), self._default_fmt)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def append_terminal(self, text):
        self._render_lines(text.splitlines(True))

    def _auto_line_color(self, line):
        """Return a QColor for the line based on keyword rules, or None for default."""
        for pattern, hex_color in self._LINE_COLOR_RULES:
            if pattern.search(line):
                return QColor(hex_color)
        return None

    def _render_lines(self, lines):
        """Render the given lines at the end of the terminal widget."""
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)

        block_fmt = QTextBlockFormat()
        block_fmt.setBottomMargin(1)

        # Join first so multi-line <color=...> tags are parsed correctly
        full_text = "".join(lines)

        for segment_text, segment_color in self._parse_color_segments(full_text):
            sub_lines = segment_text.split("\n")
            for i, sub_line in enumerate(sub_lines):
                fmt = QTextCharFormat(self._default_fmt)
                if segment_color is not None:
                    fmt.setForeground(segment_color)
                else:
                    auto_color = self._auto_line_color(sub_line)
                    if auto_color is not None:
                        fmt.setForeground(auto_color)
                cursor.insertText(sub_line, fmt)
                if i < len(sub_lines) - 1:
                    cursor.insertBlock(block_fmt)

        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def _parse_color_segments(self, text):
        """Parse <color=...>...</color> tags into (text, QColor|None) segments."""
        if "<color=" not in text.lower():
            return [(text, None)]

        segments = []
        cursor = 0

        for match in self._COLOR_TAG_RE.finditer(text):
            start, end = match.span()
            if start > cursor:
                segments.append((text[cursor:start], None))

            color_value = match.group(1).strip()
            colored_text = match.group(2)
            color = QColor(color_value)
            if not color.isValid():
                color = None

            segments.append((colored_text, color))
            cursor = end

        if cursor < len(text):
            segments.append((text[cursor:], None))

        return segments

    def _on_output_reset(self):
        self.terminal.clear()
        if self.controller.output_lines:
            self._render_lines(self.controller.output_lines)

    def _on_running_changed(self, running: bool, pid: int):
        del pid
        self._refresh_action_buttons()
        if not running:
            self.pause_btn.setText("PAUSE")

    def _on_paused_changed(self, paused: bool):
        self.pause_btn.setText("RESUME" if paused else "PAUSE")
        self._refresh_action_buttons()

    def _refresh_action_buttons(self, *_args):
        running = self.controller.is_running
        busy = self.controller.devtest_busy
        self.start_btn.setEnabled(
            not busy and self.controller.process is None and not self.farmer.get("availability_error")
        )
        self.stop_btn.setEnabled(running)
        self.pause_btn.setEnabled(running and not (busy and self.controller.is_paused))
        self.resize_btn.setEnabled(not busy)

    def _refresh_session_progress(self):
        snapshot = self.controller.get_status_snapshot()
        self._sp_clears_lbl.setText(str(snapshot.session_clears))
        self._sp_farming_lbl.setText(self.farmer["name"])
        if snapshot.last_clear_time is None:
            self._sp_last_clear_lbl.setText("--")
        else:
            self._sp_last_clear_lbl.setText(snapshot.last_clear_time.strftime("%H:%M:%S"))

        if snapshot.session_start_time is None:
            self._sp_uptime_lbl.setText("00:00:00")
            self._sp_uptime_bar.setMaximum(_UPTIME_CYCLE_SECS)
            self._sp_uptime_bar.setValue(0)
        else:
            elapsed = int(time.monotonic() - snapshot.session_start_time)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self._sp_uptime_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")
            self._sp_uptime_bar.setMaximum(_UPTIME_CYCLE_SECS)
            self._sp_uptime_bar.setValue(elapsed % _UPTIME_CYCLE_SECS)

        if snapshot.session_max_clears is not None:
            self._sp_clears_bar.setMaximum(snapshot.session_max_clears)
            self._sp_clears_bar.setValue(min(snapshot.session_clears, snapshot.session_max_clears))
        elif snapshot.is_running:
            self._sp_clears_bar.setMaximum(0)
            self._sp_clears_bar.setValue(0)
        else:
            self._sp_clears_bar.setMaximum(100)
            self._sp_clears_bar.setValue(0)

        # Wins / Loss / Total / Win Rate
        wins = snapshot.session_clears
        losses = snapshot.session_losses
        total = wins + losses
        rate = int(wins / total * 100) if total > 0 else 0
        self._sp_wins_lbl.setText(str(wins))
        self._sp_loss_lbl.setText(str(losses))
        self._sp_total_lbl.setText(str(total))
        self._sp_winrate_lbl.setText(f"{rate}%")
        self._sp_winrate_bar.setValue(rate)

        # Stamina Pots
        pots = snapshot.session_pots
        self._sp_pots_lbl.setText(str(pots))
        max_pots_raw = self.controller.get_arg_values().get("max_stamina_pots")
        try:
            max_pots = int(float(str(max_pots_raw)))
            self._sp_pots_bar.setMaximum(max_pots)
            self._sp_pots_bar.setValue(min(pots, max_pots))
        except (TypeError, ValueError):
            self._sp_pots_bar.setMaximum(max(pots, 1))
            self._sp_pots_bar.setValue(pots)

    def _on_status_snapshot_changed(self, _snapshot):
        if not self._syncing_arg_widgets:
            self._refresh_session_progress()

    def _sync_from_controller(self):
        self._sync_arg_widgets(self.controller.get_arg_values())
        self._on_output_reset()
        if not self.controller.output_lines and self.controller.process is None:
            self._append_welcome()
        self._on_running_changed(self.controller.is_running, self.controller.process_id)
        self._on_paused_changed(self.controller.is_paused)
        self._refresh_session_progress()

    def load_farmer_image(self, image_filename=None):
        image_path = get_farmer_image_path(self.farmer, image_filename)
        if image_path is None:
            return

        if os.path.exists(image_path):
            pixmap = _cover_pixmap(image_path, *self.image_size)
            if pixmap is not None:
                self.image_label.setPixmap(_round_all(pixmap, 8))
                self.image_label.setStyleSheet(f"border: none; border-radius: 8px; background: {C['panel2']};")
            else:
                self.image_label.setText(f"Couldn't load image:\n{os.path.basename(image_path)}")
        else:
            self.image_label.setText(f"Image not found:\n{os.path.basename(image_path)}")

    def _refresh_whale_mode(self):
        """Update image and requirements when whale-mode checkbox changes."""
        farmer_name = self.farmer["name"]
        if farmer_name not in WHALE_MODE_CONFIG:
            return

        whale_enabled = "--whale" in self.arg_widgets and self.arg_widgets["--whale"].isChecked()
        requirements_key, image_filename = get_farmer_display_content(farmer_name, whale_enabled)

        if self.req_label is not None:
            self.req_label.setText(REQUIREMENTS.get(requirements_key, ""))
            self.req_label.adjustSize()
            self._fit_requirements()

        self.load_farmer_image(image_filename)


CHAPTERS = [
    {
        "id": "beasts",
        "icon": "paw",
        "title": "Demonic Beasts",
        "color": INK_CYAN,
        "blurb": "Bird, Deer, Dogs, Snake and Rat fights, floors 1 to 4, plus the beast rotation.",
        "farmers": (
            "Bird Farmer",
            "Bird Floor 4",
            "Deer Farmer",
            "Deer Floor 4",
            "Dogs Farmer",
            "Dogs Floor 4",
            "Snake Farmer",
            "Rat Farmer",
            "Demonic Beast Rotation",
        ),
    },
    {
        "id": "demons",
        "icon": "horns",
        "title": "Demons & Raids",
        "color": INK_MAGENTA,
        "blurb": "Real-time demon invites, the Demon King and Guild Boss.",
        "farmers": ("Demon Farmer", "Demon King Farmer", "Guild Boss Farmer"),
    },
    {
        "id": "bosses",
        "icon": "crown",
        "title": "Bosses & Events",
        "color": INK_YELLOW,
        "blurb": "Final Boss, Legendary Boss, Boss Battle and SA Coin Dungeon.",
        "farmers": ("Final Boss", "Legendary Boss", "Boss Battle Farmer", "SA Coin Dungeon Farmer"),
    },
    {
        "id": "daily",
        "icon": "calendar",
        "title": "Dailies & Account",
        "color": INK_VIOLET,
        "blurb": "Daily quests, gold, account chores, auto clears and constellation rerolls.",
        "farmers": (
            "Daily Quests Farmer",
            "Gold Farmer",
            "Accounts Farmer",
            "Auto Clear Farmer",
            "Reroll Constellation",
        ),
    },
    {
        "id": "private",
        "icon": "key",
        "title": "Private Farmers",
        "color": INK_ORANGE,
        "blurb": "Free compiled Farmers. Some need a free license key the first time you use them.",
        "farmers": (),
    },
    {
        "id": "other",
        "icon": "grid",
        "title": "More Farmers",
        "color": INK_SLATE,
        "blurb": "Farmers that don't belong to another group yet.",
        "farmers": (),
    },
]

_STARTER_FARMERS = ("Bird Farmer", "Deer Farmer")
_RECENT_FILE = os.path.join(_CONFIG_DIR, ".recent_farmers.json")
_RECENT_LIMIT = 4


def build_chapters(farmers: list[dict]) -> list[dict]:
    by_name = {f["name"]: f for f in farmers}
    placed: set[str] = set()
    chapters = []
    for spec in CHAPTERS:
        members = []
        if spec["id"] == "private":
            members = [f for f in farmers if f.get("compiled_extension") and f["name"] not in placed]
        elif spec["id"] == "other":
            members = [f for f in farmers if f["name"] not in placed]
        else:
            members = [by_name[n] for n in spec["farmers"] if n in by_name and n not in placed]
        if not members:
            continue
        placed.update(f["name"] for f in members)
        chapters.append({**spec, "members": members})
    return chapters


def _farmer_summary(farmer: dict) -> str:
    labels = []
    for arg in farmer.get("args", []):
        if arg.get("type") == "secret":
            continue
        label = re.sub(r"\s*\(.*?\)", "", arg["label"]).strip()
        if label and label not in labels:
            labels.append(label)
    if not labels:
        return "No settings needed. Press START."
    return " · ".join(labels[:4]) + (" · and more" if len(labels) > 4 else "")


class RecentStore(QObject):
    favorites_changed = pyqtSignal()

    def __init__(self, path: str = _RECENT_FILE):
        super().__init__()
        self._path = path
        self.recent: list[str] = []
        self.favorites: list[str] = []
        self.last_runs: dict[str, dict] = {}
        try:
            with open(self._path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.recent = [n for n in data.get("recent", []) if isinstance(n, str)][:_RECENT_LIMIT]
            self.favorites = [n for n in data.get("favorites", []) if isinstance(n, str)]
            runs = data.get("last_runs", {})
            if isinstance(runs, dict):
                self.last_runs = {k: v for k, v in runs.items() if isinstance(v, dict)}
        except (OSError, ValueError):
            pass

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(
                    {"recent": self.recent, "favorites": self.favorites, "last_runs": self.last_runs}, fh, indent=2
                )
        except OSError:
            pass

    def is_favorite(self, name: str) -> bool:
        return name in self.favorites

    def toggle_favorite(self, name: str):
        if name in self.favorites:
            self.favorites.remove(name)
        else:
            self.favorites.append(name)
        self._save()
        self.favorites_changed.emit()

    def touch(self, name: str):
        self.recent = [name] + [n for n in self.recent if n != name]
        self.recent = self.recent[:_RECENT_LIMIT]
        self._save()

    def record_run(self, name: str, clears: int, ended_on_its_own: bool):
        self.last_runs[name] = {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "clears": int(clears),
            "how": "ended" if ended_on_its_own else "stopped",
        }
        self._save()

    def stamp(self, name: str) -> str:
        run = self.last_runs.get(name)
        if not run:
            return "Not run yet"
        when = run.get("time", "")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        when = when.split(" ", 1)[1] if when.startswith(today) and " " in when else when
        verb = "Ended" if run.get("how") == "ended" else "Stopped"
        clears = run.get("clears", 0)
        return f"{verb} {when} · {clears} clear{'s' if clears != 1 else ''}"


def _cover_pixmap(path: str | None, width: int, height: int) -> QPixmap | None:
    if not path or not os.path.exists(path):
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - width) // 2)
    y = max(0, (scaled.height() - height) // 2)
    return scaled.copy(x, y, width, height)


def _round_all(pixmap: QPixmap, radius: int, top_only: bool = False) -> QPixmap:
    image = QImage(pixmap.width(), pixmap.height(), QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
    if top_only:
        square_bottom = QPainterPath()
        square_bottom.addRect(0, pixmap.height() / 2, pixmap.width(), pixmap.height() / 2)
        path = path.united(square_bottom)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QPixmap.fromImage(image)


def _art_label(farmer: dict, width: int, height: int, top_only: bool = False) -> QLabel:
    label = QLabel()
    label.setFixedSize(width, height)
    label.setAlignment(Qt.AlignCenter)
    pixmap = _cover_pixmap(get_farmer_image_path(farmer), width, height)
    if pixmap is not None:
        label.setPixmap(_round_all(pixmap, 7 if top_only else 6, top_only))
        label.setStyleSheet("background: transparent; border: none;")
    else:
        label.setText(farmer["name"][:1])
        label.setStyleSheet(
            f"background: {C['panel2']}; color: {C['muted']}; font-size: 18px; font-weight: 700; border: none;"
        )
    return label


class HangingSpider(QWidget):
    _W = 34

    def __init__(self, min_len: int, max_len: int, period: float, phase: float, parent=None):
        super().__init__(parent)
        self._min_len = min_len
        self._max_len = max_len
        self._period = period
        self._phase = phase
        self._t = 0.0
        self.setFixedSize(self._W, max_len + 26)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")

    def advance(self, t: float):
        self._t = t
        self.update()

    def paintEvent(self, event):
        del event
        t = self._t
        wave = 0.5 + 0.5 * math.sin(2 * math.pi * t / self._period + self._phase)
        length = self._min_len + (self._max_len - self._min_len) * wave
        cx = self._W / 2 + 2.0 * math.sin(t * 1.3 + self._phase)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        thread = QColor(C["dim"])
        thread.setAlpha(110)
        painter.setPen(thread)
        painter.drawLine(int(self._W / 2), 0, int(cx), int(length))
        leg = QColor(C["text"])
        leg.setAlpha(170)
        pen = painter.pen()
        pen.setColor(leg)
        pen.setWidthF(1.3)
        painter.setPen(pen)
        wiggle = math.sin(t * 7 + self._phase) * 1.5
        for i, (dx, dy) in enumerate(((9, -5), (11, -1), (11, 3), (9, 7))):
            w = wiggle if i % 2 == 0 else -wiggle
            by = length + 6 + (i - 1.5) * 2.2
            for side in (-1, 1):
                knee_x = cx + side * (dx * 0.6)
                knee_y = by + dy * 0.5 - 3 + w * 0.5
                painter.drawLine(int(cx), int(by), int(knee_x), int(knee_y))
                painter.drawLine(int(knee_x), int(knee_y), int(cx + side * dx), int(by + dy + w))
        painter.setPen(QColor(C["dark"]))
        painter.setBrush(QColor("#05030A"))
        painter.drawEllipse(int(cx - 6), int(length + 3), 12, 12)
        painter.drawEllipse(int(cx - 4), int(length - 3), 8, 7)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(C["accent"]))
        painter.drawEllipse(int(cx - 3), int(length - 1), 2, 2)
        painter.drawEllipse(int(cx + 1), int(length - 1), 2, 2)
        painter.end()


class CrawlingSpider(QWidget):
    SIZE = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self._angle = 0.0
        self._gait = 0.0
        self.hide()

    def pose(self, angle_deg: float, gait: float):
        self._angle = angle_deg
        self._gait = gait
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.SIZE / 2, self.SIZE / 2)
        painter.rotate(self._angle)
        painter.scale(1.4, 1.4)
        leg = QColor(C["text"])
        leg.setAlpha(190)
        pen = painter.pen()
        pen.setColor(leg)
        pen.setWidthF(1.4)
        painter.setPen(pen)
        for i, base in enumerate((-6.0, -2.0, 2.0, 6.0)):
            swing = math.sin(self._gait + (math.pi if i % 2 else 0.0)) * 3.5
            for side in (-1, 1):
                knee = (base * 0.8 + swing * 0.5, side * 9.0)
                foot = (base * 1.6 + swing, side * 16.0)
                painter.drawLine(int(base * 0.5), 0, int(knee[0]), int(knee[1]))
                painter.drawLine(int(knee[0]), int(knee[1]), int(foot[0]), int(foot[1]))
        painter.setPen(QColor(C["dark"]))
        painter.setBrush(QColor("#05030A"))
        painter.drawEllipse(-11, -6, 13, 12)
        painter.drawEllipse(1, -4, 9, 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(C["accent"]))
        painter.drawEllipse(7, -3, 2, 2)
        painter.drawEllipse(7, 1, 2, 2)
        painter.end()


class HalloweenOverlay(QObject):
    def __init__(self, host: QWidget):
        super().__init__(host)
        self._host = host
        self._t0 = time.monotonic()
        self._spiders = [
            (0.42, HangingSpider(18, 70, 7.0, 0.0, host)),
            (0.71, HangingSpider(30, 120, 9.5, 2.1, host)),
            (0.56, HangingSpider(14, 52, 6.0, 4.0, host)),
        ]
        self._web = QLabel(host)
        self._web.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._web.setStyleSheet("background: transparent;")
        self._web.setPixmap(_cobweb_pixmap(64, C["dark"]))
        self._web.resize(64, 64)
        self._crawler = CrawlingSpider(host)
        self._crawl = None
        self._next_crawl = time.monotonic() + 20.0
        host.installEventFilter(self)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)
        self.place()

    def place(self):
        width = self._host.width()
        rail = IndexRail._W
        page = max(1, width - rail)
        for frac, spider in self._spiders:
            spider.move(int(rail + page * frac - spider.width() / 2), 0)
            spider.raise_()
        self._web.move(width - self._web.width(), 0)
        self._web.raise_()

    def eventFilter(self, obj, event):
        if obj is self._host and event.type() == event.Resize:
            self.place()
        return False

    def start_crawl(self):
        width, height = self._host.width(), self._host.height()
        size = CrawlingSpider.SIZE
        direction = random.choice((1, -1))
        x0, x1 = (-size, width) if direction == 1 else (width, -size)
        y0 = random.uniform(140, max(160, height - 120))
        duration = width / random.uniform(150.0, 210.0)
        self._crawl = (time.monotonic(), duration, x0, x1, y0, random.uniform(18, 40), direction)
        self._crawler.show()
        self._crawler.raise_()

    def _update_crawl(self, now: float):
        if self._crawl is None:
            if now >= self._next_crawl:
                self.start_crawl()
            return
        t0, duration, x0, x1, y0, amp, direction = self._crawl
        progress = (now - t0) / duration
        if progress >= 1.0:
            self._crawl = None
            self._crawler.hide()
            self._next_crawl = now + random.uniform(45.0, 120.0)
            return
        x = x0 + (x1 - x0) * progress
        wobble = 2 * math.pi * progress * 2
        y = y0 + amp * math.sin(wobble)
        dy = amp * math.cos(wobble) * 2 * math.pi * 2 / max(1.0, abs(x1 - x0))
        angle = math.degrees(math.atan2(dy * direction, 1.0)) + (0 if direction == 1 else 180)
        self._crawler.move(int(x), int(y))
        self._crawler.pose(angle, (now - t0) * 18.0)

    def _tick(self):
        if not self._host.isVisible() or self._host.window().isMinimized():
            return
        now = time.monotonic()
        t = now - self._t0
        for _frac, spider in self._spiders:
            spider.advance(t)
        self._update_crawl(now)


class StateBadge(QWidget):
    def __init__(self, large: bool = False, parent=None):
        super().__init__(parent)
        self._large = large
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8 if large else 6)
        dot_size = 10 if large else 7
        self._dot = QLabel()
        self._dot.setFixedSize(dot_size, dot_size)
        self._dot_size = dot_size
        lay.addWidget(self._dot, 0, Qt.AlignVCenter)
        self._label = QLabel()
        lay.addWidget(self._label, 0, Qt.AlignVCenter)
        self._fade = QGraphicsOpacityEffect(self._dot)
        self._dot.setGraphicsEffect(self._fade)
        self._pulse = QPropertyAnimation(self._fade, b"opacity", self)
        self._pulse.setDuration(1400)
        self._pulse.setKeyValueAt(0.0, 1.0)
        self._pulse.setKeyValueAt(0.5, 0.15)
        self._pulse.setKeyValueAt(1.0, 1.0)
        self._pulse.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse.setLoopCount(-1)
        self.hide()

    def set_state(self, state: str):
        styles = {
            "running": ("Running", C["running"]),
            "paused": ("Paused", C["warning"]),
            "unavailable": ("Unavailable", C["muted"]),
        }
        if state not in styles:
            self._pulse.stop()
            self.hide()
            return
        text, color = styles[state]
        size = 15 if self._large else 12
        self._label.setText(text)
        self._label.setStyleSheet(f"background: transparent; color: {color}; font-size: {size}px; font-weight: 700;")
        self._dot.setStyleSheet(f"background: {color}; border-radius: {self._dot_size // 2}px;")
        self._dot.setVisible(state in ("running", "paused"))
        if state == "running":
            if self._pulse.state() != QPropertyAnimation.Running:
                self._pulse.start()
        else:
            self._pulse.stop()
            self._fade.setOpacity(1.0)
        self.show()


def _state_badge(large: bool = False) -> StateBadge:
    return StateBadge(large)


def _set_badge(badge: StateBadge, state: str):
    badge.set_state(state)


def _controller_state(farmer: dict, controller) -> str:
    if controller.is_running:
        return "paused" if controller.is_paused else "running"
    if farmer.get("availability_error"):
        return "unavailable"
    return ""


def _page_title(text: str, size: int = 20, color: str | None = None) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: {size}px; font-weight: 700; color: {color or C['text']}; background: transparent;")
    return lbl


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {C['text']};")
    return lbl


def _muted(text: str, size: int = 13) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size: {size}px; color: {C['muted']}; background: transparent;")
    return lbl


class _Clickable(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class VersionSwitch(QWidget):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._index = -1
        self._buttons: list[QPushButton] = []
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)

    def addItem(self, text, data=None):
        short = text.split(" (")[0]
        button = QPushButton(short)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(text)
        idx = len(self._items)
        button.clicked.connect(lambda _=False, i=idx: self._on_clicked(i))
        self._items.append((text, data))
        self._buttons.append(button)
        self._lay.addWidget(button, 1)
        self._restyle()

    def _on_clicked(self, index):
        if index == self._index:
            self._restyle()
            return
        self.setCurrentIndex(index)

    def findData(self, data):
        for i, (_text, item_data) in enumerate(self._items):
            if item_data == data:
                return i
        return -1

    def currentData(self):
        return self._items[self._index][1] if 0 <= self._index < len(self._items) else None

    def currentIndex(self):
        return self._index

    def setCurrentIndex(self, index):
        if index == self._index or not 0 <= index < len(self._items):
            self._restyle()
            return
        self._index = index
        self._restyle()
        self.currentIndexChanged.emit(index)

    def setMinimumWidth(self, width):
        super().setMinimumWidth(width)

    def changeEvent(self, event):
        if not self.isEnabled():
            for button in self._buttons:
                if button.hasFocus():
                    button.clearFocus()
        super().changeEvent(event)
        self._restyle()

    def _restyle(self):
        enabled = self.isEnabled()
        last = len(self._buttons) - 1
        for i, button in enumerate(self._buttons):
            on = i == self._index
            button.setChecked(on)
            left = "8px" if i == 0 else "0"
            right = "8px" if i == last else "0"
            bg = C["home_ink"] if on else C["field"]
            fg = C["on_home"] if on else C["text"]
            if not enabled:
                bg = C["dark"] if on else C["panel2"]
                fg = C["bg"] if on else C["dark"]
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {C['home_ink'] if enabled else C['border2']};"
                f" border-top-left-radius: {left}; border-bottom-left-radius: {left};"
                f" border-top-right-radius: {right}; border-bottom-right-radius: {right};"
                f" {'border-left: none;' if i > 0 else ''} padding: 6px 0; font-size: 13px; font-weight: 700; }}"
                f"QPushButton:hover {{ background: {bg if on else C['panel2']}; }}"
                f"QPushButton:focus {{ border-color: {C['accent']}; }}"
            )

    def setToolTip(self, text):
        super().setToolTip(text)
        for button in self._buttons:
            button.setToolTip(text)


class IndexRow(_Clickable):
    def __init__(self, key, title, color, count=None, icon=None, parent=None):
        super().__init__(parent)
        self.key = key
        self.color = color
        self._icon_name = icon
        self._active = False
        self._running = False
        self.setFixedHeight(40)
        self.setObjectName("indexRow")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 16, 0)
        lay.setSpacing(10)
        self._mark = QLabel()
        self._mark.setFixedSize(16, 16)
        lay.addWidget(self._mark)
        self._title = QLabel(title)
        lay.addWidget(self._title, 1)
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setToolTip("A Farmer here is running")
        lay.addWidget(self._dot)
        self._count = QLabel("" if count is None else str(count))
        lay.addWidget(self._count)
        self._restyle()

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self._restyle()

    def set_running(self, running: bool):
        if self._running != running:
            self._running = running
            self._restyle()

    def _restyle(self):
        on = _on_ink(self.color) if self._active else C["text"]
        bg = self.color if self._active else "transparent"
        hover = "" if self._active else f"QFrame#indexRow:hover {{ background: {C['panel2']}; }}"
        self.setStyleSheet(
            f"QFrame#indexRow {{ background: {bg}; border: none; border-radius: 8px; margin: 1px 8px; }}{hover}"
            f"QFrame#indexRow:focus {{ border: 1px solid {C['accent']}; }}"
        )
        weight = 700
        self._title.setStyleSheet(f"color: {on}; font-size: 13px; font-weight: {weight}; background: transparent;")
        self._count.setStyleSheet(
            f"color: {on if self._active else C['muted']}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        icon_color = C["running"] if self._running and not self._active else on
        if self._icon_name:
            self._mark.setPixmap(svg_icon(self._icon_name, icon_color, 16).pixmap(16, 16))
        self._mark.setStyleSheet("background: transparent;")
        self._mark.setToolTip("A Farmer here is running" if self._running else "")
        if self._running and self._active:
            self._dot.setStyleSheet(f"background: {C['running']}; border-radius: 4px; border: 1.5px solid {on};")
            self._dot.show()
        else:
            self._dot.hide()

    def set_count(self, count):
        self._count.setText("" if count is None else str(count))


class IndexRail(QWidget):
    navigate = pyqtSignal(str)
    theme_toggled = pyqtSignal()
    halloween_toggled = pyqtSignal()

    _W = 220

    def __init__(self, chapters, game_version_combo: QWidget, favorites_count: int = 0, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self._W)
        self.setObjectName("indexRail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"QWidget#indexRail {{ background: {C['rail']}; border-right: 1px solid {C['border']}; }}")
        self._rows: dict[str, IndexRow] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QWidget()
        head.setObjectName("railHead")
        head.setAttribute(Qt.WA_StyledBackground, True)
        head.setStyleSheet("QWidget#railHead { background: transparent; }")
        head_lay = QVBoxLayout(head)
        head_lay.setContentsMargins(18, 20, 16, 16)
        head_lay.setSpacing(2)
        mark = QLabel()
        mark.setTextFormat(Qt.RichText)
        mark.setText(
            f'<span style="font-size:19px;font-weight:800;color:{_WORDMARK_TEXT};">Auto</span>'
            f'<span style="font-size:19px;font-weight:800;color:{_WORDMARK_ACCENT};">Farmers</span>'
        )
        head_lay.addWidget(mark)
        head_lay.addWidget(_muted("7DS Grand Cross", 12))
        if _HALLOWEEN:
            boo = QLabel("Happy Halloween")
            boo.setStyleSheet(f"color: {C['accent']}; font-size: 12px; font-weight: 700; background: transparent;")
            head_lay.addWidget(boo)
            web = QLabel(head)
            web.setPixmap(_cobweb_pixmap(56, C["dark"]))
            web.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            web.setStyleSheet("background: transparent;")
            web.setGeometry(self._W - 57, 0, 56, 56)
        head_lay.addSpacing(14)
        version_lbl = QLabel("Game version")
        version_lbl.setStyleSheet(f"color: {C['dim']}; font-size: 12px; font-weight: 700;")
        head_lay.addWidget(version_lbl)
        head_lay.addSpacing(4)
        head_lay.addWidget(game_version_combo)
        lay.addWidget(head)

        self._add_row(lay, IndexRow("home", "Home", C["home_ink"], icon="home"))
        self._add_row(lay, IndexRow("favorites", "Favorites", C["home_ink"], count=favorites_count or None,
                                    icon="star"))
        self._add_row(lay, IndexRow("rewards", "Rewards summary", C["home_ink"], icon="gift"))
        for ch in chapters:
            self._add_row(lay, IndexRow(ch["id"], ch["title"], ch["color"], count=None,
                                        icon=ch.get("icon", "grid")))

        filler = QWidget()
        filler.setObjectName("railFiller")
        filler.setAttribute(Qt.WA_StyledBackground, True)
        filler.setStyleSheet("QWidget#railFiller { background: transparent; }")
        lay.addWidget(filler, 1)

        foot_rule = QFrame()
        foot_rule.setFixedHeight(1)
        foot_rule.setStyleSheet(f"background: {C['border']}; border: none;")
        lay.addWidget(foot_rule)
        self._add_row(lay, IndexRow("settings", "Settings", C["home_ink"], icon="settings"))
        self._add_row(lay, IndexRow("devtest", "DevTest", C["home_ink"], icon="flask"))
        self._add_row(lay, IndexRow("about", "About & updates", C["home_ink"], icon="info"))

        dark = _ACTIVE_THEME != "light"
        self.theme_btn = IndexRow("theme", "Light theme" if dark else "Dark theme", C["home_ink"],
                                  icon="sun" if dark else "moon")
        self.theme_btn.setToolTip("Switches the look and reopens the window. Stop running Farmers first.")
        self.theme_btn.clicked.connect(self.theme_toggled)
        lay.addWidget(self.theme_btn)
        self.halloween_btn = IndexRow(
            "halloween", "Exit Halloween" if _HALLOWEEN else "Halloween theme", C["home_ink"], icon="pumpkin"
        )
        self.halloween_btn.setToolTip(
            "Back to the dark theme. Reopens the window." if _HALLOWEEN
            else "Spooky colours for the season. Reopens the window. Stop running Farmers first."
        )
        self.halloween_btn.clicked.connect(self.halloween_toggled)
        lay.addWidget(self.halloween_btn)
        lay.addSpacing(8)

    def _add_row(self, lay, row: IndexRow):
        row.clicked.connect(lambda key=row.key: self.navigate.emit(key))
        self._rows[row.key] = row
        lay.addWidget(row)

    def set_active(self, key: str):
        for row_key, row in self._rows.items():
            row.set_active(row_key == key)

    def set_favorites_count(self, count: int):
        self._rows["favorites"].set_count(count or None)

    def set_running_chapters(self, chapter_ids: set):
        for row_key, row in self._rows.items():
            row.set_running(row_key in chapter_ids)


class _PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", back_text: str = "", back_callback=None,
                 height: int = 92, parent=None):
        super().__init__(parent)
        self._back_callback = back_callback
        self.setObjectName("pageHeader")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(height)
        on = C["text"]
        self.setStyleSheet(f"QWidget#pageHeader {{ background: {C['bg']}; border-bottom: 1px solid {C['border']}; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 0, 24, 0)
        lay.setSpacing(16)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.addStretch(1)
        if back_callback is not None:
            back = QPushButton("  " + back_text.replace("&", "&&"))
            back.setIcon(svg_icon("back", on, 14))
            back.setCursor(Qt.PointingHandCursor)
            back.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {on}; border: none; padding: 0;"
                " font-size: 12px; font-weight: 700; text-align: left; }"
                "QPushButton:hover { text-decoration: underline; }"
            )
            self._back_callback = back_callback
            back.clicked.connect(lambda _checked=False: self._back_callback())
            text_col.addWidget(back, 0, Qt.AlignLeft)
        self.back_btn = back if back_callback is not None else None
        self.title_label = _page_title(title, 24, on)
        text_col.addWidget(self.title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {C['muted']}; font-size: 13px; background: transparent;")
            text_col.addWidget(sub)
        text_col.addStretch(1)
        lay.addLayout(text_col, 1)
        self.right = QHBoxLayout()
        self.right.setSpacing(10)
        lay.addLayout(self.right)

    def set_back(self, text: str, callback):
        if self.back_btn is None:
            return
        self.back_btn.setText("  " + text.replace("&", "&&"))
        self._back_callback = callback


class FavoriteButton(QPushButton):
    def __init__(self, name: str, recent: "RecentStore", on_color: str | None = None, with_text: bool = False,
                 parent=None):
        super().__init__(parent)
        self._name = name
        self._recent = recent
        self._on_color = on_color
        self._with_text = with_text
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.clicked.connect(lambda _checked=False: self._recent.toggle_favorite(self._name))
        recent.favorites_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        fav = self._recent.is_favorite(self._name)
        base = self._on_color or C["muted"]
        star_color = INK_YELLOW if fav and self._on_color is None else base
        self.setIcon(svg_icon("star_fill" if fav else "star", star_color, 18))
        self.setToolTip("Remove from Favorites" if fav else "Add to Favorites")
        if self._with_text:
            self.setText("  Favorite" if fav else "  Add to favorites")
        border = f"1.5px solid {base}" if self._with_text else "none"
        self.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {base}; border: {border}; border-radius: 8px;"
            f" padding: {'6px 12px' if self._with_text else '6px'}; font-size: 12px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {_tint(base, 0.14)}; }}"
            f"QPushButton:focus {{ border: 1px solid {C['accent']}; }}"
        )


class FarmerRow(_Clickable):
    def __init__(self, farmer, controller, recent: RecentStore, parent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.controller = controller
        self._recent = recent
        self.setObjectName("farmerRow")
        self.setStyleSheet(
            f"QFrame#farmerRow {{ background: transparent; border: none; border-bottom: 1px solid {C['border']}; }}"
            f"QFrame#farmerRow:hover {{ background: {C['tile_hover']}; }}"
            f"QFrame#farmerRow:focus {{ background: {C['tile_hover']}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 12, 24, 12)
        lay.setSpacing(18)
        lay.addWidget(_art_label(farmer, 144, 81))
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addStretch(1)
        name = QLabel(farmer["name"])
        name.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C['text']}; background: transparent;")
        col.addWidget(name)
        col.addWidget(_muted(_farmer_summary(farmer)))
        col.addStretch(1)
        lay.addLayout(col, 1)
        right = QVBoxLayout()
        right.setSpacing(6)
        right.addStretch(1)
        self.badge = _state_badge()
        right.addWidget(self.badge, 0, Qt.AlignRight)
        right.addStretch(1)
        lay.addLayout(right)
        lay.addWidget(FavoriteButton(farmer["name"], recent))
        chevron = QLabel()
        chevron.setPixmap(svg_icon("chevron", C["dark"], 16).pixmap(16, 16))
        chevron.setStyleSheet("background: transparent;")
        lay.addWidget(chevron)
        if farmer.get("availability_error"):
            self.setToolTip(farmer["availability_error"])
        self.refresh()

    def refresh(self, *_args):
        state = _controller_state(self.farmer, self.controller)
        _set_badge(self.badge, state)


class ChapterPage(QWidget):
    farmer_selected = pyqtSignal(str)

    def __init__(self, chapter, controllers, recent: RecentStore, parent=None):
        super().__init__(parent)
        self.chapter = chapter
        self._rows: list[FarmerRow] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        count = len(chapter["members"])
        header = _PageHeader(chapter["title"], chapter["blurb"], height=80)
        numeral = QLabel(f"{count}<span style='font-size:13px;'> Farmer{'s' if count != 1 else ''}</span>")
        numeral.setTextFormat(Qt.RichText)
        numeral.setStyleSheet(
            f"color: {C['text']}; font-size: 30px; font-weight: 700; background: transparent;"
        )
        lay.addWidget(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 8, 0, 24)
        body_lay.setSpacing(0)
        for farmer in chapter["members"]:
            controller = controllers[farmer["name"]]
            row = FarmerRow(farmer, controller, recent)
            row.clicked.connect(lambda n=farmer["name"]: self.farmer_selected.emit(n))
            controller.running_changed.connect(row.refresh)
            controller.paused_changed.connect(row.refresh)
            self._rows.append(row)
            body_lay.addWidget(row)
        body_lay.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)

    def refresh(self):
        for row in self._rows:
            row.refresh()


class FavoritesPage(QWidget):
    farmer_selected = pyqtSignal(str)

    def __init__(self, farmers_by_name, controllers, recent: RecentStore, parent=None):
        super().__init__(parent)
        self._farmers = farmers_by_name
        self._controllers = controllers
        self._recent = recent
        self._rows: list[FarmerRow] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_PageHeader("Favorites", "Your saved Farmers, ready to start.",
                                  height=80))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(0, 8, 0, 24)
        self._body.setSpacing(0)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        recent.favorites_changed.connect(self.rebuild)
        self.rebuild()

    def rebuild(self):
        while self._body.count():
            item = self._body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._rows = []
        names = [n for n in self._recent.favorites if n in self._farmers]
        if not names:
            empty = QWidget()
            empty_lay = QVBoxLayout(empty)
            empty_lay.setContentsMargins(28, 28, 28, 0)
            empty_lay.setSpacing(6)
            star = QLabel()
            star.setPixmap(svg_icon("star", C["dark"], 32).pixmap(32, 32))
            empty_lay.addWidget(star)
            empty_lay.addWidget(_section_title("No favorites yet"))
            empty_lay.addWidget(_muted("Press the star next to any Farmer, or on its page, to keep it here."))
            self._body.addWidget(empty)
        for name in names:
            controller = self._controllers[name]
            row = FarmerRow(self._farmers[name], controller, self._recent)
            row.clicked.connect(lambda n=name: self.farmer_selected.emit(n))
            controller.running_changed.connect(row.refresh)
            controller.paused_changed.connect(row.refresh)
            self._rows.append(row)
            self._body.addWidget(row)
        self._body.addStretch(1)

    def refresh(self):
        for row in self._rows:
            row.refresh()


class RewardTile(QFrame):
    def __init__(self, label: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.setObjectName("rewardTile")
        self.setStyleSheet(
            f"QFrame#rewardTile {{ background: {C['panel2']}; border: 1px solid {C['border']}; border-radius: 8px; }}"
        )
        self.setMinimumHeight(72)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent; border: none;")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon.setPixmap(pixmap.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon.setPixmap(svg_icon("gift", C["muted"], 24).pixmap(24, 24))
        lay.addWidget(icon, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(label)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {C['dim']}; font-size: 12px; background: transparent; border: none;")
        col.addWidget(name)
        self.total = QLabel("0")
        self.total.setStyleSheet(f"color: {C['text']}; font-size: 15px; font-weight: 700; background: transparent; border: none;")
        col.addWidget(self.total)
        self.last = QLabel("")
        self.last.setStyleSheet(f"color: {C['running']}; font-size: 11px; background: transparent; border: none;")
        col.addWidget(self.last)
        col.addStretch(1)
        lay.addLayout(col, 1)

    def set_counts(self, total: int, gained: int | None):
        self.total.setText(f"{total:,}")
        self.last.setText(f"+{gained:,} last run" if gained else "")


class RewardSection(QFrame):
    _COLS = 4

    def __init__(self, reward_set: RewardSet, controller: FarmerController, color: str, parent=None):
        super().__init__(parent)
        self._controller = controller
        self.setObjectName("rewardSection")
        self.setStyleSheet(
            f"QFrame#rewardSection {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 16)
        lay.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(16, 14, 16, 12)
        head.setSpacing(8)
        mark = QLabel()
        mark.setPixmap(svg_icon("gift", color, 16).pixmap(16, 16))
        mark.setStyleSheet("background: transparent; border: none;")
        head.addWidget(mark)
        title = QLabel(reward_set.title)
        title.setStyleSheet(f"color: {C['text']}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        head.addWidget(title)
        head.addStretch(1)
        self._status = QLabel()
        self._status.setStyleSheet(f"color: {C['muted']}; font-size: 12px; background: transparent; border: none;")
        head.addWidget(self._status)
        lay.addLayout(head)
        grid = QGridLayout()
        grid.setContentsMargins(16, 0, 16, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._tiles: dict[str, RewardTile] = {}
        for i, (key, label) in enumerate(reward_set.items):
            tile = RewardTile(label, os.path.join(reward_set.rewards_dir, f"{key}.png"))
            grid.addWidget(tile, i // self._COLS, i % self._COLS)
            self._tiles[key] = tile
        for c in range(self._COLS):
            grid.setColumnStretch(c, 1)
        lay.addLayout(grid)
        controller.rewards_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        snapshot = self._controller.get_status_snapshot()
        runs = snapshot.reward_runs
        self._status.setText(
            f"{runs} run{'s' if runs != 1 else ''} read this session" if runs else "Waiting for the first clear"
        )
        for key, tile in self._tiles.items():
            tile.set_counts(snapshot.session_rewards.get(key, 0), snapshot.last_rewards.get(key))


class RewardsPage(QWidget):
    def __init__(self, controllers: dict, chapter_of: dict, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_PageHeader("Rewards summary",
                                  "What your Farmers collected this session.", height=80))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(28, 20, 28, 32)
        body_lay.setSpacing(18)
        for name, reward_set in REWARD_SETS.items():
            controller = controllers.get(name)
            if controller is None:
                continue
            color = chapter_of[name]["color"] if name in chapter_of else C["accent"]
            body_lay.addWidget(RewardSection(reward_set, controller, color))
        body_lay.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)


class RecentCard(_Clickable):
    def __init__(self, farmer, chapter, controller, recent: RecentStore, parent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.controller = controller
        self._recent = recent
        self.setObjectName("recentCard")
        self.setFixedWidth(224)
        self.setStyleSheet(
            f"QFrame#recentCard {{ background: {C['tile_bg']}; border: 1px solid {C['border']}; border-radius: 8px; }}"
            f"QFrame#recentCard:hover {{ border-color: {C['text']}; background: {C['tile_hover']}; }}"
            f"QFrame#recentCard:focus {{ border: 2px solid {C['accent']}; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_art_label(farmer, 222, 125, top_only=True), 0, Qt.AlignHCenter)
        ink = QFrame()
        ink.setFixedHeight(3)
        ink.setStyleSheet(f"background: {chapter['color']}; border: none; border-radius: 0;")
        lay.addWidget(ink)
        body = QVBoxLayout()
        body.setContentsMargins(12, 10, 12, 12)
        body.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(6)
        name = QLabel(farmer["name"])
        name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {C['text']}; background: transparent;")
        top.addWidget(name, 1)
        self.badge = _state_badge()
        top.addWidget(self.badge)
        body.addLayout(top)
        lay.addLayout(body)
        self.refresh()

    def refresh(self, *_args):
        state = _controller_state(self.farmer, self.controller)
        _set_badge(self.badge, state)


class ChapterIndexRow(_Clickable):
    def __init__(self, chapter, parent=None):
        super().__init__(parent)
        self.setObjectName("chapterIndexRow")
        self.setStyleSheet(
            f"QFrame#chapterIndexRow {{ background: transparent; border: none; border-bottom: 1px solid {C['border']}; }}"
            f"QFrame#chapterIndexRow:hover {{ background: {C['tile_hover']}; }}"
            f"QFrame#chapterIndexRow:focus {{ background: {C['tile_hover']}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 7, 8, 7)
        lay.setSpacing(16)
        tab = QLabel()
        tab.setFixedSize(64, 70)
        tab.setAlignment(Qt.AlignCenter)
        tab.setPixmap(svg_icon(chapter.get("icon", "grid"), _on_ink(chapter["color"]), 26).pixmap(26, 26))
        tab.setFixedSize(56, 56)
        tab.setStyleSheet(f"background: {chapter['color']}; border: none; border-radius: 10px;")
        lay.addWidget(tab)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addStretch(1)
        title = QLabel(chapter["title"])
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C['text']}; background: transparent;")
        col.addWidget(title)
        col.addWidget(_muted(chapter["blurb"]))
        col.addStretch(1)
        lay.addLayout(col, 1)
        count = len(chapter["members"])
        count_lbl = QLabel(f"{count} Farmer{'s' if count != 1 else ''}")
        count_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 12px; font-weight: 700; background: transparent;")
        chevron = QLabel()
        chevron.setPixmap(svg_icon("chevron", C["dark"], 16).pixmap(16, 16))
        chevron.setStyleSheet("background: transparent;")
        lay.addWidget(chevron)


class HomePage(QWidget):
    farmer_selected = pyqtSignal(str)
    chapter_selected = pyqtSignal(str)

    def __init__(self, chapters, farmers_by_name, controllers, recent: RecentStore, parent=None):
        super().__init__(parent)
        self._chapters = chapters
        self._chapter_of = {f["name"]: ch for ch in chapters for f in ch["members"]}
        self._farmers = farmers_by_name
        self._controllers = controllers
        self._recent = recent
        self._cards: list[RecentCard] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._header = _PageHeader("Home", "Pick up where you left off, or choose what to farm.", height=80)
        lay.addWidget(self._header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        self._body = QVBoxLayout(body)
        self._body.setContentsMargins(28, 24, 28, 32)
        self._body.setSpacing(0)

        self._running_slot = QVBoxLayout()
        self._running_slot.setSpacing(0)
        self._body.addLayout(self._running_slot)

        self._recent_title = _section_title("Recent")
        self._body.addWidget(self._recent_title)
        self._recent_hint = _muted("")
        self._body.addSpacing(4)
        self._body.addWidget(self._recent_hint)
        self._body.addSpacing(12)
        self._recent_row = QHBoxLayout()
        self._recent_row.setSpacing(14)
        self._body.addLayout(self._recent_row)
        self._body.addSpacing(32)

        self._body.addWidget(_section_title("Farming"))
        self._body.addSpacing(10)
        for ch in chapters:
            row = ChapterIndexRow(ch)
            row.clicked.connect(lambda cid=ch["id"]: self.chapter_selected.emit(cid))
            self._body.addWidget(row)
        self._body.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)

        for controller in controllers.values():
            controller.running_changed.connect(self._on_state_changed)
            controller.paused_changed.connect(self._on_state_changed)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._refresh_status)
        self._tick.start(1000)
        self.rebuild()

    def _running(self):
        return [name for name, c in self._controllers.items() if c.is_running]

    def _on_state_changed(self, *_args):
        self.rebuild()

    def rebuild(self):
        while self._running_slot.count():
            item = self._running_slot.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        running = self._running()
        for name in running[:2]:
            self._running_slot.addWidget(self._now_running_plate(name))
            self._running_slot.addSpacing(16)
        if running:
            self._running_slot.addSpacing(16)

        while self._recent_row.count():
            item = self._recent_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._cards = []
        names = [n for n in self._recent.recent if n in self._farmers]
        if names:
            self._recent_title.setText("Recent")
            self._recent_hint.setText("The Farmers you opened last.")
        else:
            names = [n for n in _STARTER_FARMERS if n in self._farmers]
            self._recent_title.setText("Good first Farmers")
            self._recent_hint.setText("New here? These two are the simplest to set up. Your recent Farmers will show here.")
        for name in names:
            card = RecentCard(self._farmers[name], self._chapter_of[name], self._controllers[name], self._recent)
            card.clicked.connect(lambda n=name: self.farmer_selected.emit(n))
            self._cards.append(card)
            self._recent_row.addWidget(card)
        self._recent_row.addStretch(1)
        self._refresh_status()

    def _now_running_plate(self, name):
        farmer = self._farmers[name]
        chapter = self._chapter_of[name]
        controller = self._controllers[name]
        plate = _Clickable()
        plate.setObjectName("runPlate")
        plate.setStyleSheet(
            f"QFrame#runPlate {{ background: {C['tile_bg']}; border: 2px solid {C['running']}; border-radius: 8px; }}"
            f"QFrame#runPlate:focus {{ border-color: {C['accent']}; }}"
            f"QFrame#runPlate:hover {{ background: {C['tile_hover']}; }}"
        )
        plate.clicked.connect(lambda n=name: self.farmer_selected.emit(n))
        lay = QHBoxLayout(plate)
        lay.setContentsMargins(8, 8, 18, 8)
        lay.setSpacing(20)
        lay.addWidget(_art_label(farmer, 208, 117))
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addStretch(1)
        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(_page_title(name, 20))
        badge = _state_badge()
        _set_badge(badge, _controller_state(farmer, controller))
        top.addWidget(badge, 0, Qt.AlignVCenter)
        top.addStretch(1)
        col.addLayout(top)
        stats = QLabel()
        stats.setObjectName("runStats")
        stats.setProperty("farmer", name)
        stats.setProperty("chapter", chapter["title"])
        stats.setStyleSheet(f"color: {C['dim']}; font-size: 13px; font-weight: 700; background: transparent;")
        col.addWidget(stats)
        col.addStretch(1)
        lay.addLayout(col, 1)
        open_btn = QPushButton("Open live output")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda _=False, n=name: self.farmer_selected.emit(n))
        lay.addWidget(open_btn)
        stop_btn = QPushButton("STOP")
        stop_btn.setStyleSheet(BTN_STOP)
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.clicked.connect(controller.stop)
        lay.addWidget(stop_btn)
        return plate

    def _refresh_status(self):
        for stats in self.findChildren(QLabel, "runStats"):
            name = stats.property("farmer")
            controller = self._controllers.get(name)
            if controller is None:
                continue
            snap = controller.get_status_snapshot()
            if snap.session_start_time is None:
                uptime = "00:00:00"
            else:
                elapsed = int(time.monotonic() - snap.session_start_time)
                h, rem = divmod(elapsed, 3600)
                m, s = divmod(rem, 60)
                uptime = f"{h:02d}:{m:02d}:{s:02d}"
            target = f" of {snap.session_max_clears}" if snap.session_max_clears else ""
            stats.setText(
                f"{uptime} running  ·  {snap.session_clears}{target} clears  ·  {snap.session_losses} losses"
                f"  ·  {stats.property('chapter')}"
            )

    def refresh_cards(self):
        for card in self._cards:
            card.refresh()


class FarmerPage(QWidget):
    def __init__(self, farmer, chapter, controller, back_callback, recent: RecentStore, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.farmer = farmer
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        header = _PageHeader(farmer["name"], back_text=chapter["title"],
                             back_callback=back_callback, height=80)
        self.header = header
        self.badge = _state_badge(large=True)
        header.right.addWidget(self.badge, 0, Qt.AlignVCenter)
        header.right.addSpacing(18)
        self.favorite_btn = FavoriteButton(farmer["name"], recent, with_text=True)
        header.right.addWidget(self.favorite_btn, 0, Qt.AlignVCenter)
        lay.addWidget(header)
        self.farmer_tab = FarmerTab(farmer, controller, accent=chapter["color"])
        lay.addWidget(self.farmer_tab, 1)
        controller.running_changed.connect(self._refresh_badge)
        controller.paused_changed.connect(self._refresh_badge)
        self._refresh_badge()

    def _refresh_badge(self, *_args):
        _set_badge(self.badge, _controller_state(self.farmer, self.controller))


# Main Window


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoFarmers - 7DS Grand Cross")
        self._center_on_screen(1240, 760)
        self.setMinimumSize(1160, 640)
        _icon_path = os.path.join(os.path.dirname(__file__), "..", "gui_images", "main.ico")
        self.setWindowIcon(QIcon(_icon_path))

        self._farmer_by_name = {f["name"]: f for f in FARMERS}
        self._chapters = build_chapters(FARMERS)
        self._chapter_by_id = {ch["id"]: ch for ch in self._chapters}
        self._chapter_of = {f["name"]: ch for ch in self._chapters for f in ch["members"]}
        self._recent = RecentStore()
        self._farmer_pages: dict = {}
        self._chapter_pages: dict = {}
        self._rewards_page: "RewardsPage | None" = None

        self._settings_tab: SettingsTab | None = None
        self._about_tab: AboutTab | None = None
        self._devtest_tab: DevTestTab | None = None
        self._devtest_wrapper: QWidget | None = None
        self._about_tabs = []
        self._devtest_controller = DevTestController(self._can_start_devtest, parent=self)
        self._devtest_controller.busy_changed.connect(self._on_devtest_busy_changed)
        self._settings_wrapper: QWidget | None = None
        self._about_wrapper: QWidget | None = None
        self._repo_root = os.path.dirname(os.path.dirname(__file__))
        self._update_check_process: QProcess | None = None
        self._update_check_output = bytearray()
        self._update_check_timed_out = False
        self._manual_update_running = False
        self._update_available_popup_shown = False
        self._update_check_timeout_timer = QTimer(self)
        self._update_check_timeout_timer.setSingleShot(True)
        self._update_check_timeout_timer.timeout.connect(self._on_update_check_timeout)
        self._saved_game_version = get_saved_game_version()

        self._controllers = {
            farmer["name"]: FarmerController(
                farmer,
                password_supplier=lambda: self.settings_tab.password_edit.text(),
                parent=self,
            )
            for farmer in FARMERS
        }
        for name, controller in self._controllers.items():
            self._devtest_controller.busy_changed.connect(controller.set_devtest_busy)
            controller.running_changed.connect(self._refresh_devtest_controls)
            controller.paused_changed.connect(self._refresh_devtest_controls)
            controller.running_changed.connect(self._refresh_game_version_enabled)
            controller.running_changed.connect(lambda running, pid, n=name: self._on_farmer_running_changed(n, running))

        self._game_version_combo = VersionSwitch()
        self._game_version_combo.addItem(GameVersion.GLOBAL.display_name, GameVersion.GLOBAL.value)
        self._game_version_combo.addItem(GameVersion.JAPAN.display_name, GameVersion.JAPAN.value)
        self._game_version_combo.setToolTip("Choose which game client the next farmer will recognize.")
        saved_index = self._game_version_combo.findData(self._saved_game_version.value)
        self._game_version_combo.setCurrentIndex(max(0, saved_index))
        self._game_version_combo.currentIndexChanged.connect(self._on_game_version_changed)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.rail = IndexRail(self._chapters, self._game_version_combo, favorites_count=len(self._recent.favorites))
        self._recent.favorites_changed.connect(lambda: self.rail.set_favorites_count(len(self._recent.favorites)))
        self.rail.navigate.connect(self._on_navigate)
        self.rail.theme_toggled.connect(self._toggle_theme)
        self.rail.halloween_toggled.connect(self._toggle_halloween)
        self._theme_btn = self.rail.theme_btn
        root.addWidget(self.rail)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"QStackedWidget {{ background: {C['bg']}; }}")
        self.stack.setFocusPolicy(Qt.ClickFocus)
        root.addWidget(self.stack, 1)

        self.home_page = HomePage(self._chapters, self._farmer_by_name, self._controllers, self._recent)
        self.home_page.farmer_selected.connect(self._on_farmer_selected)
        self.home_page.chapter_selected.connect(self._show_chapter)
        self.stack.addWidget(self.home_page)

        self.favorites_page = FavoritesPage(self._farmer_by_name, self._controllers, self._recent)
        self.favorites_page.farmer_selected.connect(lambda n: self._on_farmer_selected(n, from_favorites=True))
        self.stack.addWidget(self.favorites_page)

        self.setCentralWidget(central)
        self._halloween_overlay = HalloweenOverlay(central) if _HALLOWEEN else None
        self._show_home()
        QTimer.singleShot(1000, self._check_for_update_available)


    def _center_on_screen(self, width: int, height: int):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        width, height = min(width, area.width()), min(height, area.height())
        self.setGeometry(
            area.x() + (area.width() - width) // 2, area.y() + (area.height() - height) // 2, width, height
        )

    def _set_location(self, rail_key: str, chapter_id: str | None):
        focused = QApplication.focusWidget()
        if focused is None or focused is self or self.rail.isAncestorOf(focused):
            self.stack.setFocus()
        self.rail.set_active(rail_key)

    def _on_navigate(self, key: str):
        if key == "home":
            self._show_home()
        elif key == "favorites":
            self._show_favorites()
        elif key == "rewards":
            self._show_rewards()

        elif key in ("settings", "devtest", "about"):
            self._show_page(key)
        else:
            self._show_chapter(key)

    def _show_home(self):
        self.home_page.rebuild()
        self.stack.setCurrentWidget(self.home_page)
        self._set_location("home", None)

    def _show_rewards(self):
        if self._rewards_page is None:
            self._rewards_page = RewardsPage(self._controllers, self._chapter_of)
            self.stack.addWidget(self._rewards_page)
        self.stack.setCurrentWidget(self._rewards_page)
        self._set_location("rewards", None)

    def _show_favorites(self):
        self.favorites_page.refresh()
        self.stack.setCurrentWidget(self.favorites_page)
        self._set_location("favorites", None)

    def _show_chapter(self, chapter_id: str):
        chapter = self._chapter_by_id.get(chapter_id)
        if chapter is None:
            return
        page = self._chapter_pages.get(chapter_id)
        if page is None:
            page = ChapterPage(chapter, self._controllers, self._recent)
            page.farmer_selected.connect(self._on_farmer_selected)
            self.stack.addWidget(page)
            self._chapter_pages[chapter_id] = page
        else:
            page.refresh()
        self.stack.setCurrentWidget(page)
        self._set_location(chapter_id, chapter_id)

    def _on_farmer_selected(self, name: str, from_favorites: bool = False):
        view = self._ensure_farmer_page(name)
        chapter = self._chapter_of[name]
        if from_favorites:
            view.header.set_back("Favorites", self._show_favorites)
        else:
            view.header.set_back(chapter["title"], lambda cid=chapter["id"]: self._show_chapter(cid))
        self._recent.touch(name)
        self.stack.setCurrentWidget(view)
        rail_key = "favorites" if from_favorites else chapter["id"]
        self._set_location(rail_key, chapter["id"])

    def _ensure_farmer_page(self, name: str) -> "FarmerPage":
        if name in self._farmer_pages:
            return self._farmer_pages[name]
        chapter = self._chapter_of[name]
        page = FarmerPage(
            self._farmer_by_name[name],
            chapter,
            self._controllers[name],
            back_callback=lambda cid=chapter["id"]: self._show_chapter(cid),
            recent=self._recent,
        )
        self.stack.addWidget(page)
        self._farmer_pages[name] = page
        return page

    def _on_farmer_running_changed(self, name: str, running: bool):
        controller = self._controllers[name]
        if not running:
            snap = controller.get_status_snapshot()
            self._recent.record_run(name, snap.session_clears, getattr(controller, "ended_on_its_own", False))
        running_chapters = {
            self._chapter_of[n]["id"] for n, c in self._controllers.items() if c.is_running and n in self._chapter_of
        }
        self.rail.set_running_chapters(running_chapters)
        self.home_page.refresh_cards()
        for page in self._chapter_pages.values():
            page.refresh()
        self.favorites_page.refresh()


    def _selected_game_version(self) -> GameVersion:
        return normalize_game_version(self._game_version_combo.currentData())

    def _on_game_version_changed(self, _index: int) -> None:
        selected = self._selected_game_version()
        if selected is self._saved_game_version:
            return

        previous = self._saved_game_version
        try:
            save_config_updates({"game_version": selected.value})
            config.reload()
            self._saved_game_version = selected
        except Exception as exc:
            self._game_version_combo.blockSignals(True)
            self._game_version_combo.setCurrentIndex(self._game_version_combo.findData(previous.value))
            self._game_version_combo.blockSignals(False)
            QMessageBox.critical(
                self,
                "Game Version Save Failed",
                f"Could not save the game version. The selection was restored.\n\n{exc}",
            )

    def _refresh_game_version_enabled(self, *_args) -> None:
        enabled = not self._devtest_controller.is_busy and not any(
            controller.process is not None for controller in self._controllers.values()
        )
        focused = QApplication.focusWidget()
        if not enabled and focused is not None and self._game_version_combo.isAncestorOf(focused):
            self.stack.setFocus()
        self._game_version_combo.setEnabled(enabled)
        if self._devtest_controller.is_busy:
            self._game_version_combo.setToolTip("Finish DevTest before changing the game version.")
        elif enabled:
            self._game_version_combo.setToolTip("Choose which game client the next farmer will recognize.")
        else:
            self._game_version_combo.setToolTip("Stop all running farmers before changing the game version.")

    @property
    def settings_tab(self) -> "SettingsTab":
        if self._settings_tab is None:
            self._settings_tab = SettingsTab()
        return self._settings_tab

    @property
    def about_tab(self) -> "AboutTab":
        if self._about_tab is None:
            self._about_tab = self._make_about_tab()
        return self._about_tab

    def _make_about_tab(self) -> "AboutTab":
        about_tab = AboutTab(
            restart_safe_supplier=lambda: not self._any_farmer_running() and not self._devtest_controller.is_busy,
            update_allowed_supplier=lambda: not self._devtest_controller.is_busy,
        )
        about_tab.update_started.connect(self._on_manual_update_started)
        about_tab.update_finished.connect(self._on_manual_update_finished)
        about_tab.update_btn.setEnabled(not self._devtest_controller.is_busy)
        self._about_tabs.append(about_tab)
        return about_tab

    @property
    def devtest_tab(self) -> "DevTestTab":
        if self._devtest_tab is None:
            self._devtest_tab = DevTestTab(self._devtest_controller)
        return self._devtest_tab

    @property
    def devtest_wrapper(self) -> QWidget:
        if self._devtest_wrapper is None:
            self._devtest_wrapper = self._wrap_with_back_bar(self.devtest_tab, "DevTest")
            self.stack.addWidget(self._devtest_wrapper)
        return self._devtest_wrapper

    def _can_start_devtest(self):
        return not self._manual_update_running and all(
            controller.process is None or (controller.is_running and controller.is_paused)
            for controller in self._controllers.values()
        )

    def _refresh_devtest_controls(self, *_args):
        if self._devtest_tab is not None:
            self._devtest_tab.refresh_controls()

    def _on_devtest_busy_changed(self, busy):
        self._refresh_game_version_enabled()
        self._theme_btn.setEnabled(not busy)
        for about_tab in self._about_tabs:
            about_tab.update_btn.setEnabled(not busy and not about_tab.updating)
        self._refresh_devtest_controls()

    @property
    def settings_wrapper(self) -> QWidget:
        if self._settings_wrapper is None:
            self._settings_wrapper = self._wrap_with_back_bar(self.settings_tab, "Settings")
            self.stack.addWidget(self._settings_wrapper)
        return self._settings_wrapper

    @property
    def about_wrapper(self) -> QWidget:
        if self._about_wrapper is None:
            self._about_wrapper = self._wrap_with_back_bar(self.about_tab, "About")
            self.stack.addWidget(self._about_wrapper)
        return self._about_wrapper

    def _wrap_with_back_bar(self, page_widget: QWidget, title: str = "") -> QWidget:
        wrapper = QWidget()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_PageHeader(title, back_text="Home", back_callback=self._show_home, height=80))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }}")
        scroll.setWidget(page_widget)
        lay.addWidget(scroll, 1)

        return wrapper

    def _show_page(self, page_id: str):
        if page_id == "about":
            self.stack.setCurrentWidget(self.about_wrapper)
        elif page_id == "settings":
            self.stack.setCurrentWidget(self.settings_wrapper)
        elif page_id == "devtest":
            self.stack.setCurrentWidget(self.devtest_wrapper)
        else:
            self._show_home()
            return
        self._set_location(page_id, None)

    def _clear_update_available_notification(self) -> None:
        self._update_available_popup_shown = False

    def _show_update_available_popup(self) -> None:
        if self._update_available_popup_shown:
            return
        self._update_available_popup_shown = True
        QMessageBox.information(self, "Update available", "Update available!")

    def _on_manual_update_started(self) -> None:
        self._manual_update_running = True
        self._refresh_devtest_controls()
        self._clear_update_available_notification()

    def _on_manual_update_finished(self) -> None:
        self._manual_update_running = False
        self._refresh_devtest_controls()
        self._clear_update_available_notification()
        self._check_for_update_available()

    def _check_for_update_available(self) -> None:
        """Quietly check whether the configured upstream branch is ahead."""
        if self._manual_update_running or self._update_check_process is not None:
            return
        self._run_update_check_command("git", ["fetch", "--quiet"], self._after_update_fetch)

    def _after_update_fetch(self, exit_code: int, output: str) -> None:
        del output
        if self._manual_update_running:
            return
        if exit_code != 0:
            self._clear_update_available_notification()
            return
        self._run_update_check_command("git", ["rev-list", "--count", "HEAD..@{u}"], self._after_update_count)

    def _after_update_count(self, exit_code: int, output: str) -> None:
        if self._manual_update_running:
            return
        if exit_code != 0:
            self._clear_update_available_notification()
            return
        try:
            commits_behind_upstream = int(output.strip())
        except ValueError:
            self._clear_update_available_notification()
            return
        if commits_behind_upstream > 0:
            self._show_update_available_popup()
        else:
            self._clear_update_available_notification()

    def _run_update_check_command(self, program: str, args: list[str], on_finished) -> None:
        if self._update_check_process is not None:
            return

        self._update_check_output = bytearray()
        self._update_check_timed_out = False
        self._update_check_process = QProcess(self)
        self._update_check_process.setWorkingDirectory(self._repo_root)
        self._update_check_process.setProcessChannelMode(QProcess.MergedChannels)
        self._update_check_process.readyReadStandardOutput.connect(self._on_update_check_output)
        self._update_check_process.finished.connect(
            lambda exit_code, exit_status: self._on_update_check_finished(exit_code, on_finished)
        )
        self._update_check_process.start(program, args)

        if not self._update_check_process.waitForStarted(3000):
            self._update_check_process = None
            self._clear_update_available_notification()
            return

        self._update_check_timeout_timer.start(15000)

    def _on_update_check_output(self) -> None:
        if self._update_check_process is not None:
            self._update_check_output.extend(bytes(self._update_check_process.readAllStandardOutput()))

    def _on_update_check_finished(self, exit_code: int, on_finished) -> None:
        if self._update_check_process is not None:
            try:
                self._update_check_output.extend(bytes(self._update_check_process.readAllStandardOutput()))
            except RuntimeError:
                self._update_check_process = None
                return
        output = self._update_check_output.decode(errors="replace")
        self._update_check_process = None
        self._update_check_output = bytearray()
        self._update_check_timeout_timer.stop()

        if self._update_check_timed_out:
            self._update_check_timed_out = False
            return

        on_finished(exit_code, output)

    def _on_update_check_timeout(self) -> None:
        if self._update_check_process is None:
            return
        self._update_check_timed_out = True
        self._update_check_process.kill()
        self._clear_update_available_notification()

    def _stop_update_check(self) -> None:
        process = self._update_check_process
        if process is None:
            return
        self._update_check_process = None
        self._update_check_timeout_timer.stop()
        try:
            process.readyReadStandardOutput.disconnect()
            process.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        if process.state() != QProcess.NotRunning:
            process.kill()
            process.waitForFinished(2000)

    def _toggle_theme(self):
        self._change_theme("light" if _ACTIVE_THEME != "light" else "dark")

    def _toggle_halloween(self):
        self._change_theme("dark" if _HALLOWEEN else "halloween")

    def _change_theme(self, theme: str):
        if self._devtest_controller.is_busy:
            QMessageBox.information(self, "DevTest is open", "Finish or stop DevTest before changing the theme.")
            return
        if self._any_farmer_running():
            QMessageBox.information(
                self,
                "Theme Change Blocked",
                "Stop all running farmers before changing the theme.",
            )
            return
        _save_theme(theme)
        if not _restart_application():
            QMessageBox.critical(
                self,
                "Theme Change Failed",
                "The theme was saved, but the GUI could not be reopened automatically.",
            )
            return
        self.close()
        QApplication.instance().quit()

    def _any_farmer_running(self) -> bool:
        return any(controller.is_running for controller in self._controllers.values())

    def closeEvent(self, event):
        if self._devtest_tab is not None:
            self._devtest_tab._remember_folder()
        self._devtest_controller.shutdown()
        self._stop_update_check()
        super().closeEvent(event)


def _apply_dark_title_bar(hwnd: int, dark: bool) -> None:
    """Tell Windows to use a dark (or light) title bar for the given window handle."""
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    value = ctypes.c_int(1 if dark else 0)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except (AttributeError, OSError):
        pass  # Not supported on older Windows versions


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont(UI_FONT_FAMILY, 10))
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    app.aboutToQuit.connect(window._devtest_controller.shutdown)
    window.show()
    _apply_dark_title_bar(int(window.winId()), _ACTIVE_THEME != "light")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
