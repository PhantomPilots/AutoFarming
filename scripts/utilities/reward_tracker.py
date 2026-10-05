"""Follow the reward tiles of a farmer's result screens and print one '[REWARDS]' line per run for the GUI."""

import json
import time

import numpy as np
from utilities.logging_utils import LoggerWrapper
from utilities.reward_reader import RewardReader, RewardSet


class RewardTracker:
    """Keep the most complete read of the current run, then report it once the run is counted.

    The rewards may be shown before or after the moment the farmer counts the run: if nothing was read
    yet at that point, keep looking at every screenshot for `watch_seconds`.
    """

    def __init__(self, reward_set: RewardSet, logger: LoggerWrapper, watch_seconds: float = 10):
        self._set = reward_set
        self._reader: RewardReader | None = None
        self._logger = logger
        self._watch_seconds = watch_seconds
        self._tiles: list = []
        self._tiles_screenshot = None
        self._last_screenshot = None
        self._watch_until = 0.0

    def collect(self, screenshot: np.ndarray):
        """Read the reward tiles on this screenshot, keeping the read with the most tiles."""
        if self._reader is None:
            self._reader = RewardReader(self._set)
        self._last_screenshot = screenshot
        try:
            tiles = self._reader.find_tiles(screenshot)
        except Exception as exc:  # A vision hiccup must never stop the farmer
            self._logger.warning(f"Couldn't read the rewards: {exc}")
            return
        if len(tiles) > len(self._tiles):
            self._tiles = tiles
            self._tiles_screenshot = screenshot

    def run_finished(self):
        """The farmer counted a run: report its rewards now, or keep watching for them."""
        if not self._report():
            self._watch_until = time.time() + self._watch_seconds

    def tick(self, screenshot: np.ndarray):
        """Call on every screenshot: while watching, look for the rewards of the last run."""
        if not self._watch_until:
            return
        self.collect(screenshot)
        if self._report():
            return
        if time.time() > self._watch_until:
            self.give_up()

    def give_up(self):
        """A new run starts: drop what wasn't reported, and keep the last result screen if we were watching."""
        self._tiles, self._tiles_screenshot = [], None
        if not self._watch_until:
            return
        self._watch_until = 0.0
        if self._last_screenshot is not None:
            path = self._logger.save_image(self._last_screenshot, subdir=self._set.log_subdir)
            print(f"[WARNING] Couldn't read the rewards of this run. Screen saved to {path}")
        self._last_screenshot = None

    def _report(self) -> bool:
        tiles, self._tiles = self._tiles, []
        screenshot, self._tiles_screenshot = self._tiles_screenshot, None
        if not tiles:
            return False
        self._watch_until = 0.0
        self._last_screenshot = None

        totals: dict[str, int] = {}
        for tile in tiles:
            totals[tile.key] = totals.get(tile.key, 0) + tile.count
        labels = self._set.labels
        print("Rewards of this run: " + ", ".join(f"{labels.get(k, k)} x{v}" for k, v in totals.items()))
        print(f"[REWARDS] {json.dumps(totals)}")
        self._save_reward_row(screenshot, tiles)
        return True

    def _save_reward_row(self, screenshot: np.ndarray | None, tiles: list):
        """Keep a crop of the reward row so the reading can be checked and calibrated."""
        if screenshot is None:
            return
        x0 = max(0, min(t.rect[0] for t in tiles) - 10)
        y0 = max(0, min(t.rect[1] for t in tiles) - 10)
        x1 = min(screenshot.shape[1], max(t.rect[0] + t.rect[2] for t in tiles) + 10)
        y1 = min(screenshot.shape[0], max(t.rect[1] + t.rect[3] for t in tiles) + 10)
        try:
            self._logger.save_image(screenshot[y0:y1, x0:x1], name="rewards", subdir=self._set.log_subdir)
        except Exception:
            pass
