"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardTypes
from utilities.utilities import get_hand_cards


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    def pick_cards(self, *args, **kwargs) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()

        card_indices = []
        picked_cards = []
        for _ in range(7):
            # Extract the next index to click on
            next_index = self.identify_card_indices(hand_of_cards, picked_cards)
            card_indices.append(next_index)
            picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards, _ = self._update_indices_from_card_hand(hand_of_cards, [next_index])

        return picked_cards, card_indices

    def _update_indices_from_card_hand(self, original_house_of_cards: list[Card], indices: np.ndarray) -> list[Card]:
        """Given the selected indices, select the cards accounting for card shifts
        TODO: Poor quality code, and it should probably be done recursively to further improve the logic.

        Args:
            original_house_of_cards (list[Card]): List of the cards in hand before any is played.
            indices (np.ndarray): Original cards we want to play.
                                  The indices will have to be modified accounting for shifts and merges RECURSIVELY.

        """

        # Let's keep a copy of the original list of cards
        house_of_cards = deepcopy(original_house_of_cards)

        for i, idx in enumerate(indices):

            if isinstance(idx, Integral):
                # We're playing a card
                process_card_play(house_of_cards, idx, indices, i)

            elif isinstance(idx, (tuple, list)):
                # We're moving a card
                process_card_move(house_of_cards, idx[0], idx[1], indices, i)

            else:
                raise ValueError(f"Index {idx} is neither an integer nor a list/tuple!")

        # raise ValueError("Debugging")

        # Finally, return the new card array and indices modified
        return house_of_cards, indices

    @abc.abstractmethod
    def identify_card_indices(self, hand_of_cards: list[Card]) -> tuple[list[Card], np.ndarray]:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def identify_card_indices(self, hand_of_cards: list[Card]) -> np.ndarray:
        """Always get the rightmost 4 cards"""
        return np.array([7, 6, 5, 4])


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def identify_card_indices(cls, hand_of_cards: list[Card]) -> np.ndarray:
        """Apply the logic to extract the right indices.
        NOTE: Add attack-debuff cards too."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards][::-1])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards][::-1])
        # Keep track of all the indices
        all_indices = np.arange(len(hand_of_cards))

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        first_recovery_id = recovery_ids[[0]] if recovery_ids.size else np.array([])

        # STANCE CARDS
        # Initialization required
        first_stance_id = []
        if not first_recovery_id.size:
            # Extract the first stance index ONLY if we're not using a recovery
            stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
            first_stance_id = stance_ids[[0]] if stance_ids.size else []

        # ATATCK-DEBUFF CARDS
        att_debuff_ids = np.where(card_types == CardTypes.ATTACK_DEBUFF.value)[0]
        # Sort them based on card ranks
        att_debuff_ids = np.array(sorted(att_debuff_ids, key=lambda idx: card_ranks[idx], reverse=True))
        first_att_debuff_id = att_debuff_ids[[0]] if att_debuff_ids.size else []
        if len(first_att_debuff_id):
            # Remove the first one from the list, since we'll use the att_debuff_ids list later
            att_debuff_ids = np.delete(att_debuff_ids, 0)

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=True)

        # APPEND EVERYTHING together: Ultimates, 1 recovery, 1 stance, 1 attack-debuff, all attacks, all attack-debuffs, the rest
        selected_indices = np.hstack(
            (
                ult_ids,
                first_recovery_id,
                first_stance_id,
                first_att_debuff_id,
                attack_ids,
                att_debuff_ids,
            )
        )

        # Let's extract the DISABLED and GROUND cards too, to append them at the very end
        disabled_ids = np.where(card_types == CardTypes.DISABLED.value)[0]
        ground_ids = np.where(card_types == CardTypes.GROUND.value)[0]

        # print("disabled IDs:", disabled_ids)
        # print("selected IDs:", selected_indices)

        # Find the remaining cards (without considering the disabled/ground cards), and append them at the end
        remaining_indices = np.setdiff1d(all_indices, np.hstack((selected_indices, disabled_ids, ground_ids)))

        # print("remaining indices:", remaining_indices)

        # Concatenate the selected IDs, with the remaining IDs, and at the very end, the disabled IDs.
        final_indices = np.hstack((selected_indices, remaining_indices, disabled_ids))

        # Go back to the original indexing (0 the leftmost, 'n' the rightmost)
        final_indices = len(hand_of_cards) - 1 - final_indices

        # print("Final indices:", final_indices)
        # raise ValueError("Debugging")

        return final_indices.astype(int)


class Floor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for FLoor 4"""

    def pick_cards(self, phase) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()

        card_indices = []
        picked_cards = []
        for _ in range(7):
            # Extract the next index to click on
            next_index = self.identify_card_indices(hand_of_cards, picked_cards, phase=phase)
            card_indices.append(next_index)
            picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards, _ = self._update_indices_from_card_hand(hand_of_cards, [next_index])

        return picked_cards, card_indices

    def identify_card_indices(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int
    ) -> tuple[list[Card], np.ndarray]:
        """Extract the indices based on the list of cards and the current bird phase"""
        if phase == 1:
            card_indices = self.identify_card_indices_phase_1(hand_of_cards)
        elif phase == 2:
            card_indices = self.identify_card_indices_phase_2(hand_of_cards)
        elif phase == 3:
            card_indices = self.identify_card_indices_phase_3(hand_of_cards)
        elif phase == 4:
            card_indices = self.identify_card_indices_phase_4(hand_of_cards)

        return card_indices

    def identify_card_indices_phase_1(self, hand_of_cards: list[Card]) -> list[int | tuple[int]]:
        """The logic for phase 1... use the existing smarter strategy"""
        # SmarterBattleStrategy.identify_card_indices(hand_of_cards)

        # To start testing, let's just move cards
        return [[0, 7], [1, 6], [2, 5], [3, 4]]

    def identify_card_indices_phase_2(self, hand_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(hand_of_cards)

    def identify_card_indices_phase_3(self, hand_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(hand_of_cards)

    def identify_card_indices_phase_4(self, hand_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(hand_of_cards)
