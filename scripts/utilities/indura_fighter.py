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
    crop_image,
    display_image,
    find,
    find_and_click,
    get_card_slot_region_image,
    get_hand_cards_3_cards,
    press_key,
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

            # Update the current phase
            if (new_phase := self._identify_phase(screenshot)) != IFighter.current_phase:
                print(f"MOVING TO PHASE {new_phase}!")
                IFighter.current_phase = new_phase
                if new_phase == 3:
                    self.battle_strategy.reset_fight_turn()

    def _identify_phase(self, screenshot: np.ndarray):
        """Read the screenshot and identify the phase we're currently in"""
        if find(vio.phase_2, screenshot, threshold=0.8):
            return 2
        elif find(vio.phase_3, screenshot, threshold=0.8):
            return 3

        # Default to phase 1 in case we don't see anything
        return 1

    def my_turn_state(self):
        """Select and play the cards"""
        screenshot, window_location = capture_window()

        # First, identify if we have to quit because a unit has died :(
        six_empty_slots_image = crop_image(
            screenshot,
            Coordinates.get_coordinates("6_cards_top_left"),
            Coordinates.get_coordinates("6_cards_bottom_right"),
        )
        if find(vio.mini_beta_buf, six_empty_slots_image):
            print("We are doing really bad... We have to quit :(")
            press_key("esc")
            time.sleep(5)  # To allow the farmer to click OK and exit the fight
            self.current_state = FightingStates.EXIT_FIGHT
            return

        # Just play the cards
        self.play_cards(screenshot, window_location)

    def exit_fight_state(self):
        """Very simple state, just exit the fight"""

        with self._lock:
            self.exit_thread = True
            # Reset the battle strategy turn
            self.battle_strategy.reset_fight_turn()

    def play_cards(self, screenshot, window_location):
        """Read the current hand of cards, and play them based on the available card slots.
        We had to overrde this method!"""

        empty_card_slots = self.count_empty_card_slots(screenshot)

        slot_index = InduraFighter.card_turn

        if empty_card_slots > 0:
            # KEY: Read the hand of cards
            current_hand = self.battle_strategy.pick_cards(
                picked_cards=self.picked_cards,
                num_units=3,
                phase=IFighter.current_phase,
                card_turn=InduraFighter.card_turn,
            )

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
            time.sleep(0.5)
            # Count GROUND cards after
            hand_cards = get_hand_cards_3_cards()
            after_num_ground_cards = len([card for card in hand_cards if card.card_type == CardTypes.GROUND])

            if after_num_ground_cards > before_num_ground_cards:
                # Increment the card turn, and add the picked card to the list of picked cards
                InduraFighter.card_turn += 1
                self.picked_cards[slot_index] = card_played

        elif empty_card_slots == 0:  # or slot_index >= len(current_hand[1]):
            print("Finished my turn!")
            InduraFighter.card_turn = 0
            # Increment to the next fight turn
            self.battle_strategy.increment_fight_turn()
            # And reset instance variables
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
