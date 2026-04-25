# =============================================================================
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                           🆓 FREE SOFTWARE 🆓                           ║
# ║                                                                          ║
# ║  This program is FREE and open source. You should NOT have paid         ║
# ║  anything for it. If you paid money, you were scammed!                  ║
# ║                                                                          ║
# ║  This software is provided "as is" without warranty of any kind.        ║
# ║  Use at your own risk.                                                   ║
# ║                                                                          ║
# ║  License: MIT License                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# =============================================================================

# AutoFarmers GUI (PyQt5)
# Dropdown + stacked pages for all farmer scripts, with argument fields, terminal output, and process control.

import ctypes
import ctypes.wintypes
import datetime
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass

from PyQt5.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
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

from utilities.app_config import (
    APP_CONFIG_DEFAULTS,
    config,
    get_pause_flag_path,
    load_full_config_dict,
    save_config_updates,
    test_ntfy_connection,
)

# Free software message to display in GUI
FREE_SOFTWARE_MESSAGE = """=====================================================================
                           🆓 FREE SOFTWARE 🆓

  This program is FREE and open source. You should NOT have paid
  anything for it. If you paid money, you were scammed!

  This software is provided "as is" without warranty of any kind.
  Use at your own risk.

  License: MIT License
=====================================================================

"""

# Tokyo Night (dark) palette
C_DARK = {
    "bg": "#0f0f17",
    "panel": "#171724",
    "panel2": "#1e1e2e",
    "panel3": "#1a1a2e",
    "border": "#252535",
    "border2": "#2e2e45",
    "accent": "#8b5cf6",
    "accent_light": "#c4b5fd",
    "running": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "blue": "#3b82f6",
    "text": "#e2e8f0",
    "dim": "#9ca3af",
    "muted": "#6b7280",
    "dark": "#4b5563",
    "darker": "#374151",
    "term_bg": "#16161e",
    "term_text": "#c0caf5",
    "tile_bg": "#171724",
    "tile_hover": "#1e1e2e",
    "btn_sec_bg": "transparent",
    "btn_sec_text": "#6b7280",
}

# Light palette
C_LIGHT = {
    "bg": "#F4F7FB",
    "panel": "#E9F1FF",
    "panel2": "#eef4ff",
    "panel3": "#e2ecff",
    "border": "#D6E4FF",
    "border2": "#c5d8ff",
    "accent": "#3B82F6",
    "accent_light": "#1d4ed8",
    "running": "#16a34a",
    "warning": "#d97706",
    "error": "#dc2626",
    "blue": "#2563eb",
    "text": "#1A2A44",
    "dim": "#2d4a6e",
    "muted": "#5a7a9f",
    "dark": "#8aaac8",
    "darker": "#dbe8f8",
    "term_bg": "#1e1e2e",
    "term_text": "#c0caf5",
    "tile_bg": "#FFFFFF",
    "tile_hover": "#EEF4FF",
    "btn_sec_bg": "#E5EDFF",
    "btn_sec_text": "#3B82F6",
}

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
C = C_LIGHT if _ACTIVE_THEME == "light" else C_DARK

# Action Button Styles
def _action_btn(base: str, hover: str, pressed: str, color: str = "white") -> str:
    return (
        f"QPushButton {{ background-color: {base}; color: {color};"
        f" font-weight: bold; padding: 7px 4px; border: none; border-radius: 6px; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:pressed {{ background-color: {pressed}; }}"
        f"QPushButton:disabled {{ background-color: {C['panel2']}; color: {C['muted']}; }}"
    )

_START_HOVER   = "#34d399" if _ACTIVE_THEME == "dark" else "#22c55e"
_START_PRESSED = "#059669" if _ACTIVE_THEME == "dark" else "#15803d"

BTN_START  = _action_btn(C["running"], _START_HOVER, _START_PRESSED)
BTN_STOP   = _action_btn(C["error"],   "#f87171",    "#dc2626")
BTN_PAUSE  = _action_btn(C["warning"], "#fbbf24",    "#d97706")
BTN_RESIZE = _action_btn(C["blue"],    "#60a5fa",    "#2563eb")
BTN_CLEAR  = _action_btn(C["darker"],  C["dark"],    C["darker"], C["text"])

_GUI_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gui_images")


def _make_stylesheet() -> str:
    check_icon = os.path.join(_GUI_IMAGES_DIR, "check.svg").replace("\\", "/")
    return f"""
QWidget {{
    background-color: {C['bg']};
    color: {C['text']};
    font-family: Consolas, monospace;
    font-size: 13px;
}}
QScrollArea, QAbstractScrollArea {{
    background-color: {C['bg']};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {C['bg']};
}}
QLineEdit, QSpinBox {{
    background-color: {C['bg']};
    border: 1px solid {C['border2']};
    border-radius: 5px;
    color: {C['dim']};
    padding: 5px 8px;
    font-size: 13px;
    selection-background-color: {C['accent']};
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {C['accent']};
}}
QComboBox {{
    background-color: {C['bg']};
    border: 1px solid {C['border2']};
    border-radius: 5px;
    color: {C['dim']};
    padding: 5px 8px;
    font-size: 13px;
    selection-background-color: {C['accent']};
}}
QComboBox:focus {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{ border: none; background: transparent; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {C['panel2']};
    border: 1px solid {C['border2']};
    color: {C['dim']};
    selection-background-color: {C['accent']};
    outline: none;
}}
QCheckBox {{
    color: {C['muted']};
    font-size: 13px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 13px; height: 13px;
    border: 1px solid {C['border2']};
    border-radius: 3px;
    background: {C['bg']};
}}
QCheckBox::indicator:checked {{
    background: {C['accent']};
    border-color: {C['accent']};
    image: url({check_icon});
}}
QListWidget {{
    background: {C['bg']};
    border: 1px solid {C['border2']};
    border-radius: 5px;
    color: {C['dim']};
    font-size: 13px;
}}
QListWidget::item:selected {{
    background: {C['accent']};
    color: white;
    border-radius: 3px;
}}
QListWidget::item:hover {{ background: {C['panel2']}; }}
QGroupBox {{
    border: 1px solid {C['border']};
    border-radius: 8px;
    margin-top: 14px;
    font-size: 13px;
    font-weight: bold;
    color: {C['text']};
    padding: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -1px;
    padding: 0 6px;
    color: {C['text']};
    background-color: {C['bg']};
}}
QLabel {{ color: {C['text']}; background: transparent; }}
QPushButton {{
    border: 1px solid {C['border2']};
    border-radius: 5px;
    padding: 6px 12px;
    color: {C['muted']};
    background: transparent;
    font-size: 13px;
}}
QPushButton:hover {{ border-color: {C['accent']}; color: {C['accent_light']}; }}
QPushButton:pressed {{ background: transparent; border-color: {C['accent']}; }}
QPushButton:disabled {{ color: {C['darker']}; border-color: {C['panel2']}; }}
QScrollBar:vertical {{
    background: {C['panel2']};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border2']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0; background: none;
}}
QScrollBar:horizontal {{ height: 0; background: none; }}
QTextEdit {{
    background: {C['term_bg']};
    color: {C['term_text']};
    border: none;
    font-family: Consolas, monospace;
    font-size: 13px;
    selection-background-color: {C['accent']};
}}
"""


APP_STYLESHEET = _make_stylesheet()

# Requirements for whale farmers (displayed in GUI)
REQUIREMENTS = {
    "Demon Farmer": """
<p>If multiple demons are selected, the bot will rotate between them every 2h.</p>
    """,
    "Bird Floor 4": """
<p><strong>Requirements:</strong><br>
• Any team, but best: Thor, G Tyr, Xion, Merlin/Milim Hel</p>
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
• Same team as normal Deer Floor 4 — <em>not</em> the separate Deer Whale comp<br>
• Targets finishing <strong>Phase 1 in 1</strong> player turn<br>
• Tune your gear/CC to support the aggressive opener<br>
• <strong>IMPORTANT</strong>: NO SKULD</p>
    """,
    "Dogs Floor 4": """
<p><strong>Requirements:</strong><br>
• Escalin, Lillia/Cusack/Roxy(recommended), Nasiens, Thonar</p>
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
    "Deer Whale": """
<p><strong>Requirements:</strong><br>
• 16M+ CC • 5th+ Constellation<br>
• UR Atk/Crit gear (14.5%+ atk pieces)<br>
• Team order: Jorm → Loli Merlin → Freyr → Albedo<br>
• All units need relics</p>
    """,
    "Dogs Whale": """
<p><strong>Requirements:</strong><br>
• 14-16M+ CC • 6th Constellation (5th ok)<br>
• UR Atk/Crit gear (14.5%+ top pieces)<br>
• Team: Milim LR, Loli Merlin LR, Thor, Green Hel<br>
• Links: Ludo on Milim, OG Red Sariel on Merlin, Sab on Thor, Mael on Hel<br>
• Artifacts #37 or #29</p>
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
}

# Maps base farmer names to their whale-mode requirement key and image filename.
WHALE_MODE_CONFIG = {
    "Deer Farmer": {"requirements_key": "Deer Whale", "image": "deer_whale.jpg"},
    "Deer Floor 4": {"requirements_key": "Deer Floor 4 Whale", "image": "deer_floor_4.png"},
    "Dogs Farmer": {"requirements_key": "Dogs Whale", "image": "dogs_whale_farmer.jpg"},
    "Snake Farmer": {"requirements_key": "Snake Whale", "image": "snake_whale_farmer.png"},
}

FARMER_IMAGES = {
    "Demon Farmer": "demon_farmer.jpg",
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
    "Reroll Constellation": "reroll_constellation_whale.jpg",
    "SA Coin Dungeon Farmer": "sa_coin_farmer.png",
    "Guild Boss Farmer": "guild_boss_farmer.jpg",
    "Demon King Farmer": "dk_farmer.jpg",
    "Boss Battle Farmer": "boss_battle_farmer.png",
    "Gold Farmer": "gold_farmer.jpg",
}

# Farmer script definitions (argument structure)
FARMERS = [
    {
        "name": "Demon Farmer",
        "script": "DemonFarmer.py",
        "args": [
            {
                "name": "--indura-diff",
                "label": "Indura Difficulty",
                "type": "dropdown",
                "choices": ["extreme", "hell", "chaos"],
                "default": "chaos",
            },
            {
                "name": "--indura-team",
                "label": "Indura Team",
                "type": "dropdown",
                "choices": ["fairies", "humans"],
                "default": "fairies",
            },
            {
                "name": "--demons-to-farm",
                "label": "Demons to Farm",
                "type": "multiselect",
                "choices": ["indura_demon", "og_demon", "bell_demon", "red_demon", "gray_demon", "crimson_demon"],
                "labels":  ["Indura Demon", "OG Demon",  "Bell Demon", "Red Demon",  "Gray Demon",  "Crimson Demon"],
                "default": ["indura_demon"],
            },
            {"name": "--time-to-sleep", "label": "Wait before Accept (s)", "type": "text", "default": "9.3"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Guild Boss Farmer",
        "script": "GuildBossFarmer.py",
        "args": [
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Farmer",
        "script": "BirdFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Floor 4",
        "script": "BirdFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Farmer",
        "script": "DeerFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Deer Floor 4",
        "script": "DeerFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Dogs Farmer",
        "script": "DogsFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Dogs Floor 4",
        "script": "DogsFloor4Farmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--extra-clears", "label": "Extra Clears", "type": "text", "default": "0"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Snake Farmer",
        "script": "SnakeFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
            {"name": "--whale", "label": "Whale mode", "type": "checkbox", "default": False},
        ],
    },
    {
        "name": "Rat Farmer",
        "script": "RatFarmer.py",
        "args": [
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
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
                "choices": ["hard", "extreme", "hell"],
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
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
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
        "name": "Tower Trials",
        "script": "TowerTrialsFarmer.py",
        "args": [],
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
]

_UPTIME_CYCLE_SECS = 12 * 3600  # Session uptime bar resets every 12 hours


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


class FarmerController(QObject):
    running_changed = pyqtSignal(bool, int)
    paused_changed = pyqtSignal(bool)
    output_appended = pyqtSignal(str)
    output_reset = pyqtSignal()
    session_progress_changed = pyqtSignal()
    status_snapshot_changed = pyqtSignal(object)
    arg_values_changed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, farmer_def: dict, password_supplier=None, parent=None):
        super().__init__(parent)
        self.farmer = farmer_def
        self._password_supplier = password_supplier
        self.process = None
        self.output_lines: list[str] = []
        self.paused = False
        self._session_clears = 0
        self._session_pots = 0
        self._session_losses = 0
        self._session_max_clears = None
        self._session_start_time = None
        self._pause_start_time = None
        self._last_clear_time = None
        self._process_exit_expected = False
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
        if self.process is not None:
            return

        for name, value in arg_values.items():
            self.set_arg_value(name, value)

        self.resize_window()

        script_path = os.path.join(os.path.dirname(__file__), self.farmer["script"])
        args = self._build_cli_args()
        display_args = self._build_display_args(args)

        self.process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.process_finished)

        self.output_lines = []
        self.output_reset.emit()

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

        self.process.start(sys.executable, ["-u", script_path] + args)
        self._cleanup_pause_flag()
        self._append_output(
            f"<color=#10b981>Started {self.farmer['name']} with:\n"
            f"{' '.join([sys.executable, '-u', script_path] + display_args)}\n</color>"
        )
        self._output_timer.start(100)
        self.running_changed.emit(True, self.process.processId())
        self.paused_changed.emit(False)
        self._emit_status_snapshot()

    def stop(self):
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
            self._append_output("\nProcess finished.\n")
            self.running_changed.emit(False, 0)
        self._emit_status_snapshot()

    def check_output(self):
        if self.process is None:
            return
        if self.process.bytesAvailable() > 0:
            self.handle_stdout()

    def _build_default_arg_values(self) -> dict[str, object]:
        values = {}
        for arg in self.farmer["args"]:
            default = arg.get("default")
            if arg["type"] == "multiselect":
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
            if arg["type"] == "dropdown":
                if value:
                    args.extend([arg["name"], str(value)])
            elif arg["type"] == "checkbox":
                if value:
                    args.append(arg["name"])
            elif arg["type"] == "multiselect":
                selected = [str(item) for item in (value or []) if str(item)]
                if selected:
                    args.extend([arg["name"]] + selected)
            elif value:
                args.extend([arg["name"], str(value)])
        if self.farmer["script"] in PASSWORD_CLI_SCRIPTS:
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
        if self._session_start_time is not None:
            if "[CLEAR]" in text:
                self._on_clear_detected()
            if "[POT]" in text:
                self._session_pots += 1
                self.session_progress_changed.emit()
            if "[LOSS]" in text:
                self._session_losses += 1
                self.session_progress_changed.emit()

        _HIDDEN_MARKERS = {"[CLEAR]", "[POT]", "[LOSS]"}
        new_lines = [line for line in text.splitlines(True) if line.strip() not in _HIDDEN_MARKERS]
        self.output_lines.extend(new_lines)
        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-1000:]
            self.output_reset.emit()
            return
        if new_lines:
            self.output_appended.emit("".join(new_lines))

    def _on_clear_detected(self):
        self._session_clears += 1
        self._last_clear_time = datetime.datetime.now()
        self.session_progress_changed.emit()
        self._emit_status_snapshot()

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
    def __init__(self, restart_safe_supplier=None, parent=None):
        super().__init__(parent)
        self.update_process = None
        self.updating = False
        self.repo_root = os.path.dirname(os.path.dirname(__file__))
        self.gui_file_path = os.path.abspath(__file__)
        self.requirements_file_path = os.path.join(self.repo_root, "requirements.txt")
        self._restart_safe_supplier = restart_safe_supplier or (lambda: True)
        self._pre_update_gui_hash = None
        self._pre_update_requirements_hash = None
        self._pending_gui_changed = False
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
        title = QLabel("🚀 AutoFarmers — 7DS Grand Cross")
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
        self.status_label.setStyleSheet(f"color: {C['muted']}; font-size: 15px;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)

    def load_hero_image(self, layout):
        """Load and display the hero image"""
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet(f"border: 1px solid {C['border']}; background: {C['panel2']}; border-radius: 8px;")

        # Try to load the GUI image from readme_images
        image_paths = [
            os.path.join(_GUI_IMAGES_DIR, "main_gui.jpg"),
        ]

        image_loaded = False
        for image_path in image_paths:
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale to match the widescreen aspect ratio of main_gui.jpg (16:9)
                    scaled_pixmap = pixmap.scaled(640, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_label.setPixmap(scaled_pixmap)
                    img_label.setFixedSize(scaled_pixmap.size())
                    image_loaded = True
                    break

        if not image_loaded:
            img_label.setText("🖼️ AutoFarmers GUI\n(Image not found)")
            img_label.setFixedSize(640, 360)
            img_label.setStyleSheet(
                f"border: 1px solid {C['border']}; background: {C['panel2']}; color: {C['dark']}; border-radius: 8px; font-size: 14px;"
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
        self.update_btn = QPushButton("🔄 UPDATE")
        self.update_btn.setStyleSheet(
            f"background-color: {C['accent']}; color: white; font-weight: bold; padding: 8px 16px;"
        )
        self.update_btn.clicked.connect(self.on_update_clicked)
        btn_layout.addWidget(self.update_btn)

        # GitHub button
        github_btn = QPushButton("🐙 GitHub")
        github_btn.setStyleSheet(f"background-color: {C['dark']}; color: white; font-weight: bold; padding: 8px 16px;")
        github_btn.clicked.connect(lambda: self.open_url("https://github.com/PhantomPilots/AutoFarming"))
        btn_layout.addWidget(github_btn)

        # Discord button
        discord_btn = QPushButton("💬 Discord")
        discord_btn.setStyleSheet("background-color: #7289DA; color: white; font-weight: bold; padding: 8px 16px;")
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
        desc_label.setText(
            """
<h3>🎮 AutoFarmers for 7DS Grand Cross</h3>
<p>Automate your farming in Seven Deadly Sins: Grand Cross with this collection of specialized bots.</p>
        """
        )
        desc_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        layout.addWidget(desc_label)

        # Available Farmers and Requirements in two columns
        farmers_req_layout = QHBoxLayout()

        # Left column - Available Farmers
        farmers_label = QLabel()
        farmers_label.setWordWrap(True)
        farmers_label.setAlignment(Qt.AlignTop)
        farmers_label.setText(
            """
<p><strong>Available Farmers:</strong><br>
• Demon, Bird, Deer, Snake, Dogs farming<br>
• Final Boss battles and Tower Trials<br>
• Account management and daily quests<br>
• Equipment farming and constellation rerolls</p>
        """
        )
        farmers_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        farmers_req_layout.addWidget(farmers_label)

        # Right column - Requirements
        req_label = QLabel()
        req_label.setWordWrap(True)
        req_label.setAlignment(Qt.AlignTop)
        req_label.setText(
            """
<p><strong>⚙️ Requirements:</strong><br>
• Official 7DS PC Beta Client<br>
• Portrait mode (disable landscape)<br>
• Game set to English<br>
• Disable all game notifications</p>
        """
        )
        req_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4;")
        farmers_req_layout.addWidget(req_label)

        layout.addLayout(farmers_req_layout)

        # Call to action
        cta_label = QLabel()
        cta_label.setWordWrap(True)
        cta_label.setAlignment(Qt.AlignCenter)
        cta_label.setText("<p><em>Pick a farmer tab to configure and start, and join our Discord for help!</em></p>")
        cta_label.setStyleSheet(f"font-size: 13px; color: {C['dim']}; line-height: 1.4; font-style: italic;")
        layout.addWidget(cta_label)

    def on_update_clicked(self):
        """Handle update button click - run git stash then git pull"""
        if self.updating:
            return  # Already updating

        # Start the update process
        self.updating = True
        self.update_btn.setEnabled(False)
        self.status_label.setText("🔄 Running 'git stash'...")

        # Start with git stash
        self.run_process("git", ["stash"], self.after_stash)

    def open_url(self, url: str):
        """Open URL in default browser"""
        try:
            QDesktopServices.openUrl(QUrl(url))
            if "github" in url.lower():
                self.status_label.setText("🐙 Opening GitHub repository...")
            elif "discord" in url.lower():
                self.status_label.setText("💬 Opening Discord invite...")
            else:
                self.status_label.setText(f"🌐 Opening {url}...")

            # Clear status after 2 seconds
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
        except Exception as e:
            self.status_label.setText(f"❌ Failed to open URL: {e}")

    def after_stash(self, exit_code):
        """Handle completion of git stash command"""
        if exit_code != 0:
            self.status_label.setText("❌ git stash failed")
            self._finish_update()
            return

        # Stash successful, now run git pull
        self._pre_update_gui_hash = self._compute_file_hash(self.gui_file_path)
        self._pre_update_requirements_hash = self._compute_file_hash(self.requirements_file_path)
        self.status_label.setText("🔄 Running 'git pull'...")
        self.run_process("git", ["pull"], self.after_pull)

    def after_pull(self, exit_code):
        """Handle completion of git pull command"""
        if exit_code != 0:
            self.status_label.setText("❌ git pull failed")
            self._finish_update()
            return

        self._handle_post_pull_completion()

    def after_requirements_install(self, exit_code):
        """Handle completion of the requirements install step."""
        if exit_code != 0:
            self.status_label.setText(
                "❌ Requirements install failed; please run python -m pip install -r requirements.txt"
            )
            self._finish_update(clear_status=False)
            return

        self._complete_restart_decision()

    def run_process(self, program, args, on_finished):
        """Run an external command in the repo root directory."""
        if self.update_process is not None:
            return  # Already running a command

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
            self.status_label.setText(f"❌ Failed to start {program}")
            self.update_process = None
            self._finish_update()

    def on_git_output(self):
        """Handle git command output (optional - could be used for detailed logging)"""
        if self.update_process is not None:
            # For now, we'll just read and ignore the output
            # In the future, this could be logged to a details view
            self.update_process.readAllStandardOutput()

    def on_git_finished(self, exit_code, callback):
        """Handle git command completion"""
        self.update_process = None
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
            self.status_label.setText("🔄 Installing updated requirements...")
            self.run_process(
                sys.executable,
                ["-m", "pip", "install", "-r", self.requirements_file_path],
                self.after_requirements_install,
            )
            return

        self._complete_restart_decision()

    def _complete_restart_decision(self):
        """Decide whether the update should trigger a GUI restart."""
        if not self._pending_gui_changed:
            self.status_label.setText("✅ Update complete")
            self._finish_update()
            return

        if not self._restart_safe_supplier():
            self.status_label.setText("✅ Update complete - restart required because AutoFarmers.py changed")
            self._finish_update(clear_status=False)
            return

        self.status_label.setText("✅ Update complete - restarting GUI...")
        self._finish_update(clear_status=False)
        if not _restart_application():
            self.status_label.setText("✅ Update complete - GUI restart failed; please reopen manually")
            return
        QApplication.instance().quit()

    def _finish_update(self, clear_status=True):
        """Reset update UI state and optionally clear the status after a delay."""
        self.updating = False
        self.update_btn.setEnabled(True)
        self._pre_update_gui_hash = None
        self._pre_update_requirements_hash = None
        self._pending_gui_changed = False
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
        footnote.setStyleSheet(f"color: {C['dark']}; font-size: 13px;")
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
                    "game_password": stripped_pwd,
                    "minutes_to_wait_before_login": self.login_wait_spin.value(),
                }
            )
            config.reload()
            self.status_label.setText("Saved.")
            self.status_label.setStyleSheet("color: #10b981;")
        except Exception as e:
            self.status_label.setText(f"Save failed: {e}")
            self.status_label.setStyleSheet("color: #ef4444;")

    def on_test_notification(self):
        config.reload()
        ok, msg = test_ntfy_connection()
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #10b981;" if ok else "color: #ef4444;")


class FarmerTab(QWidget):
    _COLOR_TAG_RE = re.compile(r"<color=([^>]+)>(.*?)</color>", re.IGNORECASE | re.DOTALL)
    _LINE_COLOR_RULES = [
        (re.compile(r"error|failed|exception|traceback|critical", re.I), "#ef4444"),
        (re.compile(r"\bwarn(ing)?\b", re.I), "#f59e0b"),
        (re.compile(r"success|complet|finished|victory|cleared|✓|✅", re.I), "#10b981"),
        (re.compile(r"\b(info|start|launch|connect|running)\b", re.I), "#3b82f6"),
        (re.compile(r"^\s*[>=\-#]{3,}"), "#4b5563"),
    ]

    def __init__(self, farmer, controller, parent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.controller = controller
        self._syncing_arg_widgets = False
        self.sa_chest_warning_label = None
        self._default_fmt = QTextCharFormat()
        self._default_fmt.setForeground(QColor("#c0caf5"))
        self.init_ui()
        self.controller.output_reset.connect(self._on_output_reset)
        self.controller.output_appended.connect(self.append_terminal)
        self.controller.running_changed.connect(self._on_running_changed)
        self.controller.paused_changed.connect(self._on_paused_changed)
        self.controller.session_progress_changed.connect(self._refresh_session_progress)
        self.controller.arg_values_changed.connect(self._sync_arg_widgets)
        self.controller.status_snapshot_changed.connect(self._on_status_snapshot_changed)
        self._sync_from_controller()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.addLayout(self._build_left_panel(), 1)
        layout.addLayout(self._build_right_panel(), 2)
        self.setLayout(layout)
        self._append_terminal_centered(FREE_SOFTWARE_MESSAGE)

    def _build_left_panel(self):
        panel = QVBoxLayout()

        # Image
        self.image_size = (400, 250)
        self.image_label = QLabel(f"[Image Placeholder]\n{self.image_size[0]}x{self.image_size[1]}")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            f"border: 1px solid {C['border']}; background: {C['panel2']};" f" color: {C['dark']}; border-radius: 5px;"
        )
        self.image_label.setFixedSize(*self.image_size)
        self.load_farmer_image()
        panel.addWidget(self.image_label, 0, Qt.AlignHCenter)

        # Arguments
        if self.farmer["args"]:
            args_group = QGroupBox("Arguments")
            args_group.setStyleSheet(
                f"QGroupBox {{ margin-top: 21px; border: 1px solid {C['border']}; border-radius: 8px;"
                f" font-size: 14px; font-weight: bold; color: {C['dim']}; padding: 8px; }}"
                f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left;"
                f" padding: 0 6px; left: 12px; }}"
            )
            args_layout = QFormLayout()
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
                    widget.setStyleSheet(
                        f"QFrame {{ border: 1px solid {C['border2']}; border-radius: 5px; background: {C['bg']}; }}"
                    )
                    _vbox = QVBoxLayout(widget)
                    _vbox.setContentsMargins(8, 6, 8, 6)
                    _vbox.setSpacing(4)
                    widget._checkboxes = []
                    _labels = arg.get("labels") or []
                    for idx, choice in enumerate(arg["choices"]):
                        label = _labels[idx] if idx < len(_labels) else choice
                        cb = QCheckBox(label)
                        cb.setProperty("value", choice)
                        cb.setChecked(choice in arg.get("default", []))
                        _vbox.addWidget(cb)
                        widget._checkboxes.append(cb)
                else:
                    widget = QLineEdit()
                    widget.setText(arg["default"])
                self.arg_widgets[arg["name"]] = widget
                args_layout.addRow(arg["label"] + ":", widget)
                self._bind_arg_widget(arg, widget)

                if self.farmer["name"] == "SA Coin Dungeon Farmer" and arg["name"] == "--min-chest-type":
                    widget.currentTextChanged.connect(self.update_sa_chest_warning)
                if arg["name"] == "--whale":
                    widget.stateChanged.connect(self._refresh_whale_mode)
            args_group.setLayout(args_layout)
            panel.addWidget(args_group)

            if self.farmer["name"] == "SA Coin Dungeon Farmer":
                self.sa_chest_warning_label = QLabel()
                self.sa_chest_warning_label.setWordWrap(True)
                self.sa_chest_warning_label.setStyleSheet(
                    f"font-size: 13px; color: {C['error']}; border: 1px solid {C['error']};"
                    f" border-radius: 5px; padding: 6px; background: rgba(239,68,68,0.1);"
                )
                self.sa_chest_warning_label.hide()
                panel.addWidget(self.sa_chest_warning_label)
                self.update_sa_chest_warning(self.arg_widgets["--min-chest-type"].currentText())
        else:
            self.arg_widgets = {}

        # Requirements text (dynamically updated for whale-capable farmers)
        self.req_label = None
        if self.farmer["name"] in REQUIREMENTS or self.farmer["name"] in WHALE_MODE_CONFIG:
            self.req_label = QLabel()
            self.req_label.setWordWrap(True)
            self.req_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.req_label.setText(REQUIREMENTS.get(self.farmer["name"], ""))
            self.req_label.setStyleSheet(
                f"font-size: 13px; color: {C['dim']}; line-height: 1.4; background: {C['panel3']};"
                f" border-left: 3px solid {C['accent']}; padding: 9px 12px; border-radius: 0 5px 5px 0;"
            )
            req_scroll = QScrollArea()
            req_scroll.setWidget(self.req_label)
            req_scroll.setWidgetResizable(True)
            req_scroll.setMaximumHeight(180)
            req_scroll.setStyleSheet(
                f"QScrollArea {{ background: {C['panel3']}; border-left: 3px solid {C['accent']};"
                f" border-radius: 0 5px 5px 0; border-top: none; border-right: none; border-bottom: none; }}"
            )
            panel.addWidget(req_scroll)
            panel.addSpacing(4)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START")
        self.start_btn.setStyleSheet(BTN_START)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet(BTN_STOP)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setStyleSheet(BTN_PAUSE)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.resize_btn = QPushButton("RESIZE")
        self.resize_btn.setStyleSheet(BTN_RESIZE)
        self.resize_btn.clicked.connect(self._on_resize_clicked)
        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setStyleSheet(BTN_CLEAR)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        for btn in (self.start_btn, self.stop_btn, self.pause_btn, self.resize_btn, self.clear_btn):
            btn_layout.addWidget(btn)

        panel.addLayout(btn_layout)
        panel.addStretch(1)
        return panel

    def _build_right_panel(self):
        panel = QVBoxLayout()

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        _term_font = QFont("Consolas")
        _term_font.setPixelSize(15)
        self.terminal.document().setDefaultFont(_term_font)
        self._default_fmt.setFont(_term_font)
        self.terminal.setStyleSheet(
            f"background: {C['term_bg']}; color: {C['term_text']}; border: none; border-radius: 5px;"
            " padding: 10px 14px; font-family: Consolas, monospace;"
            " font-size: 15px; line-height: 1.6;"
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
        self._sp_pots_lbl, self._sp_pots_bar = make_bar_metric(left_lay, "Stamina Pots", "0", bar_color="#f59e0b")
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
            "color: #10b981; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        self._sp_loss_lbl = make_row(right_lay, "Loss", "0")
        self._sp_loss_lbl.setStyleSheet(
            "color: #ef4444; font-size: 13px; font-weight: 600; background: transparent; border: none;"
        )
        self._sp_total_lbl = make_row(right_lay, "Total Runs", "0")
        self._sp_winrate_lbl, self._sp_winrate_bar = make_bar_metric(
            right_lay, "Win Rate", "0%", bar_max=100, bar_color="#10b981"
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
                "Warning: Selecting silver minimum is expected to use many stamina pots for a full run.\n"
                "5% silver + 2% gold: ~15 retries or ~7 pots per chest!\nExpect over 150 pots for a full run!"
            )
            self.sa_chest_warning_label.show()
            return

        if normalized_type == "gold":
            self.sa_chest_warning_label.setText(
                "Warning: Selecting gold minimum is extremely costly.\n"
                "2% gold: ~50 retries or ~23 pots per chest!\nExpect over 600 pots for a full run!"
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
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.pause_btn.setEnabled(running)
        if not running:
            self.pause_btn.setText("PAUSE")

    def _on_paused_changed(self, paused: bool):
        self.pause_btn.setText("RESUME" if paused else "PAUSE")

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
            self._append_terminal_centered(FREE_SOFTWARE_MESSAGE)
        self._on_running_changed(self.controller.is_running, self.controller.process_id)
        self._on_paused_changed(self.controller.is_paused)
        self._refresh_session_progress()

    def load_farmer_image(self, image_filename=None):
        """Load and display a farmer image into self.image_label."""
        if image_filename is None:
            image_filename = FARMER_IMAGES.get(self.farmer["name"])
        if image_filename is None:
            return

        image_path = os.path.join(_GUI_IMAGES_DIR, image_filename)
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(*self.image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("border: 1px solid #252535; border-radius: 5px;")
            else:
                self.image_label.setText(f"Failed to load image:\n{image_filename}")
        else:
            self.image_label.setText(f"Image not found:\n{image_filename}")

    def _refresh_whale_mode(self):
        """Update image and requirements when whale-mode checkbox changes."""
        whale_config = WHALE_MODE_CONFIG.get(self.farmer["name"])
        if not whale_config:
            return

        whale_enabled = "--whale" in self.arg_widgets and self.arg_widgets["--whale"].isChecked()

        if self.req_label is not None:
            key = whale_config["requirements_key"] if whale_enabled else self.farmer["name"]
            self.req_label.setText(REQUIREMENTS.get(key, ""))
            self.req_label.adjustSize()

        image = whale_config["image"] if whale_enabled else FARMER_IMAGES.get(self.farmer["name"])
        self.load_farmer_image(image)


# Tile Widget
def _rounded_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
    """Return a copy of pixmap with only the top corners rounded."""
    w, h = pixmap.width(), pixmap.height()
    image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.moveTo(radius, 0)
    path.lineTo(w - radius, 0)
    path.quadTo(w, 0, w, radius)  # top-right
    path.lineTo(w, h)
    path.lineTo(0, h)
    path.lineTo(0, radius)
    path.quadTo(0, 0, radius, 0)  # top-left
    path.closeSubpath()
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QPixmap.fromImage(image)


class FarmerTile(QFrame):
    clicked = pyqtSignal(str)

    _TILE_W = 200
    _IMG_H = 112  # 16:9

    def __init__(self, farmer, parent=None):
        super().__init__(parent)
        self.farmer_name = farmer["name"]
        self.setFixedWidth(self._TILE_W)
        self.setCursor(Qt.PointingHandCursor)
        self._set_style(running=False)
        self._init_ui(farmer)

    def _set_style(self, running: bool):
        border = "#10b981" if running else C["border"]
        hover_border = "#10b981" if running else C["accent"]
        self.setStyleSheet(
            f"""
            FarmerTile {{
                background: {C['tile_bg']};
                border: 2px solid {border};
                border-radius: 8px;
            }}
            FarmerTile:hover {{
                border-color: {hover_border};
                background: {C['tile_hover']};
            }}
        """
        )

    def _init_ui(self, farmer):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image wrapper
        img_wrapper = QWidget()
        img_wrapper.setFixedHeight(self._IMG_H)
        img_wrapper.setStyleSheet(f"background: {C['panel2']}; border-radius: 8px 8px 0 0;")
        img_wr_lay = QVBoxLayout(img_wrapper)
        img_wr_lay.setContentsMargins(0, 0, 0, 0)

        _img_w = self._TILE_W - 4  # tile border is 2px on each side
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(_img_w, self._IMG_H)
        self.img_label.setStyleSheet("background: transparent;")
        img_wr_lay.addWidget(self.img_label, 0, Qt.AlignCenter)
        layout.addWidget(img_wrapper)

        # Load image
        image_filename = FARMER_IMAGES.get(farmer["name"])
        if image_filename:
            image_path = os.path.join(_GUI_IMAGES_DIR, image_filename)
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(_img_w, self._IMG_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    x = max(0, (scaled.width() - _img_w) // 2)
                    y = max(0, (scaled.height() - self._IMG_H) // 2)
                    cropped = scaled.copy(x, y, _img_w, self._IMG_H)
                    self.img_label.setPixmap(_rounded_pixmap(cropped, 9))

        # Body
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(8, 20, 8, 8)
        body_lay.setSpacing(2)

        name_label = QLabel(farmer["name"])
        name_label.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {C['text']};")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(name_label)

        status_row = QHBoxLayout()
        status_row.setSpacing(4)
        status_row.setContentsMargins(0, 0, 0, 0)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #252535; font-size: 8px;")
        self.status_dot.hide()
        self.status_text = QLabel("")
        self.status_text.setStyleSheet("font-size: 10px; color: #3f3f5a;")
        status_row.addStretch(1)
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_text)
        status_row.addStretch(1)
        body_lay.addLayout(status_row)

        layout.addWidget(body)

    def set_running(self, running: bool):
        self._set_style(running)
        if running:
            self.status_dot.setStyleSheet("color: #10b981; font-size: 8px;")
            self.status_dot.show()
            self.status_text.setStyleSheet("font-size: 10px; color: #10b981;")
            self.status_text.setText("Running")
        else:
            self.status_dot.hide()
            self.status_text.setText("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.farmer_name)
        super().mousePressEvent(event)


# Grid View


class GridView(QWidget):
    farmer_selected = pyqtSignal(str)

    _COLS = 5

    def __init__(self, farmers, parent=None):
        super().__init__(parent)
        self._tiles: dict = {}
        self._init_ui(farmers)

    def _init_ui(self, farmers):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Build rows of tiles, each row centered with stretches
        container = QWidget()
        container.setStyleSheet(f"background: {C['bg']};")
        v_lay = QVBoxLayout(container)
        v_lay.setContentsMargins(0, 24, 0, 24)
        v_lay.setSpacing(9)

        rows = [farmers[i : i + self._COLS] for i in range(0, len(farmers), self._COLS)]
        for row_farmers in rows:
            row = QHBoxLayout()
            row.setSpacing(9)
            row.addStretch(1)
            for farmer in row_farmers:
                tile = FarmerTile(farmer)
                tile.clicked.connect(self.farmer_selected)
                self._tiles[farmer["name"]] = tile
                row.addWidget(tile)
            row.addStretch(1)
            v_lay.addLayout(row)

        v_lay.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def filter(self, text: str):
        lower = text.strip().lower()
        for name, tile in self._tiles.items():
            tile.setVisible(not lower or lower in name.lower())

    def set_running(self, farmer_name: str, running: bool):
        if farmer_name in self._tiles:
            self._tiles[farmer_name].set_running(running)


# Detail View


class DetailView(QWidget):
    """Wraps a FarmerTab with the detail bar (← Back + name + running status)."""

    def __init__(self, farmer, controller, back_callback, parent=None):
        super().__init__(parent)
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Detail bar ──
        detail_bar = QWidget()
        detail_bar.setFixedHeight(40)
        detail_bar.setStyleSheet(f"background: {C['panel']}; border-bottom: 1px solid {C['border']};")
        bar_lay = QHBoxLayout(detail_bar)
        bar_lay.setContentsMargins(18, 0, 18, 0)
        bar_lay.setSpacing(12)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(_BTN_BACK_STYLE)
        back_btn.clicked.connect(back_callback)
        bar_lay.addWidget(back_btn)

        name_lbl = QLabel(farmer["name"])
        name_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C['text']};")
        bar_lay.addWidget(name_lbl)

        bar_lay.addStretch(1)

        self.running_lbl = QLabel("")
        self.running_lbl.setStyleSheet("font-size: 13px; color: #10b981;")
        bar_lay.addWidget(self.running_lbl)

        layout.addWidget(detail_bar)

        # ── FarmerTab ──
        self.farmer_tab = FarmerTab(farmer, controller)
        layout.addWidget(self.farmer_tab, 1)
        self.controller.running_changed.connect(self._on_running_changed)
        self._on_running_changed(self.controller.is_running, self.controller.process_id)

    def _on_running_changed(self, running: bool, pid: int):
        del pid
        if running:
            self.running_lbl.setText("● Running")
        else:
            self.running_lbl.setText("")


# List View


class ListView(QWidget):
    """Sidebar list + right content panel (alternative to grid)."""

    def __init__(self, farmers, controllers, parent=None):
        super().__init__(parent)
        self._farmers = farmers
        self._controllers = controllers
        self._farmer_tabs: dict = {}
        self._list_rows: dict = {}  # farmer_name → row index in QListWidget
        self._slot_built: list[bool] = []  # parallel to self._stack indices; False = placeholder
        self._row_to_farmer: dict = {}  # stack/row index → farmer name (rows 1+ only)
        self._about_tab: AboutTab | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Left sidebar ──
        sidebar = QWidget()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"background: {C['panel']}; border-right: 1px solid {C['border']};")
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(0, 8, 0, 8)
        sidebar_lay.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; font-size: 13px; }"
            f"QListWidget::item {{ color: {C['dim']}; padding: 9px 16px; }}"
            f"QListWidget::item:selected {{ background: {C['panel2']};"
            f"  border-left: 3px solid {C['accent']}; padding-left: 13px; }}"
            f"QListWidget::item:hover:!selected {{ background: {C['panel3']}; }}"
        )
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Row 0: About
        self._list.addItem(QListWidgetItem("  About"))

        # Rows 1+: farmers
        for i, farmer in enumerate(self._farmers):
            item = QListWidgetItem("  " + farmer["name"])
            self._list.addItem(item)
            self._list_rows[farmer["name"]] = i + 1
            self._row_to_farmer[i + 1] = farmer["name"]

        self._list.currentRowChanged.connect(self._on_row_changed)
        sidebar_lay.addWidget(self._list)
        layout.addWidget(sidebar)

        # ── Right content stack ──
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {C['bg']};")

        # Empty placeholder per row (index 0 = About, indices 1+ = farmers).
        # Real widgets are injected lazily on first selection; this keeps stack
        # indices 1:1 with sidebar rows without paying the build cost up front.
        for _ in range(1 + len(self._farmers)):
            self._stack.addWidget(self._make_slot())
            self._slot_built.append(False)

        # Sidebar dot indicator must update for every farmer, even before its
        # tab is built — so the running_changed wiring stays eager.
        for farmer in self._farmers:
            controller = self._controllers[farmer["name"]]
            controller.running_changed.connect(
                lambda running, pid, n=farmer["name"]: self._on_running_changed(n, running)
            )
            self._on_running_changed(farmer["name"], controller.is_running)

        layout.addWidget(self._stack, 1)

        # Visually select row 0 (About) without triggering the lazy build now;
        # defer the actual AboutTab construction to the next event-loop tick so
        # the window paints first, then the About content fills in.
        self._list.blockSignals(True)
        self._list.setCurrentRow(0)
        self._list.blockSignals(False)
        QTimer.singleShot(0, lambda: self._on_row_changed(0))

    @staticmethod
    def _make_slot() -> QWidget:
        slot = QWidget()
        lay = QVBoxLayout(slot)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return slot

    def _on_row_changed(self, row):
        if row < 0:
            return
        if not self._slot_built[row]:
            self._build_slot(row)
            self._slot_built[row] = True
        self._stack.setCurrentIndex(row)

    def _build_slot(self, row: int) -> None:
        slot = self._stack.widget(row)
        if row == 0:
            self._about_tab = AboutTab()
            about_scroll = QScrollArea()
            about_scroll.setWidgetResizable(True)
            about_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }}")
            about_scroll.setWidget(self._about_tab)
            slot.layout().addWidget(about_scroll)
            return

        farmer_name = self._row_to_farmer[row]
        farmer = next(f for f in self._farmers if f["name"] == farmer_name)
        tab = FarmerTab(farmer, self._controllers[farmer_name])
        self._farmer_tabs[farmer_name] = tab
        slot.layout().addWidget(tab)

    def _on_running_changed(self, name: str, running: bool):
        row = self._list_rows.get(name)
        if row is None:
            return
        item = self._list.item(row)
        if item is None:
            return
        if running:
            item.setText("●  " + name)
            item.setForeground(QColor(C["running"]))
        else:
            item.setText("  " + name)
            item.setForeground(QColor(C["dim"]))

    def show_about(self):
        self._list.setCurrentRow(0)


# Main Window

_BTN_BACK_STYLE = f"""
    QPushButton {{
        background: {C['btn_sec_bg']};
        border: 1px solid {C['border2']};
        border-radius: 6px;
        color: {C['btn_sec_text']};
        padding: 4px 13px;
        font-size: 13px;
    }}
    QPushButton:hover {{ border-color: {C['accent']}; background: {C['panel2']}; }}
    QPushButton:pressed {{ background: {C['btn_sec_bg']}; border-color: {C['accent']}; }}
"""

_BTN_TOP_STYLE = f"""
    QPushButton {{
        background: {C['btn_sec_bg']};
        border: 1px solid {C['border2']};
        border-radius: 6px;
        color: {C['btn_sec_text']};
        padding: 6px 16px;
        font-size: 13px;
    }}
    QPushButton:hover {{ border-color: {C['accent']}; background: {C['panel2']}; }}
    QPushButton:pressed {{ background: {C['btn_sec_bg']}; border-color: {C['accent']}; }}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoFarmers - 7DS Grand Cross")
        self.setGeometry(100, 100, 1200, 700)
        _icon_path = os.path.join(os.path.dirname(__file__), "..", "gui_images", "main.ico")
        self.setWindowIcon(QIcon(_icon_path))

        self._detail_views: dict = {}
        self._farmer_by_name = {f["name"]: f for f in FARMERS}
        self._active_main_view: str = "list"  # "grid" or "list"

        self._settings_tab: SettingsTab | None = None
        self._about_tab: AboutTab | None = None
        self._settings_wrapper: QWidget | None = None
        self._about_wrapper: QWidget | None = None

        self._controllers = {
            farmer["name"]: FarmerController(
                farmer,
                password_supplier=lambda: self.settings_tab.password_edit.text(),
                parent=self,
            )
            for farmer in FARMERS
        }

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──
        top_bar = QWidget()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"background: {C['panel']}; border-bottom: 2px solid {C['border']};")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(20, 0, 20, 0)
        top_lay.setSpacing(14)

        logo = QLabel()
        logo.setText(
            f'<span style="font-size:19px;font-weight:800;color:{C["text"]};">Auto</span>'
            f'<span style="font-size:19px;font-weight:800;color:{C["accent"]};">Farmers</span>'
        )
        logo.setTextFormat(Qt.RichText)
        top_lay.addWidget(logo)

        top_lay.addStretch(1)

        self._view_toggle_btn = QPushButton("⊞  Grid")
        self._view_toggle_btn.setStyleSheet(_BTN_TOP_STYLE)
        self._view_toggle_btn.clicked.connect(self._toggle_view)
        top_lay.addWidget(self._view_toggle_btn)

        _theme_label = "☀  Light" if _ACTIVE_THEME == "dark" else "🌙  Dark"
        self._theme_btn = QPushButton(_theme_label)
        self._theme_btn.setStyleSheet(_BTN_TOP_STYLE)
        self._theme_btn.clicked.connect(self._toggle_theme)
        top_lay.addWidget(self._theme_btn)

        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setStyleSheet(_BTN_TOP_STYLE)
        settings_btn.clicked.connect(lambda: self._show_page("settings"))
        top_lay.addWidget(settings_btn)

        about_btn = QPushButton("ℹ About")
        about_btn.setStyleSheet(_BTN_TOP_STYLE)
        about_btn.clicked.connect(lambda: self._show_page("about"))
        top_lay.addWidget(about_btn)

        root.addWidget(top_bar)

        # ── Stacked views ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"QStackedWidget {{ background: {C['bg']}; }}")

        self.grid_view = GridView(FARMERS)
        self.grid_view.farmer_selected.connect(self._on_farmer_selected)
        for name, controller in self._controllers.items():
            controller.running_changed.connect(lambda running, pid, n=name: self.grid_view.set_running(n, running))
            self.grid_view.set_running(name, controller.is_running)

        self.list_view = ListView(FARMERS, self._controllers)

        self.stack.addWidget(self.grid_view)
        self.stack.addWidget(self.list_view)

        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.stack.setCurrentWidget(self.list_view)

    @property
    def settings_tab(self) -> "SettingsTab":
        if self._settings_tab is None:
            self._settings_tab = SettingsTab()
        return self._settings_tab

    @property
    def about_tab(self) -> "AboutTab":
        if self._about_tab is None:
            self._about_tab = AboutTab(restart_safe_supplier=lambda: not self._any_farmer_running())
        return self._about_tab

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

        back_bar = QWidget()
        back_bar.setFixedHeight(40)
        back_bar.setStyleSheet(f"background: {C['panel']}; border-bottom: 1px solid {C['border']};")
        bar_lay = QHBoxLayout(back_bar)
        bar_lay.setContentsMargins(18, 0, 18, 0)
        bar_lay.setSpacing(12)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(_BTN_BACK_STYLE)
        back_btn.clicked.connect(self._show_grid)
        bar_lay.addWidget(back_btn)
        if title:
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C['text']};")
            bar_lay.addWidget(title_lbl)
        bar_lay.addStretch(1)

        lay.addWidget(back_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['bg']}; }}")
        scroll.setWidget(page_widget)
        lay.addWidget(scroll, 1)

        return wrapper

    def _on_farmer_selected(self, name: str):
        view = self._ensure_detail_view(name)
        self.stack.setCurrentWidget(view)

    def _show_page(self, page_id: str):
        if page_id == "about":
            self.stack.setCurrentWidget(self.about_wrapper)
        elif page_id == "settings":
            self.stack.setCurrentWidget(self.settings_wrapper)
        else:
            self._show_grid()

    def _toggle_theme(self):
        if self._any_farmer_running():
            QMessageBox.information(
                self,
                "Theme Change Blocked",
                "Stop all running farmers before changing the theme.",
            )
            return
        _save_theme("light" if _ACTIVE_THEME == "dark" else "dark")
        if not _restart_application():
            QMessageBox.critical(
                self,
                "Theme Change Failed",
                "The theme was saved, but the GUI could not be reopened automatically.",
            )
            return
        QApplication.instance().quit()

    def _toggle_view(self):
        if self._active_main_view == "list":
            self._active_main_view = "grid"
            self._view_toggle_btn.setText("☰  List")
            self.stack.setCurrentWidget(self.grid_view)
        else:
            self._active_main_view = "list"
            self._view_toggle_btn.setText("⊞  Grid")
            self.list_view.show_about()
            self.stack.setCurrentWidget(self.list_view)

    def _show_grid(self):
        """Return to whichever main view (grid or list) the user had selected."""
        if self._active_main_view == "list":
            self._view_toggle_btn.setText("⊞  Grid")
            self.stack.setCurrentWidget(self.list_view)
        else:
            self._view_toggle_btn.setText("☰  List")
            self.stack.setCurrentWidget(self.grid_view)

    def _ensure_detail_view(self, name: str) -> "DetailView":
        if name in self._detail_views:
            return self._detail_views[name]
        farmer_def = self._farmer_by_name[name]
        view = DetailView(farmer_def, self._controllers[name], back_callback=self._show_grid)
        self.stack.addWidget(view)
        self._detail_views[name] = view
        return view

    def _any_farmer_running(self) -> bool:
        return any(controller.is_running for controller in self._controllers.values())


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
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    _apply_dark_title_bar(int(window.winId()), _ACTIVE_THEME == "dark")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
