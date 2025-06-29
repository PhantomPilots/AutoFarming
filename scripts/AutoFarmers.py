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
import signal
import sys
import time

from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette, QPixmap
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
from utilities.capture_window import resize_7ds_window

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
            {"name": "--time-to-sleep", "label": "Time to Sleep (s)", "type": "text", "default": "9.15"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Farmer",
        "script": "BirdFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Bird Floor 4",
        "script": "BirdFloor4Farmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Farmer",
        "script": "DeerFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {
        "name": "Deer Floor 4",
        "script": "DeerFloor4Farmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {"name": "Deer Whale", "script": "DeerFarmerWhale.py", "args": []},
    {
        "name": "Dogs Farmer",
        "script": "DogsFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
        ],
    },
    {"name": "Dogs Whale", "script": "DogsFarmerWhale.py", "args": []},
    {
        "name": "Snake Farmer",
        "script": "SnakeFarmer.py",
        "args": [
            {"name": "--password", "label": "Password", "type": "text", "default": ""},
            {"name": "--clears", "label": "Clears", "type": "text", "default": "inf"},
            {"name": "--do-dailies", "label": "Do Dailies", "type": "checkbox", "default": True},
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
        "name": "Tower Trials",
        "script": "TowerTrialsFarmer.py",
        "args": [],
    },
]


class FarmerTab(QWidget):
    def __init__(self, farmer, parent=None):
        super().__init__(parent)
        self.farmer = farmer
        self.process = None
        self.output_lines = []
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        # Left panel
        left_panel = QVBoxLayout()
        # Title
        title = QLabel(f"{self.farmer['name']} Configuration")
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
            args_group.setLayout(args_layout)
            left_panel.addWidget(args_group)
        else:
            self.arg_widgets = {}
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
                    args.append("--do-dailies")
                else:
                    args.append("--no-do-dailies")
            elif arg["type"] == "multiselect":
                if selected := [item.text() for item in widget.selectedItems()]:
                    args.extend([arg["name"], ",".join(selected)])
            elif value := widget.text():
                args.extend([arg["name"], value])
        return args

    def start_farmer(self):
        if self.process is not None:
            return

        # First, try to resize the 7DS window to the required size
        self.append_terminal("Attempting to resize 7DS window to 540x960...\n")
        resize_success = resize_7ds_window(width=538, height=921)

        if not resize_success:
            self.append_terminal("[WARNING] Failed to resize 7DS window. Continuing with current window size...\n")
        else:
            self.append_terminal("[SUCCESS] 7DS window resized successfully!\n")

        # Small delay to allow window resize to complete
        time.sleep(0.5)

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
        self.append_terminal(
            f"Started {self.farmer['name']} with:\n{' '.join([sys.executable, '-u', script_path]+display_args)}\n"
        )

        # Add a timer to periodically check for output (in case of buffering issues)
        self.output_timer = QTimer(self)
        self.output_timer.timeout.connect(self.check_output)
        self.output_timer.start(100)  # Check every 100ms

    def stop_farmer(self):
        if self.process is not None:
            with contextlib.suppress(Exception):
                # Stop the output timer
                if hasattr(self, "output_timer") and self.output_timer is not None:
                    self.output_timer.stop()
                    self.output_timer.deleteLater()
                    self.output_timer = None
                self.process.kill()  # QProcess does not support SIGINT on Windows, so we use kill
            self.process = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_terminal("\nProcess stopped.\n")

    def handle_stdout(self):
        if self.process is None:
            return
        while self.process.canReadLine():
            line = bytes(self.process.readLine()).decode("utf-8", errors="replace")
            self.append_terminal(line)

    def handle_stderr(self):
        if self.process is None:
            return
        while self.process.canReadLine():
            line = bytes(self.process.readLine()).decode("utf-8", errors="replace")
            self.append_terminal(line)

    def append_terminal(self, text):
        # Output limiting
        self.output_lines.extend(text.splitlines(True))
        if len(self.output_lines) > 1000:
            self.output_lines = self.output_lines[-1000:]
        self.terminal.setPlainText("".join(self.output_lines))
        self.terminal.moveCursor(self.terminal.textCursor().End)

    def process_finished(self):
        # Stop the output timer
        if hasattr(self, "output_timer") and self.output_timer is not None:
            self.output_timer.stop()
            self.output_timer.deleteLater()
            self.output_timer = None
        self.process = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
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
            "Final Boss": "final_boss.png",
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
        self.setGeometry(100, 100, 1000, 600)
        self.tabs = QTabWidget()
        for farmer in FARMERS:
            tab = FarmerTab(farmer)
            self.tabs.addTab(tab, farmer["name"])
        self.setCentralWidget(self.tabs)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
