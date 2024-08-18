"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy

import numpy as np
from termcolor import cprint
from utilities.battle_utilities import determine_card_merge, handle_card_merges
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import get_hand_cards, increment_in_place


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    def pick_cards(self, *args, **kwargs) -> tuple[list[Card], np.ndarray]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        list_of_cards: list[Card] = get_hand_cards()

        # Extract the indices
        card_indices = self.identify_card_indices(list_of_cards)

        return self._update_indices_from_card_hand(list_of_cards, card_indices)

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

            if not isinstance(idx, (tuple, list)):
                # We're playing a card
                self.process_card_play(house_of_cards, idx, indices, i)

            else:
                # We're moving a card
                self.process_card_move(house_of_cards, idx[0], idx[1], indices, i)

        # raise ValueError("Debugging")

        # Finally, return the selected cards from the original house of cards!
        return original_house_of_cards, indices

    def process_card_move(
        self, house_of_cards: list[Card], origin_idx: int, target_idx: int, indices: list[int], i: int
    ):
        """If we're moving a card, how does the whole hand change?"""

        if determine_card_merge(house_of_cards[origin_idx], house_of_cards[target_idx]):
            # First, increase the rank of the target card
            target_rank = house_of_cards[target_idx].card_rank
            house_of_cards[target_idx].card_rank = CardRanks(target_rank.value + 1)
            # And let's remove the origin card. Otherwise, we don't remove it
            house_of_cards.pop(origin_idx)
            # Let's insert a dummy card
            house_of_cards.insert(0, None)
            # And increase the indices
            increment_in_place(indices[i + 1 :], thresh=origin_idx, condition=lambda a, b: a < b)
        else:
            # The case in which we move without having a card merge
            cprint(f"We're moving a card from {origin_idx} to {target_idx}, but it's not generating a merge!", "yellow")
            # The two lines below should only decrement `indices` of all those cards between the origin position (excluded) and the target position (included)
            increment_in_place(indices[i + 1 :], thresh=target_idx, condition=lambda a, b: a <= b, operator=-1)
            increment_in_place(indices[i + 1 :], thresh=origin_idx, condition=lambda a, b: a <= b, operator=+1)
            # Now rearrange the house of cards
            card = house_of_cards.pop(origin_idx)
            house_of_cards.insert(target_idx, card)

        # Handle card merges due to the deletion of `idx`
        handle_card_merges(house_of_cards, origin_idx, origin_idx + 1, indices[i + 1 :], threshold=origin_idx)

        # Handle  card merges on the target side. NOTE: The masks here change, they depend on the target index instead!
        handle_card_merges(house_of_cards, target_idx - 1, target_idx, indices[i + 1 :], threshold=target_idx)
        handle_card_merges(house_of_cards, target_idx, target_idx + 1, indices[i + 1 :], threshold=target_idx + 1)

    def process_card_play(self, house_of_cards: list[Card], idx: int, indices: list[int], i: int):
        """If we're playing a card, how does the whole hand change?"""

        # Let's shift the indices vector first
        increment_in_place(indices[i + 1 :], thresh=idx, condition=lambda a, b: a < b, operator=1)

        # Since we assume we play a card now, let's remove it from the house of cards
        house_of_cards.pop(idx)
        # Let's insert a dummy card
        house_of_cards.insert(0, None)

        # print(f"New indices after playing {idx}:", indices)

        # If we're not at the beginning or end of the list, let's handle the card merges
        if idx > 0 and idx < len(house_of_cards) - 1:
            handle_card_merges(
                house_of_cards,
                left_card_idx=idx,
                right_card_idx=idx + 1,
                indices_to_update=indices[i + 1 :],
                threshold=idx,
            )

    @abc.abstractmethod
    def identify_card_indices(self, list_of_cards: list[Card]) -> tuple[list[Card], np.ndarray]:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def identify_card_indices(self, list_of_cards: list[Card]) -> np.ndarray:
        """Always get the rightmost 4 cards"""
        return np.array([7, 6, 5, 4])


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def identify_card_indices(cls, list_of_cards: list[Card]) -> np.ndarray:
        """Apply the logic to extract the right indices.
        NOTE: Add attack-debuff cards too."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in list_of_cards][::-1])
        card_ranks = np.array([card.card_rank.value for card in list_of_cards][::-1])
        # Keep track of all the indices
        all_indices = np.arange(len(list_of_cards))

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
        final_indices = len(list_of_cards) - 1 - final_indices

        # print("Final indices:", final_indices)
        # raise ValueError("Debugging")

        return final_indices.astype(int)


class Floor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for FLoor 4"""

    def pick_cards(self, phase: int) -> tuple[list[Card], np.ndarray]:
        """We need a custom version that accepts the phase it is in as a parameter"""

        # Extract the cards
        list_of_cards: list[Card] = get_hand_cards()

        card_indices = self.identify_card_indices(list_of_cards, phase)

        return self._update_indices_from_card_hand(list_of_cards, card_indices)

    def identify_card_indices(self, list_of_cards: list[Card], phase: int) -> tuple[list[Card], np.ndarray]:
        """Extract the indices based on the list of cards and the current bird phase"""
        if phase == 1:
            card_indices = self.identify_card_indices_phase_1(list_of_cards)
        elif phase == 2:
            card_indices = self.identify_card_indices_phase_2(list_of_cards)
        elif phase == 3:
            card_indices = self.identify_card_indices_phase_3(list_of_cards)
        elif phase == 4:
            card_indices = self.identify_card_indices_phase_4(list_of_cards)

        return card_indices

    def identify_card_indices_phase_1(self, list_of_cards: list[Card]) -> list[int | tuple[int]]:
        """The logic for phase 1... use the existing smarter strategy"""
        # SmarterBattleStrategy.identify_card_indices(list_of_cards)

        # To start testing, let's just move cards
        return [(0, 7), (1, 6), (2, 5), (3, 4)]

    def identify_card_indices_phase_2(self, list_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(list_of_cards)

    def identify_card_indices_phase_3(self, list_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(list_of_cards)

    def identify_card_indices_phase_4(self, list_of_cards: list[Card]):
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.identify_card_indices(list_of_cards)
