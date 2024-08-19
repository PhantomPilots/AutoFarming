from numbers import Integral

import numpy as np
from termcolor import cprint
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import determine_card_merge


def process_card_move(house_of_cards: list[Card], origin_idx: int, target_idx: int):
    """If we're moving a card, how does the whole hand change?"""

    if determine_card_merge(house_of_cards[origin_idx], house_of_cards[target_idx]):
        # First, increase the rank of the target card
        target_rank = house_of_cards[target_idx].card_rank
        house_of_cards[target_idx].card_rank = CardRanks(target_rank.value + 1)
        # And let's remove the origin card. Otherwise, we don't remove it
        house_of_cards.pop(origin_idx)
        # Let's insert a dummy card
        house_of_cards.insert(0, Card(CardTypes.NONE, None, None))
    else:
        # The case in which we move without having a card merge
        cprint(f"We're moving a card from {origin_idx} to {target_idx}, but it's not generating a merge!", "yellow")
        # Rearrange the house of cards
        card = house_of_cards.pop(origin_idx)
        house_of_cards.insert(target_idx, card)

    # Handle card merges due to the deletion of `idx`
    handle_card_merges(house_of_cards, origin_idx, origin_idx + 1)

    # Handle  card merges on the target side. NOTE: The masks here change, they depend on the target index instead!
    handle_card_merges(house_of_cards, target_idx - 1, target_idx)
    handle_card_merges(house_of_cards, target_idx, target_idx + 1)


def process_card_play(house_of_cards: list[Card], idx: int):
    """If we're playing a card, how does the whole hand change?"""

    # Since we assume we play a card now, let's remove it from the house of cards
    house_of_cards.pop(idx)
    # Let's insert a dummy card
    house_of_cards.insert(0, Card(CardTypes.GROUND, None, None))

    # If we're not at the beginning or end of the list, let's handle the card merges
    if idx > 0 and idx < len(house_of_cards) - 1:
        handle_card_merges(
            house_of_cards,
            left_card_idx=idx,
            right_card_idx=idx + 1,
        )


def handle_card_merges(house_of_cards: list[Card], left_card_idx: int, right_card_idx: int) -> bool:
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

    if determine_card_merge(left_card, right_card):
        print(f"Card at idx {left_card_idx} will merge with idx {right_card_idx}!")
        # Increase the rank of the right card
        if right_card.card_rank.value != 2:
            right_card.card_rank = CardRanks(right_card.card_rank.value + 1)

        # Remove the left card
        house_of_cards.pop(left_card_idx)
        # Let's insert a dummy None card to keep proper indexing
        house_of_cards.insert(0, Card(CardTypes.GROUND, None, None))

        # We may need to call this function recursively, in case multiple merges happen!
        handle_card_merges(
            house_of_cards,
            left_card_idx=right_card_idx,
            right_card_idx=right_card_idx + 1,
        )

    else:
        # If we don't find a merge, there's not gonna be a subsequent merge either
        return


def pick_card_type(card_types: list[Card], picked_card_types: list[Card], chosen_type: CardTypes) -> int:
    """Given a card type, return the chosen index"""

    ids = np.where(card_types == chosen_type.value)[0]
    if ids.size and not np.where(picked_card_types == chosen_type)[0].size:
        return ids[-1]
    return None
