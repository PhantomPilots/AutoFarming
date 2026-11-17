"""Read result screens and report one '[REWARDS]' line per successfully read run."""

import json
import time

import numpy as np
from utilities.logging_utils import LoggerWrapper
from utilities.reward_reader import RewardReader
from utilities.reward_sets import RewardSet


class RewardTracker:
    """Keep the best reading until a clear is counted, retrying unclear result screens."""

    def __init__(self, reward_set: RewardSet, logger: LoggerWrapper, watch_seconds: float = 5):
        self._set = reward_set
        self._reader: RewardReader | None = None
        self._logger = logger
        self._watch_seconds = watch_seconds
        self.give_up()

    def collect(self, screenshot: np.ndarray):
        if self._reading_finished:
            return
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

    def read_before_continue(self, screenshot: np.ndarray) -> bool:
        """Read an eligible reward screen; return whether navigation may continue."""
        if self._reading_finished:
            return True
        if self._deadline is None:
            self._deadline = time.monotonic() + self._watch_seconds
        if time.monotonic() < self._deadline:
            self.collect(screenshot)
        if not self.read_complete and time.monotonic() < self._deadline:
            return False
        self._reading_finished = True
        if self.read_complete:
            self._report()
        else:
            self._tiles = []
            print("[WARNING] Couldn't read this run's rewards. Continuing.")
            try:
                path = self._logger.save_image(screenshot, subdir=self._set.log_subdir)
                print(f"[WARNING] Result screen saved to {path}")
            except Exception:
                pass
        return True

    def run_finished(self):
        """Confirm the completed run, reporting a usable reading once it exists."""
        self._run_confirmed = True
        self._report()

    def give_up(self):
        """Reset the result lifecycle while keeping cached image templates."""
        self._tiles = []
        self._deadline = None
        self._reading_finished = False
        self._run_confirmed = False
        self._reported = False

    @property
    def read_complete(self) -> bool:
        return bool(self._tiles) and all(tile.count is not None for tile in self._tiles)

    def _report(self):
        if self._reported or not self._run_confirmed or not self.read_complete:
            return
        totals: dict[str, int] = {}
        for tile in self._tiles:
            totals[tile.key] = totals.get(tile.key, 0) + tile.count
        labels = self._set.labels
        print("Rewards of this run: " + ", ".join(f"{labels.get(k, k)} x{v}" for k, v in totals.items()))
        print(f"[REWARDS] {json.dumps(totals)}")
        self._tiles = []
        self._reading_finished = True
        self._reported = True
