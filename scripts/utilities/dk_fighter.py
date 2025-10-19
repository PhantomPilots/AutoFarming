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


class DemonKingFighter(IFighter):
    """The Indura fighter!"""

    current_team = 0

    def fighting_state(self):
        screenshot, _ = capture_window()

        if find(vio.ok_main_button, screenshot):
            # Finished the fight, just exit the Fighter
            self.current_state = FightingStates.EXIT_FIGHT

        elif (available_card_slots := DemonKingFighter.count_empty_card_slots(screenshot)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            # Finally, time to play the cards
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

            # Update the current phase
            if (new_phase := self._identify_phase(screenshot)) != IFighter.current_phase:
                print(f"MOVING TO PHASE {new_phase}!")
                IFighter.current_phase = new_phase

    @staticmethod
    def _identify_phase(screenshot: np.ndarray):
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

        if IFighter.current_phase == 2 and DemonKingFighter.current_team == 0:
            print("Switching teams...")
            DemonKingFighter.current_team = 1
            find_and_click(vio.switch_dk_team, screenshot, window_location)

        # Just play the cards
        self.play_cards(dk_team=DemonKingFighter.current_team)

    def exit_fight_state(self):
        """Very simple state, just exit the fight"""
        screenshot, _ = capture_window()

        with self._lock:
            self.exit_thread = True
            # Reset the battle strategy turn
            self.battle_strategy.reset_fight_turn()

        self.complete_callback(find(vio.victory, screenshot))

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6, plot=False):
        """Count how many empty card slots are there for DEER"""

        card_slots_image = get_card_slot_region_image(screenshot)

        rectangles, _ = vio.empty_card_slot.find_all_rectangles(card_slots_image, threshold=threshold)
        rectangles_2, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.7)
        rectangles_3, _ = vio.dk_empty_slot.find_all_rectangles(screenshot, threshold=0.7)

        # Pick what type of rectangles to keep
        rectangles = rectangles_3 if rectangles_3.size else rectangles_2 if rectangles_2.size else rectangles

        return 3 if find(vio.skill_locked, screenshot, threshold=0.6) else min(3, len(rectangles))

    @IFighter.run_wrapper
    def run(self):

        print("Fighting very hard on Demon King...")

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.EXIT_FIGHT:
                self.exit_fight_state()

            if self.exit_thread:
                print("Closing DK fighter thread!")
                return

            time.sleep(0.7)
