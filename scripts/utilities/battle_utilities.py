from copy import deepcopy

import numpy as np
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import determine_card_merge


def handle_card_merges(
    house_of_cards: list[Card], left_card_idx: int, right_card_idx: int, indices_to_update: np.ndarray, mask: np.ndarray
) -> bool:
    """Modifies the current list of cards in-place if there is a merge caused by the given index.
    Handles card merges by playing a card recursively.

    Args:
        house_of_cards (list[Card]): The list of cards to evaluate.
        idx (int): The index of the card we want to play evaluate if playing it will generate a merge.

    Returns:
        bool: It modifies the list in place, and returns whether a merge took place.
    """
    if left_card_idx >= right_card_idx or right_card_idx >= len(house_of_cards):
        return

    left_card, right_card = house_of_cards[left_card_idx], house_of_cards[right_card_idx]

    if left_card and right_card and determine_card_merge(left_card, right_card):
        print(f"Card at idx {left_card_idx} will merge with idx {right_card_idx}!")
        # Increase the rank of the right card
        if right_card.card_rank.value != 2:
            right_card.card_rank = CardRanks(right_card.card_rank.value + 1)

        # Remove the left card
        house_of_cards.pop(left_card_idx)
        # Let's insert a dummy None card to keep proper indexing
        house_of_cards.insert(0, None)

        # Shift the indices by one
        indices_to_update[mask] += 1

        # We may need to call this function recursively, in case multiple merges happen!
        handle_card_merges(
            house_of_cards,
            left_card_idx=left_card_idx + 2,
            right_card_idx=right_card_idx + 1,
            indices_to_update=indices_to_update,
            mask=mask,
        )
