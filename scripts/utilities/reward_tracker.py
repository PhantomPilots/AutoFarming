"""Report rewards from one result screenshot.

Farmers check is_victory_result, guard against handling that result twice, then call
read_and_report before navigating. Rearm the guard for a new battle, not merely a click.
"""

import json

import numpy as np
import utilities.vision_images as vio
from utilities.reward_reader import RewardReader
from utilities.reward_sets import RewardSet
from utilities.utilities import find


VICTORY_THRESHOLD = 0.6


def is_victory_result(screenshot: np.ndarray) -> bool:
    """Both result markers must be visible in this screenshot."""
    return find(vio.victory, screenshot, threshold=VICTORY_THRESHOLD) and find(vio.ok_main_button, screenshot)


class RewardTracker:
    """Read once and report whatever rewards are recognized, without delaying navigation."""

    def __init__(self, reward_set: RewardSet):
        self._set = reward_set
        self._reader: RewardReader | None = None

    def read_and_report(self, screenshot: np.ndarray) -> None:
        try:  # Optional reward tracking must never interrupt farming.
            if self._reader is None:
                self._reader = RewardReader(self._set)
            tiles = self._reader.find_tiles(screenshot)
        except Exception:
            print("[WARNING] Couldn't read this run's rewards. Continuing.")
            return

        totals: dict[str, int] = {}
        for tile in tiles:
            if tile.count is not None and tile.count > 0:
                totals[tile.key] = totals.get(tile.key, 0) + tile.count
        if not totals:
            print("[WARNING] Couldn't read this run's rewards. Continuing.")
            return
        labels = self._set.labels
        print("Rewards of this run: " + ", ".join(f"{labels.get(k, k)} x{v}" for k, v in totals.items()))
        print(f"[REWARDS] {json.dumps(totals)}")
