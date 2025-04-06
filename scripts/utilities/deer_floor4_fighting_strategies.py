import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.deer_utilities import (
    count_cards,
    is_blue_card,
    is_Freyr_card,
    is_green_card,
    is_Hel_card,
    is_Jorm_card,
    is_red_card,
    is_Thor_card,
)
from utilities.fighting_strategies import (
    IBattleStrategy,
    SmarterBattleStrategy,
    play_stance_card,
)
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
)

logger = LoggerWrapper("BirdFloor4FightingStrategies", log_file="deer_floor4_AI.log")


class DeerFloor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for Floor 4"""

    # Keep track of the turn within a phase
    turn = 0

    # To keep track of what phases have been initialized
    _phase_initialized = set()

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(hand_of_cards, picked_cards)
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards)

        return card_index

    def _maybe_reset(self, phase_id: str):
        """Reset the turn counter if we're in a new phase"""
        if phase_id not in DeerFloor4BattleStrategy._phase_initialized:
            print("Resetting turn counter for phase", phase_id)
            DeerFloor4BattleStrategy.turn = 0
            DeerFloor4BattleStrategy._phase_initialized.add(phase_id)

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        # sourcery skip: merge-duplicate-blocks
        """The strategy is the following:

        Turn 1 - Freyr Cleave > Hel Att > Jorm buff removal > Thor Crit chance

        (This where the Strat deviates depending on the rng you get)

        Turn 2 (With an extra thor card) - Move thor card 2 times and use her lvl 2 (she must have 4 ult gauge )hel card once.

        Turn 2 (without a extra thor card) - Attack with thor and move hel card 3 times

        Turn 3 - (With extra thor card) - move thor once and use her card to kill, then move hel or freyr card 2 times (u want hel and freyr to be close to their ults. ideally u want Hel to have 3 ult points)
        """
        self._maybe_reset("phase_1")  # Not needed, but whatever

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])

        if DeerFloor4BattleStrategy.turn == 0:
            return self._phase1_turn0(hand_of_cards)

        elif DeerFloor4BattleStrategy.turn == 1:
            if count_cards(hand_of_cards, is_Thor_card) >= 2:
                # If we have two Thor cards...
                if IBattleStrategy.card_turn <= 1:
                    # Move a Thor card to the left
                    return [thor_cards[0], thor_cards[0] + 1]
                elif IBattleStrategy.card_turn == 2:
                    # Use a Hel card, we're guaranteed to have one
                    return hel_cards[-1]
                else:
                    # Play Thor card
                    DeerFloor4BattleStrategy.turn += 1
                    return thor_cards[-1]
            else:
                # If not...
                if IBattleStrategy.card_turn <= 2:
                    return [hel_cards[0], hel_cards[0] + 1]
                # Play Thor card
                DeerFloor4BattleStrategy.turn += 1
                return thor_cards[-1]

        elif DeerFloor4BattleStrategy.turn == 2:
            if len(thor_cards) > 0:
                if IBattleStrategy.card_turn == 0:
                    # Move Thor card first to remove freeze
                    return [thor_cards[0], thor_cards[0] + 1]
                elif IBattleStrategy.card_turn <= 2:
                    return [hel_cards[0], hel_cards[0] + 1]
                else:
                    return thor_cards[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _phase1_turn0(self, hand_of_cards):
        """The first turn of the first phase"""
        # First, try to play a Freyr stance card
        freyr_stance = np.where([find(vio.freyr_1, card.card_image) for card in hand_of_cards])[0]
        if len(freyr_stance) > 0:
            return freyr_stance[-1]

        # Then, try to play a Hel card if we haven't played one yet
        hel_cards = np.where([find(vio.hel_1, card.card_image) for card in hand_of_cards])[0]
        if len(hel_cards) > 0:
            return hel_cards[-1]

        # Then, Jorm's buff removal
        jorm_card = np.where([find(vio.jorm_2, card.card_image) for card in hand_of_cards])[0]
        if len(jorm_card) > 0:
            return jorm_card[-1]

        # Finish the turn with a Thor card
        thor_cards = np.where([find(vio.thor_1, card.card_image) for card in hand_of_cards])[0]
        DeerFloor4BattleStrategy.turn += 1
        return thor_cards[-1]

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_2")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        freyr_cards = sorted(
            np.where([is_Freyr_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        jorm_cards = sorted(
            np.where([is_Jorm_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_cards = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        if DeerFloor4BattleStrategy.turn == 0:
            if IBattleStrategy.card_turn <= 1:
                num_blue_cards = count_cards(hand_of_cards, is_blue_card) + count_cards(picked_cards, is_blue_card)
                num_red_cards = count_cards(hand_of_cards, is_red_card) + count_cards(picked_cards, is_red_card)
                if num_blue_cards >= 2 or num_red_cards >= 2:
                    cards_to_pick = np.where(
                        [is_red_card(card) if num_red_cards >= 2 else is_blue_card(card) for card in hand_of_cards]
                    )[0]
                    return cards_to_pick[-1]
            elif IBattleStrategy.card_turn >= 2:
                if IBattleStrategy.card_turn == 3:
                    # Go to next turn
                    DeerFloor4BattleStrategy.turn += 1
                return [hel_cards[0], hel_cards[0] + 1]

        elif DeerFloor4BattleStrategy.turn == 1:
            if IBattleStrategy.card_turn <= 1:
                # Play a green card, but prioritize the ult if we have it
                hel_ult_id = np.where([find(vio.hel_ult, card.card_image) for card in hand_of_cards])[0]
                return hel_ult_id[0] if len(hel_ult_id) > 0 else green_cards[-1]
            else:
                if IBattleStrategy.card_turn == 3:
                    # Go to next turn after this one
                    DeerFloor4BattleStrategy.turn += 1
                if len(freyr_cards) > 0:
                    # Try to get Freyr's ult
                    return [freyr_cards[0], freyr_cards[0] + 1]
                # Else just move an arbitrary card
                return [-1, -2]

        elif DeerFloor4BattleStrategy.turn == 2:
            raise ValueError

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_3")

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_4")

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
