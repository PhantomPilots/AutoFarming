from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import (
    IBattleStrategy,
    SmarterBattleStrategy,
    play_stance_card,
)
from utilities.logging_utils import LoggerWrapper
from utilities.rat_utilities import is_bleed_card, is_poison_card, is_shock_card
from utilities.utilities import (
    capture_window,
    count_immortality_buffs,
    determine_card_merge,
    find,
    is_amplify_card,
    is_hard_hitting_card,
    is_Thor_card,
)

logger = LoggerWrapper("RatFightingStrategies", log_file="rat_AI.log")


class RatFightingStrategy(IBattleStrategy):
    """The logic behind Rat. It's gonna be complex, brace yourself..."""

    def get_next_card_index(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        floor: int,
        phase: int,
        card_turn: int,
        current_stump: int,
        **kwargs
    ) -> int:
        """Distinguish between floors and phases"""

        if floor == 1 and phase == 1:
            return self.floor1_phase1(hand_of_cards, picked_cards, current_stump)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], current_stump: int):
        """Make sure we're always rotating the Rat... And *always* save one bleed card if possible"""
