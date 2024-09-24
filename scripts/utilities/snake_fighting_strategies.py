import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
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
    is_hard_hitting_snake_card,
    is_Meli_card,
    is_stance_cancel_card,
    is_Thor_card,
)


class SnakeBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Snake"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if floor in {1, 3} and phase == 1:
            return self.floor_13_phase_1(hand_of_cards, picked_cards)

        elif floor == 2:
            if phase == 1:
                return self.floor_2_phase_1(hand_of_cards, picked_cards)

        elif floor == 3:
            if phase == 2:
                return self.floor_3_phase_2(hand_of_cards, picked_cards)
            elif phase == 3:
                return self.floor_3_phase_3(hand_of_cards, picked_cards)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_13_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Use all high-hitting cards"""

        ham_ids = np.where([is_hard_hitting_snake_card(card) for card in hand_of_cards])[0]
        if len(ham_ids):
            return ham_ids[-1]

        # Default to Smarter strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_2_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Strategy for Phase 1 of Floor 2: We cannot use Liz's AOE card until the very end"""

        # If it's the last card to play, use Liz's AOE:
        if IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1:
            print("Can we use Liz's AOE card?")
            liz_aoe_ids = np.where([find(vio.lr_liz_aoe, card.card_image) for card in hand_of_cards])[0]
            if len(liz_aoe_ids):
                return liz_aoe_ids[-1]

        # Default strategy: Simply use HAM cards to one-turn it
        ham_ids = np.where(
            [
                find(vio.freyja_st, card.card_image)
                or find(vio.mael_aoe, card.card_image)
                or find(vio.mael_st, card.card_image)
                for card in hand_of_cards
            ]
        )[0]
        if len(ham_ids):
            return ham_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_3_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        # sourcery skip: for-index-replacement
        """Use stance card at the very end of each turn?"""

        played_freyja_ids = np.where(
            [find(vio.freyja_aoe, card.card_image) or find(vio.freyja_st, card.card_image) for card in picked_cards]
        )[0]

        # Play a Freyja card to avoid getting darkness!
        freyja_aoe_ids = np.where([find(vio.freyja_aoe, card.card_image) for card in hand_of_cards])[0]
        if not len(played_freyja_ids):
            if len(freyja_aoe_ids):
                return freyja_aoe_ids[-1]
            freyja_st_ids = np.where([find(vio.freyja_st, card.card_image) for card in hand_of_cards])[0]
            if len(freyja_st_ids):
                return freyja_st_ids[-1]

        # elif not len(played_freyja_ids) and len(stance_ids) and not len(played_stance_ids):
        #     # Arbitrary logic: If we're not playing a Freyja card, play a stance cancel
        #     return stance_ids[-1]

        # Set all stance IDs to DISABLED, and run the SmarterBattleStrategy
        for i in range(len(hand_of_cards)):
            if is_stance_cancel_card(hand_of_cards[i]):
                hand_of_cards[i].card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_3_phase_3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """If we see an enemy stance, use a stance cancel"""

        screenshot, _ = capture_window()

        if find(vio.snake_stance, screenshot, threshold=0.8):
            print("The snake has a stance! Can we cancel it?")

            # Cancel the stance and also play a buff if possible
            buff_ids = np.where([card.card_type == CardTypes.BUFF for card in hand_of_cards])[0]
            played_buff_ids = np.where([card.card_type == CardTypes.BUFF for card in picked_cards])[0]
            stance_ids = np.where([is_stance_cancel_card(card) for card in hand_of_cards])[0]
            played_stance_ids = np.where([is_stance_cancel_card(card) for card in picked_cards])[0]

            if len(stance_ids) and not len(played_stance_ids):
                return stance_ids[-1]

            if len(buff_ids) and not len(played_buff_ids):
                return buff_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
