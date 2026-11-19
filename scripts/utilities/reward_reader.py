"""Read the reward tiles (item icon + count in the bottom-right corner) from a result screenshot.

Used by the Indura and Guild Boss farmers. On the result screen each reward is a square tile. The same item
can appear on several tiles (e.g. three "Purple Crystals" tiles showing "2" each = 6 crystals); a tile without
a number holds 1.
"""

import os

import cv2
import numpy as np
from utilities.reward_sets import REWARDS_DIR, RewardSet
from utilities.vision import read_image

# Same font on every result screen
DIGITS_DIR = os.path.join(REWARDS_DIR, "digits")


def _whiteness(bgr: np.ndarray) -> np.ndarray:
    """Bright *and* unsaturated pixels. Counts are drawn white/light grey over coloured artwork,
    so this keeps the digits while the blue background and the blue corner ornament vanish."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    return np.clip(hsv[:, :, 2] * (1.0 - hsv[:, :, 1] / 90.0), 0, 255).astype(np.uint8)


def _iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    iw = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    ih = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = iw * ih
    return inter / float(aw * ah + bw * bh - inter)


class RewardTile:
    """One reward tile found on screen."""

    __slots__ = ("key", "score", "rect", "count")

    def __init__(self, key, score, rect):
        self.key = key
        self.score = score
        self.rect = rect  # full tile (x, y, w, h), frame included
        self.count: int | None = None  # None: the quantity could not be read


class RewardReader:
    """Match reward icons and quantity digits at their saved sizes."""

    _ICON_THRESHOLD = 0.75
    _GLYPH_THRESHOLD = 0.74

    def __init__(self, reward_set: RewardSet):
        self._set = reward_set
        self._icons: dict[str, tuple[np.ndarray, tuple[int, int, int, int]]] = {}
        for key in [k for k, _label in reward_set.items] + list(reward_set.ignored_items):
            img = read_image(os.path.join(reward_set.rewards_dir, f"{key}.png"))
            if img is not None:
                h, w = img.shape[:2]
                mx, my = int(w * reward_set.icon_margin), int(h * reward_set.icon_margin)
                self._icons[key] = (img[my : h - my, mx : w - mx], (w, h, mx, my))

        self._glyphs: dict[str, np.ndarray] = {}
        for name in "0123456789":
            g = read_image(os.path.join(DIGITS_DIR, f"{name}.png"), cv2.IMREAD_GRAYSCALE)
            if g is not None:
                self._glyphs[name] = g

    @property
    def available(self) -> bool:
        return bool(self._icons) and len(self._glyphs) == 10

    # ── tiles ────────────────────────────────────────────────────────────
    def _match_all(self, image: np.ndarray, key: str) -> list[RewardTile]:
        tpl, (w, h, mx, my) = self._icons[key]
        th, tw = tpl.shape[:2]
        if th > image.shape[0] or tw > image.shape[1]:
            return []
        res = cv2.matchTemplate(image, tpl, cv2.TM_CCOEFF_NORMED)
        found = []
        while True:
            _min, score, _minloc, (x, y) = cv2.minMaxLoc(res)
            if score < self._ICON_THRESHOLD or len(found) >= 12:
                break
            found.append(RewardTile(key, float(score), (x - mx, y - my, w, h)))
            x0, y0 = max(0, x - tw // 2), max(0, y - th // 2)
            res[y0 : y + th // 2 + 1, x0 : x + tw // 2 + 1] = -1
        return found

    def find_tiles(self, screenshot: np.ndarray) -> list[RewardTile]:
        """Every reward tile on the screenshot, with its corner count read."""
        if screenshot is None or not self.available:
            return []
        if screenshot.ndim == 3 and screenshot.shape[2] == 4:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

        candidates = [tile for key in self._icons for tile in self._match_all(screenshot, key)]
        tiles = []
        for tile in sorted(candidates, key=lambda t: t.score, reverse=True):
            if all(_iou(tile.rect, kept.rect) < 0.3 for kept in tiles):
                tiles.append(tile)

        tiles = [t for t in tiles if t.key not in self._set.ignored_items]
        for tile in tiles:
            self._read_tile_count(screenshot, tile)
        return sorted(tiles, key=lambda t: (t.rect[1] // max(t.rect[3], 1), t.rect[0]))

    # ── corner counts ────────────────────────────────────────────────────
    def _read_tile_count(self, screenshot: np.ndarray, tile: RewardTile) -> None:
        x, y, w, h = tile.rect
        # The count sits in the bottom-right corner (glyphs ~15% of the tile tall, ending at ~87%).
        top, bottom = int(y + h * 0.60), int(y + h * 0.96)
        left, right = int(x + w * 0.50), int(x + w * 1.0)
        if top < 0 or left < 0 or bottom > screenshot.shape[0] or right > screenshot.shape[1]:
            return
        if bottom - top < 6 or right - left < 6:
            return
        region = _whiteness(screenshot[top:bottom, left:right])
        tile.count = self._read_number(region)
        if tile.count is None:
            tile.count = 1  # The game omits the quantity for single items.
        elif tile.count == 0:
            tile.count = None

    def _read_number(self, region: np.ndarray) -> int | None:
        candidates = []  # (score, x, width, char)
        for char, tpl in self._glyphs.items():
            if tpl.shape[0] > region.shape[0] or tpl.shape[1] > region.shape[1]:
                continue
            res = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
            column_best = res.max(axis=0)
            for cx in np.where(column_best >= self._GLYPH_THRESHOLD)[0]:
                candidates.append((float(column_best[cx]), int(cx), tpl.shape[1], char))

        accepted = []
        for score, cx, width, char in sorted(candidates, reverse=True):
            overlaps = (
                min(cx + width, ax + aw) - max(cx, ax) > 0.25 * min(width, aw) for _s, ax, aw, _c in accepted
            )
            if not any(overlaps):
                accepted.append((score, cx, width, char))
        if not accepted:
            return None
        # A count is one contiguous group of glyphs; keep the group touching the strongest glyph.
        accepted.sort(key=lambda c: c[1])
        strongest = max(range(len(accepted)), key=lambda i: accepted[i][0])
        group = [accepted[strongest]]
        for direction in (-1, 1):
            i = strongest
            while 0 <= i + direction < len(accepted):
                prev, nxt = accepted[i], accepted[i + direction]
                gap = (nxt[1] - (prev[1] + prev[2])) if direction == 1 else (prev[1] - (nxt[1] + nxt[2]))
                if gap > 0.6 * max(prev[2], nxt[2]):
                    break
                group.append(nxt)
                i += direction
        group.sort(key=lambda c: c[1])
        digits = "".join(c for _s, _x, _w, c in group)
        return int(digits)
