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
# This script provides a tabbed GUI for all farmer scripts, with argument fields, terminal output, and process control.

import contextlib
import os
import re
import signal
import sys
import time

from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, QUrl
from PyQt5.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QPalette,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Import the window resize function
from utilities.capture_window import capture_window, resize_7ds_window
from utilities.utilities import get_pause_flag_path

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
• NO SKULD</p>
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
<p><strong>Requirements:</strong><br>
• Team A: Skuld (att/crit), any 3 boosters<br>
• Team B: Anything, won't be used</p>
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

# Farmer script definitions (argument structure)
FARMERS = [
    {
        "name": "Demon Farmer",
        "script": "DemonFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {
                "name": "--indura-diff",
                "label": "Indura Difficulty",
                "type": "dropdown",
                "choices": ["extreme", "hell", "chaos"],
                "default": "chaos",
            },
            {
                "name": "--demons-to-farm",
                "label": "Demons to Farm",
                "type": "multiselect",
                "choices": ["indura_demon", "og_demon", "bell_demon", "red_demon", "gray_demon", "crimson_demon"],
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
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Farmer",
        "script": "BirdFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Floor 4",
        "script": "BirdFloor4Farmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Farmer",
        "script": "DeerFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Floor 4",
        "script": "DeerFloor4Farmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Dogs Farmer",
        "script": "DogsFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Snake Farmer",
        "script": "SnakeFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Rat Farmer",
        "script": "RatFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Whale",
        "script": "DeerFarmerWhale.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Dogs Whale",
        "script": "DogsFarmerWhale.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies (2am PST)", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Snake Whale",
        "script": "SnakeFarmerWhale.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
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
        "name": "SA Coin Dungeon Farmer",
        "script": "SADungeonFarmer.py",
        "args": [
            {
                "name": "--min-chest-type",
                "label": "Min chest type",
                "type": "dropdown",
                "choices": ["bronze", "silver", "gold"],
                "default": "bronze"
            }
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
]


class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.update_process = None
        self.updating = False
        self.repo_root = os.path.dirname(os.path.dirname(__file__))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 20)

        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)

        # Main title
        title = QLabel("🚀 AutoFarmers — 7DS Grand Cross")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title)

        # Tagline
        tagline = QLabel("Automate the grind. Save your time.")
        tagline.setFont(QFont("Arial", 12))
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet("color: #666; font-style: italic;")
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
        self.status_label.setStyleSheet("color: #888; font-size: 15px;")
        layout.addWidget(self.status_label)

        layout.addStretch(1)

    def load_hero_image(self, layout):
        """Load and display the hero image"""
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("border: 1px solid #aaa; background: #e0e0e0;")

        # Try to load the GUI image from readme_images
        image_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "gui_images", "main_gui.jpg"),
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
            img_label.setStyleSheet("border: 1px solid #aaa; background: #e0e0e0; color: #666; font-size: 14px;")

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
        self.update_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px;")
        self.update_btn.clicked.connect(self.on_update_clicked)
        btn_layout.addWidget(self.update_btn)

        # GitHub button
        github_btn = QPushButton("🐙 GitHub")
        github_btn.setStyleSheet("background-color: #333; color: white; font-weight: bold; padding: 8px 16px;")
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
        desc_label.setStyleSheet("font-size: 12px; line-height: 1.4;")
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
        farmers_label.setStyleSheet("font-size: 12px; line-height: 1.4;")
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
        req_label.setStyleSheet("font-size: 12px; line-height: 1.4;")
        farmers_req_layout.addWidget(req_label)

        layout.addLayout(farmers_req_layout)

        # Call to action
        cta_label = QLabel()
        cta_label.setWordWrap(True)
        cta_label.setAlignment(Qt.AlignCenter)
        cta_label.setText("<p><em>Pick a farmer tab to configure and start, and join our Discord for help!</em></p>")
        cta_label.setStyleSheet("font-size: 12px; line-height: 1.4; font-style: italic; color: #666;")
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
        self.run_git_command(["stash"], self.after_stash)

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
            self.updating = False
            self.update_btn.setEnabled(True)
            return

        # Stash successful, now run git pull
        self.status_label.setText("🔄 Running 'git pull'...")
        self.run_git_command(["pull"], self.after_pull)

    def after_pull(self, exit_code):
        """Handle completion of git pull command"""
        if exit_code == 0:
            self.status_label.setText("✅ Update complete!")
        else:
            self.status_label.setText("❌ git pull failed")

        # Re-enable button and reset state
        self.updating = False
        self.update_btn.setEnabled(True)

        # Clear status after 5 seconds
        QTimer.singleShot(5000, lambda: self.status_label.setText(""))

    def run_git_command(self, args, on_finished):
        """Run a git command in the repo root directory"""
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

        # Start the git command
        self.update_process.start("git", args)

        if not self.update_process.waitForStarted(3000):
            self.status_label.setText("❌ Failed to start git command")
            self.update_process = None
            self.updating = False
            self.update_btn.setEnabled(True)

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


class FarmerTab(QWidget):
    _COLOR_TAG_RE = re.compile(r"<color=([^>]+)>(.*?)</color>", re.IGNORECASE | re.DOTALL)

    def __init__(self, farmer, parent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.process = None
        self.output_lines = []
        self.paused = False
        self.sa_chest_warning_label = None
        self._default_fmt = QTextCharFormat()
        self._default_fmt.setForeground(QColor("#eeeeee"))
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        # Left panel
        left_panel = QVBoxLayout()
        # Title
        title = QLabel(f"{self.farmer['name']}")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        left_panel.addWidget(title)
        # Image placeholder
        image_size = (400, 250)
        img = QLabel(f"[Image Placeholder]\n{image_size[0]}x{image_size[1]}")
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("border: 1px solid #aaa; background: #e0e0e0; color: #666;")
        img.setFixedSize(*image_size)

        # Load farmer-specific image
        self.load_farmer_image(img, image_size)

        left_panel.addWidget(img)
        # Arguments
        if self.farmer["args"]:
            args_group = QGroupBox("Arguments")
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
                    widget = QListWidget()
                    widget.setSelectionMode(QListWidget.MultiSelection)
                    for choice in arg["choices"]:
                        item = QListWidgetItem(choice)
                        widget.addItem(item)
                        if choice in arg.get("default", []):
                            item.setSelected(True)
                    widget.setMaximumHeight(80)
                else:
                    widget = QLineEdit()
                    widget.setText(arg["default"])
                    if arg["label"].lower() == "password":
                        widget.setEchoMode(QLineEdit.Password)
                self.arg_widgets[arg["name"]] = widget
                args_layout.addRow(arg["label"] + ":", widget)

                if self.farmer["name"] == "SA Coin Dungeon Farmer" and arg["name"] == "--min-chest-type":
                    widget.currentTextChanged.connect(self.update_sa_chest_warning)
            args_group.setLayout(args_layout)
            left_panel.addWidget(args_group)

            if self.farmer["name"] == "SA Coin Dungeon Farmer":
                self.sa_chest_warning_label = QLabel()
                self.sa_chest_warning_label.setWordWrap(True)
                self.sa_chest_warning_label.setStyleSheet(
                    "font-size: 12px; color: #8B0000; border: 1px solid #8B0000; padding: 6px;"
                )
                self.sa_chest_warning_label.hide()
                left_panel.addWidget(self.sa_chest_warning_label)
                self.update_sa_chest_warning(self.arg_widgets["--min-chest-type"].currentText())
        else:
            self.arg_widgets = {}

        # Add whale farmer requirements if applicable
        if self.farmer["name"] in REQUIREMENTS:
            req_label = QLabel()
            req_label.setWordWrap(True)
            req_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            req_label.setText(REQUIREMENTS[self.farmer["name"]])
            req_label.setStyleSheet("font-size: 13px; color: #777; line-height: 1.2;")
            req_label.setMaximumHeight(180)
            req_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            left_panel.addWidget(req_label)
            left_panel.addSpacing(4)

        # Start/Stop buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_farmer)
        btn_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_farmer)
        btn_layout.addWidget(self.stop_btn)
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setStyleSheet("background-color: #FFC107; color: white; font-weight: bold;")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        btn_layout.addWidget(self.pause_btn)
        self.resize_btn = QPushButton("RESIZE")
        self.resize_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.resize_btn.clicked.connect(self.resize_window)
        btn_layout.addWidget(self.resize_btn)
        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.clear_btn.clicked.connect(self.clear_output)
        btn_layout.addWidget(self.clear_btn)
        left_panel.addLayout(btn_layout)
        left_panel.addStretch(1)
        layout.addLayout(left_panel, 1)
        # Right panel (terminal)
        right_panel = QVBoxLayout()
        terminal_label = QLabel("Output")
        terminal_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_panel.addWidget(terminal_label)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 9))
        self.terminal.setStyleSheet("background: #222; color: #eee;")
        right_panel.addWidget(self.terminal, 1)
        layout.addLayout(right_panel, 2)
        self.setLayout(layout)

        # Display free software message in terminal
        self.append_terminal(FREE_SOFTWARE_MESSAGE)

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

    def get_args(self):
        args = []
        for arg in self.farmer["args"]:
            widget = self.arg_widgets[arg["name"]]
            if arg["type"] == "dropdown":
                if value := widget.currentText():
                    args.extend([arg["name"], value])
            elif arg["type"] == "checkbox":
                checked = widget.isChecked()
                if checked:
                    args.append(arg["name"])
            elif arg["type"] == "multiselect":
                if selected := [item.text() for item in widget.selectedItems()]:
                    args.extend([arg["name"]] + selected)
            elif value := widget.text():
                args.extend([arg["name"], value])
        return args

    def start_farmer(self):
        if self.process is not None:
            return

        # First, try to resize the 7DS window to the required size
        self.resize_window()

        script_path = os.path.join(os.path.dirname(__file__), self.farmer["script"])
        args = self.get_args()
        # Mask password in the command display
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

        self.process = QProcess(self)

        # Force unbuffered output to ensure print statements are captured immediately
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)

        # Capture both stdout and stderr
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.terminal.clear()
        self.output_lines = []

        # Start the process with -u flag for unbuffered output
        self.process.start(sys.executable, ["-u", script_path] + args)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("PAUSE")
        self.paused = False

        # Clean up any old pause flag for this PID
        pid = self.process.processId()
        if pid > 0:
            flag_path = get_pause_flag_path(pid)
            if os.path.exists(flag_path):
                try:
                    os.remove(flag_path)
                except:
                    pass  # Ignore cleanup errors

        self.append_terminal(
            f"Started {self.farmer['name']} with:\n{' '.join([sys.executable, '-u', script_path]+display_args)}\n"
        )

        # Add a timer to periodically check for output (in case of buffering issues)
        self.output_timer = QTimer(self)
        self.output_timer.timeout.connect(self.check_output)
        self.output_timer.start(100)  # Check every 100ms

    def stop_farmer(self):
        if self.process is not None:
            # Clean up pause flag before stopping
            pid = self.process.processId()
            if pid > 0:
                flag_path = get_pause_flag_path(pid)
                if os.path.exists(flag_path):
                    try:
                        os.remove(flag_path)
                    except:
                        pass  # Ignore cleanup errors

            with contextlib.suppress(Exception):
                # Stop the output timer
                if hasattr(self, "output_timer") and self.output_timer is not None:
                    self.output_timer.stop()
                    self.output_timer.deleteLater()
                    self.output_timer = None
                self.process.kill()
            self.process = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("PAUSE")
        self.paused = False
        self.append_terminal("\nProcess stopped.\n")

    def handle_stdout(self):
        if self.process is None:
            return
        lines = []
        while self.process.canReadLine():
            lines.append(bytes(self.process.readLine()).decode("utf-8", errors="replace"))
        if lines:
            self.append_terminal("".join(lines))

    def handle_stderr(self):
        if self.process is None:
            return
        lines = []
        while self.process.canReadLine():
            lines.append(bytes(self.process.readLine()).decode("utf-8", errors="replace"))
        if lines:
            self.append_terminal("".join(lines))

    def append_terminal(self, text):
        new_lines = text.splitlines(True)
        self.output_lines.extend(new_lines)

        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-1000:]
            # Trimmed: must rebuild entire document
            self.terminal.clear()
            self._render_lines(self.output_lines)
        else:
            # Append only the new lines (no clear/rebuild)
            self._render_lines(new_lines)

    def _render_lines(self, lines):
        """Render the given lines at the end of the terminal widget."""
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)

        for line in lines:
            for segment_text, segment_color in self._parse_color_segments(line):
                fmt = QTextCharFormat(self._default_fmt)
                if segment_color is not None:
                    fmt.setForeground(segment_color)
                cursor.insertText(segment_text, fmt)

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

    def process_finished(self):
        # Clean up pause flag when process finishes
        if self.process is not None:
            pid = self.process.processId()
            if pid > 0:
                flag_path = get_pause_flag_path(pid)
                if os.path.exists(flag_path):
                    try:
                        os.remove(flag_path)
                    except:
                        pass  # Ignore cleanup errors

        # Stop the output timer
        if hasattr(self, "output_timer") and self.output_timer is not None:
            self.output_timer.stop()
            self.output_timer.deleteLater()
            self.output_timer = None
        self.process = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("PAUSE")
        self.paused = False
        self.append_terminal("\nProcess finished.\n")

    def check_output(self):
        if self.process is None:
            return
        if self.process.bytesAvailable() > 0:
            self.handle_stdout()

    def clear_output(self):
        self.terminal.clear()
        self.output_lines = []
        self.append_terminal("\nOutput cleared.\n")

    def resize_window(self):
        """Resize the 7DS window to the required size"""
        # First, try to resize the 7DS window to the required size
        if resize_7ds_window(width=538, height=921):
            # Capture screenshot to get actual dimensions after resize
            try:
                screenshot, _ = capture_window()
                screenshot_shape = screenshot.shape[:2]
                self.append_terminal(
                    f"[SUCCESS] 7DS window resized successfully! Screenshot shape: {screenshot_shape}\n"
                )
            except Exception as e:
                self.append_terminal(f"[SUCCESS] 7DS window resized successfully!\n")
        else:
            self.append_terminal("[WARNING] Failed to resize 7DS window. Continuing with current window size...\n")
        # Small delay to allow window resize to complete
        time.sleep(0.5)

    def toggle_pause(self):
        """Toggle pause/resume for the current farmer process"""
        if self.process is None or self.process.state() != QProcess.Running:
            return

        pid = self.process.processId()
        flag_path = get_pause_flag_path(pid)

        if not self.paused:
            # Pause the process
            try:
                with open(flag_path, "w") as f:
                    f.write("")  # Create empty flag file
                self.paused = True
                self.pause_btn.setText("RESUME")
                self.append_terminal(f"[PAUSED] Created pause flag at {flag_path}\n")
            except Exception as e:
                self.append_terminal(f"[ERROR] Failed to create pause flag: {e}\n")
        else:
            # Resume the process
            try:
                self.resize_window()
                if os.path.exists(flag_path):
                    os.remove(flag_path)
                self.paused = False
                self.pause_btn.setText("PAUSE")
                self.append_terminal(f"[RESUMED] Removed pause flag\n")
            except Exception as e:
                self.append_terminal(f"[ERROR] Failed to remove pause flag: {e}\n")

    def load_farmer_image(self, img, image_size):
        """Load and display farmer-specific images"""
        # Map farmer names to their image files
        farmer_images = {
            "Demon Farmer": "demon_farmer.jpg",
            "Bird Farmer": "bird_farmer.jpg",
            "Bird Floor 4": "bird_floor_4.jpeg",
            "Deer Farmer": "deer_farmer.png",
            "Deer Floor 4": "deer_floor_4.png",
            "Deer Whale": "deer_whale.jpg",
            "Tower Trials": "tower_trials_farmer.jpg",
            "Dogs Farmer": "dogs_farmer.jpeg",
            "Dogs Whale": "dogs_whale_farmer.jpg",
            "Snake Farmer": "snake_farmer.png",
            "Rat Farmer": "rat_farmer.jpg",
            "Snake Whale": "snake_whale_farmer.png",
            "Final Boss": "final_boss.png",
            "Accounts Farmer": "accounts_farmer.jpg",  # Placeholder image
            "Reroll Constellation": "reroll_constellation_whale.jpg",  # Placeholder image
            "SA Coin Dungeon Farmer": "sa_coin_farmer.png",
            "Guild Boss Farmer": "guild_boss_farmer.jpg",
            "Demon King Farmer": "dk_farmer.jpg",
        }

        # Check if this farmer has a specific image
        if self.farmer["name"] in farmer_images:
            image_filename = farmer_images[self.farmer["name"]]
            image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gui_images", image_filename)

            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale the image to fit the specified size while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(*image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img.setPixmap(scaled_pixmap)
                    img.setStyleSheet("border: 1px solid #aaa;")
                else:
                    img.setText(f"Failed to load image:\n{image_filename}")
            else:
                img.setText(f"Image not found:\n{image_filename}")
        # If no specific image is defined, keep the placeholder


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoFarmers - 7DS Grand Cross")
        self.setGeometry(100, 100, 1150, 680)  # Adjusted size for About tab
        self.tabs = QTabWidget()

        # Add About tab as the first tab
        about_tab = AboutTab()
        self.tabs.addTab(about_tab, "About")

        # Add farmer tabs
        for farmer in FARMERS:
            tab = FarmerTab(farmer)
            self.tabs.addTab(tab, farmer["name"])

        # Set About tab as the default
        self.tabs.setCurrentIndex(0)

        self.setCentralWidget(self.tabs)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
