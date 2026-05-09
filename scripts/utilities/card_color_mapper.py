from collections import defaultdict

import numpy as np
from utilities.card_data import Card, CardColors, CardTypes
from utilities.pattern_match_strategies import TemplateMatchingStrategy


class CardColorMapper:
    """Farmer-agnostic runtime card-color mapper.

    Calibrates from the opening hand + pre-fight unit colors,
    then matches live cards against stored templates.

    Calibration contract (inferred from hand length):
      - 8 cards: 4 front-line units x 2 cards each, all slots deterministic.
      - 7 cards: 3 front-line units x 2 cards (slots [1..6]).
        Slot [0] is ignored (wildcard).
    """

    def __init__(self):
        self._templates: dict[CardColors, list[np.ndarray]] = defaultdict(list)
        self._calibrated = False

    # -- Calibration --

    def calibrate(self, hand: list[Card], unit_colors: list[CardColors]):
        """Single calibration entrypoint. Layout is inferred from len(hand)."""
        n = len(hand)
        if n == 8:
            self._calibrate_8(hand, unit_colors)
        elif n == 7:
            self._calibrate_7(hand, unit_colors)
        else:
            raise ValueError(f"[CardColorMapper] Unsupported hand length {n}. Expected 7 or 8.")

    def _calibrate_8(self, hand: list[Card], unit_colors: list[CardColors]):
        """4 units x 2 cards = 8 deterministic slots."""
        if len(unit_colors) < 4:
            raise ValueError(f"[CardColorMapper] 8-card hand requires >= 4 unit colors, got {len(unit_colors)}.")
        self._validate_slot_images(hand, range(8))
        self._templates.clear()
        for unit_idx in range(4):
            color = unit_colors[unit_idx]
            self._templates[color].append(hand[unit_idx * 2].card_image)
            self._templates[color].append(hand[unit_idx * 2 + 1].card_image)
        self._calibrated = True
        print(f"[CardColorMapper] Calibrated (8-card): {[c.name for c in self._templates]}")

    def _calibrate_7(self, hand: list[Card], unit_colors: list[CardColors]):
        """3 front units x 2 cards (slots [1..6]). Slot [0] is ignored (wildcard)."""
        if len(unit_colors) < 3:
            raise ValueError(f"[CardColorMapper] 7-card hand requires >= 3 unit colors, got {len(unit_colors)}.")
        self._validate_slot_images(hand, range(1, 7))
        self._templates.clear()
        for unit_idx in range(3):
            color = unit_colors[unit_idx]
            self._templates[color].append(hand[1 + unit_idx * 2].card_image)
            self._templates[color].append(hand[1 + unit_idx * 2 + 1].card_image)
        self._calibrated = True
        print(f"[CardColorMapper] Calibrated (7-card): {[c.name for c in self._templates]}")

    # -- Lookup APIs --

    def get_card_color(self, card: Card) -> CardColors:
        """Return the color of a card via template matching."""
        if not self._calibrated or card.card_type == CardTypes.DISABLED or card.card_image is None:
            return CardColors.NONE
        return self._match_card_image(card.card_image)

    def get_color_card_ids(self, hand: list[Card], color: CardColors) -> list[int]:
        """Indices of non-disabled cards matching *color*, sorted by rank ascending."""
        ids = [
            i
            for i, card in enumerate(hand)
            if card.card_type != CardTypes.DISABLED and self.get_card_color(card) == color
        ]
        ids.sort(key=lambda i: hand[i].card_rank.value)
        return ids

    def count_color_cards(self, cards: list[Card], color: CardColors) -> int:
        return sum(1 for c in cards if self.get_card_color(c) == color)

    # -- Internal --

    @staticmethod
    def _validate_slot_images(hand: list[Card], required_slots):
        missing = [i for i in required_slots if hand[i].card_image is None]
        if missing:
            raise ValueError(f"[CardColorMapper] Missing card images at required slots: {missing}")

    def _match_card_image(self, card_image: np.ndarray) -> CardColors:
        if card_image is None:
            return CardColors.NONE
        for color, templates in self._templates.items():
            for tmpl in templates:
                rect = TemplateMatchingStrategy.find(card_image, tmpl)
                if rect is not None and rect.size > 0:
                    return color
        return CardColors.NONE

    # -- Lifecycle --

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def reset(self):
        self._templates.clear()
        self._calibrated = False
