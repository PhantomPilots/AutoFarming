import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.deer_utilities import *
from utilities.deer_utilities import is_blue_card, is_green_card, is_red_card
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import (
    capture_window,
    determine_card_merge,
    find,
    is_ground_card,
    is_hard_hitting_snake_card,
    is_stance_cancel_card,
)


class DeerBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Deer"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if phase == 1:
            return self.phase_1(hand_of_cards, picked_cards)

        if phase in {2, 4}:
            return self.phase_2_4(hand_of_cards, picked_cards)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Try not to pick two cards from the same unit"""
        card_idx = -1 - DeerBattleStrategy.card_turn

        while is_ground_card(hand_of_cards[card_idx]):
            card_idx -= 1
            card_idx %= len(hand_of_cards)

        return card_idx

    def phase_2_4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Take into account the roulette"""

        screenshot, _ = capture_window()

        red_card_ids = np.where([is_red_card(card) for card in hand_of_cards])[0]
        blue_card_ids = np.where([is_blue_card(card) for card in hand_of_cards])[0]
        green_card_ids = np.where([is_green_card(card) for card in hand_of_cards])[0]

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
        if find(vio.red_buff, screenshot) and len(red_card_ids):
            print("There's a red buff on! Picking red card")
            return red_card_ids[-1]
        if find(vio.blue_buff, screenshot) and len(blue_card_ids):
            print("There's a blue buff on! Picking blue card")
            return blue_card_ids[-1]
        if find(vio.green_buff, screenshot) and len(green_card_ids):
            print("There's a green buff on! Picking green card")
            return green_card_ids[-1]

        # If it's the beginning of the roulette and no color is present...
        if last_card.card_image is None and len(green_card_ids):
            # Pick a green card, since we have twice the chances to have one of those
            print("Roulette hasn't started, picking a green card by default")
            return green_card_ids[-1]

        # If the above doesn't happen, meaning we don't have available cards for this:
        print("Couldn't find the right card, defaulting to -1...")
        return -1
