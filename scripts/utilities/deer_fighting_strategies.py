import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import (
    capture_window,
    determine_card_merge,
    find,
    is_hard_hitting_snake_card,
    is_stance_cancel_card,
)


class DeerBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Deer"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        # if floor in {1, 3} and phase == 1:
        #     return self.floor_13_phase_1(hand_of_cards, picked_cards)

        # elif floor == 2:
        #     if phase == 1:
        #         return self.floor_2_phase_1(hand_of_cards, picked_cards)

        # elif floor == 3:
        #     if phase == 2:
        #         return self.floor_3_phase_2(hand_of_cards, picked_cards)
        #     elif phase == 3:
        #         return self.floor_3_phase_3(hand_of_cards, picked_cards)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
