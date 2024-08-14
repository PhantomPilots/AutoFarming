"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy

import numpy as np
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import determine_card_merge, display_image, get_hand_cards


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    def pick_cards(self) -> tuple[list[Card], np.ndarray]:
        """How do we quantify the 'state'?
        Should it be the highest-level possible information, i.e. a screenshot?
        """

        # Extract the cards
        list_of_cards: list[Card] = get_hand_cards()

        # Extract the indices
        card_indices = self.identify_card_indices(list_of_cards)

        return self._select_cards_from_indices(list_of_cards, card_indices), card_indices

    def _select_cards_from_indices(self, house_of_cards: list[Card], indices: np.ndarray) -> list[Card]:
        """Given the selected indices, select the cards accounting for card shifts
        TODO: Poor quality code, and it should probably be done recursively to further improve the logic.
        """

        # Let's keep a copy of the original list of cards
        original_house_of_cards = deepcopy(house_of_cards)

        for i, idx in enumerate(indices):
            idx: int

            # Let's shift the indices vector first
            mask = indices[i + 1 :] < idx
            indices[i + 1 :][mask] += 1
            # print("Index shifts:", mask, indices)

            # Now, let's handle the merge...
            if idx > 0 and idx < len(house_of_cards) - 1:
                left_card, right_card = (house_of_cards[idx - 1], house_of_cards[idx + 1])
                center_card = house_of_cards[idx]

                if left_card and right_card and determine_card_merge(left_card, right_card):
                    print(f"Card {center_card.card_type.name} with idx {idx} generates a merge!")
                    # Increase the indices again -- We should not recompute the mask!
                    indices[i + 1 :][mask] += 1
                    # print("Index shifts after the merge:", indices)

                    # Increase the rank of the right card
                    if house_of_cards[idx + 1].card_rank.value != 2:
                        house_of_cards[idx + 1].card_rank = CardRanks(house_of_cards[idx + 1].card_rank.value + 1)

                    # Remove the left card
                    house_of_cards.pop(idx - 1)
                    # Let's insert a dummy card to keep proper indexing
                    house_of_cards.insert(0, None)

            house_of_cards.pop(idx)
            # Let's insert the dummy card again
            house_of_cards.insert(0, None)

        # print("Final indices:", indices)

        # Finally, return the selected cards from the original house of cards!
        return np.array(original_house_of_cards)[indices].tolist()

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

    def identify_card_indices(self, list_of_cards: list[Card]) -> np.ndarray:
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


class RecursiveBattleStrategy(IBattleStrategy):
    """Implement the logic recursively"""

    def pick_cards(self) -> tuple[list[Card], np.ndarray]:
        """"""

    def _select_cards_from_indices(
        self, house_of_cards: list[Card], n: int, indices_list: list[int] = None
    ) -> np.ndarray:
        """Return the indices of cards to click on, computed recursively

        Args:
            house_of_cards (list[Card]): Remaining list of cards for the next index to pic.
            n (int): How many cards left to pick.
            indices_list (list[int]): List of indices of cards
        """
