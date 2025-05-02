import time

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
from utilities.coordinates import Coordinates
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import (
    capture_hand_image,
    capture_hand_image_3_cards,
    capture_window,
    display_image,
    find,
    find_and_click,
    get_card_slot_region_image,
    get_hand_cards_3_cards,
)


class InduraFighter(IFighter):
    """The Indura fighter!"""

    card_turn = 0

    def fighting_state(self):
        screenshot, _ = capture_window()

        if find(vio.ok_main_button, screenshot):
            # Finished the fight, just exit the Indura Fighter
            self.current_state = FightingStates.EXIT_FIGHT

        elif (available_card_slots := InduraFighter.count_empty_card_slots(screenshot)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            # Finally, time to play the cards
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

    def my_turn_state(self):
        """Select and play the cards"""

        # Ensure we have the current hand
        if self.current_hand is None:
            self.current_hand = self.battle_strategy.pick_cards(cards_to_play=3)

        if finished_turn := self.play_cards(self.current_hand):
            print("Finished my turn, going back to FIGHTING")
            self.current_state = FightingStates.FIGHTING
            # Reset the hand
            self.current_hand = None

    def exit_fight_state(self):
        """Very simple state, just exit the fight"""

        with self._lock:
            self.exit_thread = True

    def play_cards(self, selected_cards: tuple[list[Card], list[int | tuple[int, int]]]):
        """We need to overrde this method!"""

        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot)

        slot_index = InduraFighter.card_turn
        if slot_index < len(selected_cards[1]) and empty_card_slots > 0 and len(selected_cards[1]) >= empty_card_slots:
            print(
                f"Selecting card for slot index {slot_index}, with {self.available_card_slots} og card slots and now seeing {empty_card_slots} empty slots.",
            )
            # What is the index in the hand we have to play? It can be an `int` or a `tuple[int, int]`
            index_to_play = selected_cards[1][slot_index]

            # Count how many GROUND before and after playing a card
            hand_cards = get_hand_cards_3_cards()
            before_num_ground_cards = len([card for card in hand_cards if card.card_type == CardTypes.GROUND])
            # Play/move the selected card
            self._play_card(
                selected_cards[0], index=index_to_play, window_location=window_location, screenshot=screenshot
            )
            time.sleep(0.5)
            # Count GROUND cards after
            hand_cards = get_hand_cards_3_cards()
            after_num_ground_cards = len([card for card in hand_cards if card.card_type == CardTypes.GROUND])

            if after_num_ground_cards > before_num_ground_cards:
                InduraFighter.card_turn += 1

        elif empty_card_slots == 0 or slot_index >= len(selected_cards[1]):
            print("Finished my turn!")
            InduraFighter.card_turn = 0
            return 1

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6, plot=False):
        """Count how many empty card slots are there for DEER"""

        card_slots_image = get_card_slot_region_image(screenshot)

        rectangles, _ = vio.empty_card_slot.find_all_rectangles(card_slots_image, threshold=threshold)
        rectangles_2, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.7)
        rectangles_3, _ = vio.indura_empty_slot.find_all_rectangles(screenshot, threshold=0.7)

        # Pick what type of rectangles to keep
        rectangles = rectangles_3 if rectangles_3.size else rectangles_2 if rectangles_2.size else rectangles

        return 3 if find(vio.skill_locked, screenshot, threshold=0.6) else min(3, len(rectangles))

    @IFighter.run_wrapper
    def run(self):

        print("Fighting very hard on Indura...")

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.EXIT_FIGHT:
                self.exit_fight_state()

            if self.exit_thread:
                print("Closing Indura fighter thread!")
                return

            time.sleep(1)
