import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    count_immortality_buffs,
    determine_card_merge,
    display_image,
    find,
    get_hand_cards,
    is_amplify_card,
    is_ground_card,
    is_hard_hitting_card,
    is_Meli_card,
    is_Thor_card,
)


class SnakeBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Snake"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], **kwargs) -> int:
        """Extract the next card index based on the hand and picked cards information"""
        return -1
