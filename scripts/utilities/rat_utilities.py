import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.utilities import count_needle_image, crop_image, find

# ---------------------------------------------------------------------------
#  Stump door vision detection
# ---------------------------------------------------------------------------


def _score_door_darkness(screenshot: np.ndarray, roi_key: str) -> float:
    """Return a brightness score for a stump-door ROI (lower = darker = open door).

    Uses the 20th percentile of the grayscale channel after light
    Gaussian smoothing, which is robust to noise and small UI artifacts.
    """
    x1, y1, x2, y2 = Coordinates.get_coordinates(roi_key)
    region = crop_image(screenshot, (x1, y1), (x2, y2))
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return float(np.percentile(gray, 20))


def detect_stump_from_screen(
    screenshot: np.ndarray,
    abs_threshold: float = 120,
    margin: float = 15,
) -> int | None:
    """Detect which stump door is open (darkest region).

    Args:
        screenshot: Current game screenshot.
        abs_threshold: Max brightness score to consider "open door".
        margin: Min gap between best and second-best score for confidence.

    Returns the stump index (0=left, 1=center, 2=right) if confident,
    or None if confidence is insufficient or an error occurs.
    """
    door_keys = ("rat_door_left", "rat_door_center", "rat_door_right")
    labels = ("left", "center", "right")

    try:
        scores = [_score_door_darkness(screenshot, k) for k in door_keys]
    except Exception as e:
        print(f"[StumpVision] Error scoring door regions: {e}")
        return None

    sorted_scores = sorted(scores)
    best_idx = int(np.argmin(scores))
    best_score, second_best = sorted_scores[0], sorted_scores[1]

    confident = best_score < abs_threshold and (second_best - best_score) >= margin

    print(
        f"[StumpVision] scores L={scores[0]:.1f} C={scores[1]:.1f} R={scores[2]:.1f} "
        f"-> {'CONFIDENT' if confident else 'LOW-CONF'} best={labels[best_idx]}"
    )

    return best_idx if confident else None


# ---------------------------------------------------------------------------
#  Card identification helpers
# ---------------------------------------------------------------------------


def is_shock_card(card: Card):
    return find(vio.val_shock, card.card_image)


def is_bleed_card(card: Card):
    return find(vio.jorm_bleed, card.card_image)


def is_poison_card(card: Card):
    return find(vio.val_poison, card.card_image) or find(vio.val_ult, card.card_image)


def is_buff_removal(card: Card):
    return find(vio.lr_liz_aoe, card.card_image) or find(vio.jorm_buff_rem, card.card_image)


def count_rat_buffs(screenshot, threshold=0.6) -> int:
    return count_needle_image(vio.rat_buff, screenshot, threshold)
