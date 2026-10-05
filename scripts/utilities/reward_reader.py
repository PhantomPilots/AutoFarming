"""Read the reward tiles (item icon + count in the bottom-right corner) from a result screenshot.

On the result screens each reward is a square tile. The same item can appear on several tiles
(e.g. three "Purple Crystals" tiles showing "2" each = 6 crystals); a tile without a number holds 1.
"""

import os
from dataclasses import dataclass, field

import cv2
import numpy as np

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
INDURA_REWARDS_DIR = os.path.join(IMAGES_DIR, "demons", "rewards")
DIGITS_DIR = os.path.join(INDURA_REWARDS_DIR, "digits")

# (key, display label). The key is also the template filename in images/demons/rewards/.
INDURA_ITEMS = (
    ("super_awakening_coin_fragment", "Super Awakening Coin Fragment"),
    ("chaos_fragment", "Chaos Fragment"),
    ("anvil", "Anvil"),
    ("brilliant_component", "Brilliant Component"),
    ("dark_eraser", '"Dark Eraser"'),
    ("indura_of_retribution", "Indura of Retribution"),
    ("death_match_reward", "Death Match Reward"),
    ("scroll", "Scroll"),
    ("potion", "Potion"),
)

# Tiles that are recognized (so they can't be mistaken for another item) but never reported.
INDURA_IGNORED_ITEMS = ("bingo_ticket",)

# Quantities one tile can hold, from Indura's Bronze/Silver/Gold box drop tables (1 = no number drawn).
# Restricting the read to these values makes a blurry corner digit impossible to misread.
# Items missing here are read freely.
INDURA_TILE_COUNTS = {
    "super_awakening_coin_fragment": (4, 5),
    "chaos_fragment": (2, 4),
    "anvil": (5,),
    "brilliant_component": (1, 2),
    "dark_eraser": (1,),
    "indura_of_retribution": (1,),
}


@dataclass(frozen=True)
class RewardSet:
    """The reward tiles a farmer can read: templates, labels and the quantities a tile can show."""

    title: str  # shown in the GUI rewards panel
    rewards_dir: str  # holds '<key>.png' for every item
    items: tuple  # (key, display label)
    log_subdir: str  # logs/<log_subdir>/ keeps the reward rows and the unreadable result screens
    tile_counts: dict = field(default_factory=dict)
    ignored_items: tuple = ()
    show_labels: bool = True  # False: the GUI panel shows only the icons and counts (labels stay as tooltips)
    # Share of each template side dropped before matching (rarity frame, corner count, corner badge)
    icon_margin: float = 0.14

    @property
    def labels(self) -> dict:
        return dict(self.items)


INDURA_REWARDS = RewardSet(
    title="Indura Rewards",
    rewards_dir=INDURA_REWARDS_DIR,
    items=INDURA_ITEMS,
    log_subdir="demon_rewards",
    tile_counts=INDURA_TILE_COUNTS,
    ignored_items=INDURA_IGNORED_ITEMS,
    show_labels=False,
)

# Guild Boss (Belgius) drop table. Templates are cut from the in-game "Reward" list, whose tiles carry a
# badge in the top-right corner and the count in the bottom-right one: a wider margin keeps only the art.
GUILD_BOSS_REWARDS = RewardSet(
    title="Guild Boss Rewards",
    rewards_dir=os.path.join(IMAGES_DIR, "guild_boss", "rewards"),
    items=(
        ("belgius_artifact_card", "Demonic Beast Belgius (Artifact Card)"),
        ("awakening_stone", "Awakening Stone"),
        ("anvil", "Anvil"),
        ("treasure_chest", "Treasure Chest"),
        ("enhance_stone", "Enhance Stone"),
    ),
    log_subdir="guild_boss_rewards",
    tile_counts={
        "belgius_artifact_card": (1,),
        "awakening_stone": (2,),
        "anvil": (10,),
        "treasure_chest": (1,),
        "enhance_stone": (80,),
    },
    icon_margin=0.22,
)


def _read(path: str, flags=cv2.IMREAD_COLOR) -> np.ndarray | None:
    try:
        with open(path, "rb") as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        return cv2.imdecode(data, flags) if data.size else None
    except (OSError, cv2.error):
        return None


def _resize(img: np.ndarray, scale: float) -> np.ndarray:
    h, w = img.shape[:2]
    size = (max(3, round(w * scale)), max(3, round(h * scale)))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)


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

    __slots__ = ("key", "score", "rect", "count", "count_confidence")

    def __init__(self, key, score, rect):
        self.key = key
        self.score = score
        self.rect = rect  # full tile (x, y, w, h), frame included
        self.count = 1
        self.count_confidence = None  # None: no number on the tile


class RewardReader:
    """Multi-scale template matching for the tiles, glyph template matching for the corner counts.

    Tile templates are 74x74 px (scale 1.0). On the 538x921 bot window a tile is ~60 px (scale ~0.8).
    """

    _SCALES = tuple(float(s) for s in np.round(np.arange(0.40, 1.31, 0.05), 2))
    _TILE = 74
    _ICON_THRESHOLD = 0.75
    _MIN_ICON_SIZE = 14
    # Digit templates (images/demons/rewards/digits) are whiteness maps cut from ~60 px tiles.
    # "2" and "5" come from real result screens; the others are the same font, resized to match.
    _DIGIT_TILE = 60
    # Real counts score 0.78-1.0; tiles without a number (corner ornament only) stay below ~0.7.
    _GLYPH_THRESHOLD = 0.74

    def __init__(self, reward_set: RewardSet):
        self._set = reward_set
        self._icons: dict[str, np.ndarray] = {}
        for key in [k for k, _label in reward_set.items] + list(reward_set.ignored_items):
            img = _read(os.path.join(reward_set.rewards_dir, f"{key}.png"))
            if img is not None:
                img = cv2.resize(img, (self._TILE, self._TILE), interpolation=cv2.INTER_AREA)
                m = int(self._TILE * reward_set.icon_margin)
                self._icons[key] = img[m : self._TILE - m, m : self._TILE - m]

        self._glyphs: dict[str, np.ndarray] = {}
        for name in "0123456789":
            g = _read(os.path.join(DIGITS_DIR, f"{name}.png"), cv2.IMREAD_GRAYSCALE)
            if g is not None:
                self._glyphs[name] = g
        self._scale: float | None = None

    @property
    def available(self) -> bool:
        return bool(self._icons) and len(self._glyphs) == 10

    # ── tiles ────────────────────────────────────────────────────────────
    def _match_all(self, image: np.ndarray, key: str, scale: float, threshold: float) -> list[RewardTile]:
        tpl = _resize(self._icons[key], scale)
        th, tw = tpl.shape[:2]
        # Tiny templates match noise everywhere and would win the "most tiles" ranking of _scan
        if min(th, tw) < self._MIN_ICON_SIZE or th >= image.shape[0] or tw >= image.shape[1]:
            return []
        res = cv2.matchTemplate(image, tpl, cv2.TM_CCOEFF_NORMED)
        tile = self._TILE * scale
        pad = (tile - tw) / 2
        found = []
        while True:
            _min, score, _minloc, (x, y) = cv2.minMaxLoc(res)
            if score < threshold or len(found) >= 12:
                break
            found.append(RewardTile(key, float(score), (int(x - pad), int(y - pad), int(tile), int(tile))))
            # Suppress this peak so the next iteration finds another tile of the same item
            x0, y0 = max(0, x - tw // 2), max(0, y - th // 2)
            res[y0 : y + th // 2 + 1, x0 : x + tw // 2 + 1] = -1
        return found

    def _scan(self, image: np.ndarray, scales, threshold: float) -> tuple[float | None, list[RewardTile]]:
        """Return the scale whose matches are the most numerous/confident, with non-overlapping tiles."""
        best_scale, best_tiles, best_key = None, [], (0, 0.0)
        for scale in scales:
            candidates = []
            for key in self._icons:
                candidates += self._match_all(image, key, scale, threshold)
            tiles = []
            for tile in sorted(candidates, key=lambda t: t.score, reverse=True):
                if all(_iou(tile.rect, kept.rect) < 0.3 for kept in tiles):
                    tiles.append(tile)
            rank = (len(tiles), sum(t.score for t in tiles))
            if rank > best_key:
                best_scale, best_tiles, best_key = scale, tiles, rank
        return best_scale, best_tiles

    def find_tiles(self, screenshot: np.ndarray) -> list[RewardTile]:
        """Every reward tile on the screenshot, with its corner count read."""
        if screenshot is None or not self.available:
            return []
        if screenshot.ndim == 3 and screenshot.shape[2] == 4:
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

        if self._scale is None:
            # Coarse pass on a half-size image, then refine around the winner at full size.
            half = cv2.resize(screenshot, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            coarse, _tiles = self._scan(half, [s * 0.5 for s in self._SCALES], self._ICON_THRESHOLD - 0.1)
            if coarse is None:
                return []
            center = coarse * 2
        else:
            center = self._scale
        scales = [s for s in self._SCALES if abs(s - center) <= 0.051]
        scale, tiles = self._scan(screenshot, scales, self._ICON_THRESHOLD)
        if not tiles:
            return []
        self._scale = scale

        tiles = [t for t in tiles if t.key not in self._set.ignored_items]
        for tile in tiles:
            self._read_tile_count(screenshot, tile)
        return sorted(tiles, key=lambda t: (t.rect[1] // max(t.rect[3], 1), t.rect[0]))

    def read(self, screenshot: np.ndarray) -> dict[str, int]:
        """Return {item_key: total count}, summing every tile of the same item."""
        totals: dict[str, int] = {}
        for tile in self.find_tiles(screenshot):
            totals[tile.key] = totals.get(tile.key, 0) + tile.count
        return totals

    # ── corner counts ────────────────────────────────────────────────────
    def _read_tile_count(self, screenshot: np.ndarray, tile: RewardTile) -> None:
        x, y, w, h = tile.rect
        # The count sits in the bottom-right corner (glyphs ~15% of the tile tall, ending at ~87%).
        top, bottom = int(y + h * 0.60), int(y + h * 0.96)
        left, right = int(x + w * 0.50), int(x + w * 1.0)
        top, left = max(top, 0), max(left, 0)
        bottom, right = min(bottom, screenshot.shape[0]), min(right, screenshot.shape[1])
        if bottom - top < 6 or right - left < 6:
            return
        region = _whiteness(screenshot[top:bottom, left:right])
        scale = h / self._DIGIT_TILE
        allowed = self._set.tile_counts.get(tile.key)
        if allowed is None:
            read = self._read_number(region, scale)
            if read is not None:
                tile.count, tile.count_confidence = read
            return
        if len(allowed) == 1:
            tile.count = allowed[0]
            return
        # Score only the digits this item can show, and pick the best one.
        scored = [(self._digit_score(region, str(v), scale), v) for v in allowed if v != 1]
        best_score, best_value = max(scored)
        if best_score >= self._GLYPH_THRESHOLD or 1 not in allowed:
            tile.count, tile.count_confidence = best_value, best_score
        else:
            tile.count = 1

    def _digit_score(self, region: np.ndarray, digit: str, scale: float) -> float:
        best = -1.0
        glyph = self._glyphs.get(digit)
        if glyph is None:
            return best
        for factor in (0.95, 1.0, 1.05):
            tpl = _resize(glyph, scale * factor)
            if tpl.shape[0] > region.shape[0] or tpl.shape[1] > region.shape[1]:
                continue
            best = max(best, float(cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED).max()))
        return best

    def _read_number(self, region: np.ndarray, scale: float) -> tuple[int, float] | None:
        candidates = []  # (score, x, width, char)
        for factor in (0.95, 1.0, 1.05):
            for char, glyph in self._glyphs.items():
                tpl = _resize(glyph, scale * factor)
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
        return int(digits), float(np.mean([s for s, _x, _w, _c in group]))
