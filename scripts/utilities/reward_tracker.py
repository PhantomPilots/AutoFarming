"""Read result screens and report one '[REWARDS]' line per successfully read run."""

import json
import time

import numpy as np
from utilities.logging_utils import LoggerWrapper
from utilities.reward_reader import RewardReader
from utilities.reward_sets import RewardSet


class RewardTracker:
    """Keep the best reading until a clear is counted, retrying unclear result screens."""

    def __init__(self, reward_set: RewardSet, logger: LoggerWrapper, watch_seconds: float = 10):
        self._set = reward_set
        self._reader: RewardReader | None = None
        self._logger = logger
        self._watch_seconds = watch_seconds
        self._tiles: list = []
        self._last_screenshot = None
        self._watch_until = 0.0
        self._reported = False

    def collect(self, screenshot: np.ndarray):
        if self._reported:
            return
        self._last_screenshot = screenshot
        try:  # Optional reward tracking must never interrupt farming.
            if self._reader is None:
                self._reader = RewardReader(self._set)
            tiles = self._reader.find_tiles(screenshot)
        except Exception:
            return

        def quality(tiles):
            return (
                len(tiles),
                sum(t.count is not None for t in tiles),
                sum(t.score + (t.count_confidence or 0) for t in tiles),
            )

        if quality(tiles) > quality(self._tiles):
            self._tiles = tiles

    def run_finished(self):
        if not self._reported and not self._watch_until:
            self._watch_until = time.monotonic() + self._watch_seconds
            self._report()

    def tick(self, screenshot: np.ndarray):
        if not self._watch_until:
            return
        if time.monotonic() >= self._watch_until:
            self.give_up()
            self._reported = True
            return
        self.collect(screenshot)
        self._report()

    def give_up(self):
        """End pending tracking and reset for the next battle."""
        screenshot, self._last_screenshot = self._last_screenshot, None
        waiting, self._watch_until = self._watch_until, 0.0
        self._tiles, self._reported = [], False
        if waiting:
            print("[WARNING] Couldn't read this run's rewards. This run was skipped.")
            if screenshot is not None:
                try:
                    path = self._logger.save_image(screenshot, subdir=self._set.log_subdir)
                    print(f"[WARNING] Result screen saved to {path}")
                except Exception:
                    pass

    def _report(self):
        if not self._tiles or any(t.count is None for t in self._tiles):
            return
        totals: dict[str, int] = {}
        for tile in self._tiles:
            totals[tile.key] = totals.get(tile.key, 0) + tile.count
        labels = self._set.labels
        print("Rewards of this run: " + ", ".join(f"{labels.get(k, k)} x{v}" for k, v in totals.items()))
        print(f"[REWARDS] {json.dumps(totals)}")
        self._watch_until = 0.0
        self.give_up()
        self._reported = True
