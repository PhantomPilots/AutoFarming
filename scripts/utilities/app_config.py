"""Lightweight GUI-facing helpers extracted from utilities.utilities.

This module is deliberately kept dependency-light (only stdlib + yaml + requests)
so the AutoFarmers GUI can import it at startup without dragging in cv2, sklearn,
numpy, pyautogui, dill, or the ~470 image reads triggered by vision_images.
"""

import contextlib
import os
import tempfile
import threading
import time

import requests
import yaml

APP_CONFIG_KEYS = frozenset(
    {
        "ntfy_private_channel",
        "stuck_timeout_minutes",
        "notification_cooldown_minutes",
        "max_notifications_per_incident",
        "game_password",
        "minutes_to_wait_before_login",
    }
)

APP_CONFIG_DEFAULTS = {
    "ntfy_private_channel": "",
    "stuck_timeout_minutes": 10,
    "notification_cooldown_minutes": 5,
    "max_notifications_per_incident": 5,
    "game_password": "",
    "minutes_to_wait_before_login": 30,
}


def get_config_yaml_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")


def load_yaml_config(file_path: str) -> dict:
    """Load a YAML configuration file and return its contents as a dictionary."""
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data if isinstance(data, dict) else {}


class Config:
    """Thread-safe lazy-loading config accessor for scripts/config/config.yaml."""

    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._path = path
        self._data: dict | None = None

    def get(self, key: str, default=None):
        with self._lock:
            if self._data is None:
                try:
                    self._data = load_yaml_config(self._path)
                except (FileNotFoundError, yaml.YAMLError):
                    self._data = {}
            return self._data.get(key, default)

    def reload(self):
        """Drop cached YAML so the next get() reads from disk."""
        with self._lock:
            self._data = None


config = Config(get_config_yaml_path())


def get_minutes_to_wait_before_login() -> int:
    """Minutes to wait after logout before attempting login again (from config.yaml)."""
    raw = config.get("minutes_to_wait_before_login", APP_CONFIG_DEFAULTS["minutes_to_wait_before_login"])
    try:
        n = int(raw)
        return max(1, min(1440, n))
    except (TypeError, ValueError):
        return int(APP_CONFIG_DEFAULTS["minutes_to_wait_before_login"])


class ClickTracker:
    """Thread-safe tracker for click timestamps and repeated-image-click patterns."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last_click_time: float | None = None
        self._last_image_name: str | None = None
        self._last_image_click_time: float | None = None
        self._consecutive_clicks: int = 0

    def record_click(self):
        with self._lock:
            self._last_click_time = time.time()

    def record_image_click(self, image_name: str):
        with self._lock:
            now = time.time()
            self._last_click_time = now
            self._last_image_click_time = now
            if image_name == self._last_image_name:
                self._consecutive_clicks += 1
            else:
                self._last_image_name = image_name
                self._consecutive_clicks = 1

    def get_state(self) -> tuple[float | None, str | None, int, float | None]:
        with self._lock:
            return self._last_click_time, self._last_image_name, self._consecutive_clicks, self._last_image_click_time

    def reset(self):
        with self._lock:
            self._last_click_time = None
            self._last_image_name = None
            self._last_image_click_time = None
            self._consecutive_clicks = 0


click_tracker = ClickTracker()


def get_pause_flag_path(pid: int | None = None) -> str:
    """Get the path to the pause flag file for a given process ID"""
    if pid is None:
        pid = os.getpid()
    return os.path.join(tempfile.gettempdir(), f"autofarmers_pause_{pid}.flag")


def is_paused() -> bool:
    """Check if the current process is paused"""
    return os.path.exists(get_pause_flag_path())


def wait_if_paused(print_messages: bool = True):
    """Wait while the process is paused, with optional status messages"""
    if not is_paused():
        return

    if print_messages:
        print("Paused...")

    while is_paused():
        time.sleep(0.1)

    if print_messages:
        print("Resumed.")


def load_full_config_dict() -> dict:
    """Load scripts/config/config.yaml for merge-writes; missing or invalid file yields {}."""
    path = get_config_yaml_path()
    try:
        data = load_yaml_config(path)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, yaml.YAMLError, OSError):
        return {}


def save_config_updates(updates: dict) -> None:
    """Merge allowed keys into config.yaml and atomically replace the file."""
    path = get_config_yaml_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    merged = load_full_config_dict()
    for key, value in updates.items():
        if key in APP_CONFIG_KEYS:
            merged[key] = value
    merged.pop("default_game_password", None)
    parent = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(prefix="config_", suffix=".yaml.tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            yaml.safe_dump(merged, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise


def test_ntfy_connection() -> tuple[bool, str]:
    """POST a one-line test message synchronously; returns (success, message for UI)."""
    channel = (config.get("ntfy_private_channel") or "").strip()
    if not channel:
        return False, "Set a topic and save, or leave empty to disable notifications."
    try:
        url = f"https://ntfy.sh/{channel}"
        resp = requests.post(url, data=b"AutoFarmers: test notification", timeout=10)
        resp.raise_for_status()
        return True, "Test notification sent."
    except requests.RequestException as e:
        return False, f"Failed to send: {e}"
