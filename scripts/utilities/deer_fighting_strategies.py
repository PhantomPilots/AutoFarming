import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
from utilities.deer_utilities import (
    is_blue_card,
    is_green_card,
    is_red_card,
    reorder_buff_removal_card,
)
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, find, is_ground_card


class DeerBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Deer"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if phase in {2, 4}:
            return self.phase_2_4(hand_of_cards, picked_cards)

        return self.default_strategy(hand_of_cards, picked_cards)

    def phase_2_4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Take into account the roulette"""

        screenshot, _ = capture_window()

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        # Get all card types
        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_card_ids: list[int] = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        # Place buff removal card at the beginning of the list, to save it if necessary
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        # First of all, if the beast has an evasion and we haven't played one yet:
        buff_removal_ids = np.where([find(vio.jorm_2, card.card_image) for card in hand_of_cards])[0]
        if find(vio.evasion, screenshot, threshold=0.7) and (
            len(buff_removal_ids) and not np.any([find(vio.jorm_2, card.card_image) for card in picked_cards])
        ):
            print("Deer has an evasion, let's remove it")
            return buff_removal_ids[-1]

        # Keep track of last picked card
        last_card = picked_cards[-1] if len(picked_cards) else Card()

        if is_green_card(last_card) and len(blue_card_ids):
            print("Last card green! Picking blue")
            # Gotta pick a blue card
            return blue_card_ids[-1]
        if is_red_card(last_card) and len(green_card_ids):
            print("Last card red! Picking green")
            # Gotta pick a green card
            return green_card_ids[-1]
        if is_blue_card(last_card) and len(red_card_ids):
            print("Last card blue! Picking red")
            # Gotta pick a red card
            return red_card_ids[-1]

        # If the above doesn't happen, meaning it's the first card to pick...
        if last_card.card_image is None:
            if find(vio.red_buff, screenshot) and len(red_card_ids):
                print("There's a red buff on! Picking red card")
                return red_card_ids[-1]
            if find(vio.blue_buff, screenshot) and len(blue_card_ids):
                print("There's a blue buff on! Picking blue card")
                return blue_card_ids[-1]
            if find(vio.green_buff, screenshot) and len(green_card_ids):
                print("There's a green buff on! Picking green card")
                return green_card_ids[-1]

            # If none of the above, picked the card that has the most types
            max_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
            if len(max_ids):
                print("Roulette hasn't started, picking the type that has the most cards.")
                return max_ids[-1]

        # If the above doesn't happen...
        print("Couldn't find the right card, defaulting...")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def default_strategy(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Default strategy: Picked a card whose type has the most number of cards"""

        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        # Play a buff card first, if we have it and haven't played it yet
        buff_ids = sorted(np.where(card_types == CardTypes.BUFF.value)[0], key=lambda idx: card_ranks[idx])
        if len(buff_ids) and not np.where(picked_card_types == CardTypes.BUFF.value)[0].size:
            return buff_ids[-1]

        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        # Place buff removal card at the beginning of the list, to save it if necessary
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        max_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
        if len(max_ids):
            print("Defaulting to picking the type that has the most cards.")
            return max_ids[-1]

        print("Defaulting...")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
