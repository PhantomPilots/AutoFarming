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

        # Just play the cards
        self.play_cards()

    def exit_fight_state(self):
        """Very simple state, just exit the fight"""

        with self._lock:
            self.exit_thread = True

    def play_cards(self):
        """Read the current hand of cards, and play them based on the available card slots.
        We had to overrde this method!"""

        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot)

        # KEY: Read the hand of cards
        current_hand = self.battle_strategy.pick_cards(
            picked_cards=self.picked_cards,
            cards_to_play=3,
            phase=IFighter.current_phase,
            floor=IFighter.current_floor,
        )

        slot_index = InduraFighter.card_turn
        if slot_index < len(current_hand[1]) and empty_card_slots > 0 and len(current_hand[1]) >= empty_card_slots:
            print(
                f"Selecting card for slot index {slot_index}, with {self.available_card_slots} og card slots and now seeing {empty_card_slots} empty slots.",
            )
            # What is the index in the hand we have to play? It can be an `int` or a `tuple[int, int]`
            index_to_play = current_hand[1][0]

            # Count how many GROUND before and after playing a card
            hand_cards = get_hand_cards_3_cards()
            before_num_ground_cards = len([card for card in hand_cards if card.card_type == CardTypes.GROUND])
            # Play/move the selected card
            card_played = self._play_card(
                current_hand[0], index=index_to_play, window_location=window_location, screenshot=screenshot
            )
            time.sleep(0.25)
            # Count GROUND cards after
            hand_cards = get_hand_cards_3_cards()
            after_num_ground_cards = len([card for card in hand_cards if card.card_type == CardTypes.GROUND])

            if after_num_ground_cards > before_num_ground_cards:
                # Increment the card turn, and add the picked card to the list of picked cards
                InduraFighter.card_turn += 1
                self.picked_cards[slot_index] = card_played

        elif empty_card_slots == 0 or slot_index >= len(current_hand[1]):
            print("Finished my turn!")
            InduraFighter.card_turn = 0
            self._reset_instance_variables()
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
