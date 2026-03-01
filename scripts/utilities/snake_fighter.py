import time
from typing import Callable

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import (
    capture_window,
    click_and_sleep,
    click_im,
    draw_rectangles,
    find,
    find_and_click,
    get_card_slot_region_image,
)
from utilities.vision import Vision


class SnakeFighter(IFighter):
    # Keep track of what floor has been defeated
    floor_defeated = None

    # Keep track of what floor we're fighting
    current_floor = -1

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None):
        super().__init__(battle_strategy=battle_strategy, callback=callback)

    def fighting_state(self):

        screenshot, window_location = capture_window()

        # In case we've been lazy and it's the first time we're doing Demonic Beast this week...
        find_and_click(
            vio.weekly_mission,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("lazy_weekly_bird_mission"),
        )
        find_and_click(vio.daily_quest_info, screenshot, window_location)

        # To skip quickly to the rewards when the fight is done
        find_and_click(vio.creature_destroyed, screenshot, window_location)

        if find(vio.defeat, screenshot):
            # I may have lost though...
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT

        elif find(vio.db_victory, screenshot, threshold=0.7):
            # Fight is complete
            print("Fighting complete! Is it true? Double check...")
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif (available_card_slots := SnakeFighter.count_empty_card_slots(screenshot, threshold=0.7)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

            # Update the phase
            if (phase := self._identify_phase(screenshot)) != IFighter.current_phase:
                print(f"Moving to phase {phase}!")
                IFighter.current_phase = phase

            self.activate_talent(screenshot, window_location)

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6, debug=False):
        """Count how many empty card slots are there for SNAKE"""
        card_slots_image = get_card_slot_region_image(screenshot)
        rectangles, _ = vio.empty_card_slot.find_all_rectangles(card_slots_image, threshold=threshold)
        rectangles_2, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.7)

        # Pick what type of rectangles to keep
        rectangles = rectangles_2 if rectangles_2.size else rectangles

        if debug and len(rectangles):
            print(f"We have {len(rectangles)} empty slots.")
            # rectangles_fig = draw_rectangles(screenshot, np.array(rectangles), line_color=(0, 0, 255))
            translated_rectangles = np.array(
                [
                    [
                        r[0] + Coordinates.get_coordinates("card_slots_region")[0],
                        r[1] + Coordinates.get_coordinates("card_slots_region")[1],
                        r[2],
                        r[3],
                    ]
                    for r in rectangles
                ]
            )
            rectangles_fig = draw_rectangles(screenshot, translated_rectangles)
            cv2.imshow("rectangles", rectangles_fig)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return 4 if find(vio.skill_locked, screenshot, threshold=0.6) else len(rectangles)

    def activate_talent(self, screenshot, window_location):
        """Check if we can activate a talent"""

        talents = [
            # vio.talent_trist,
        ]

        for talent in talents:
            if find(talent, screenshot):
                print(f"Activating {talent.image_name} and waiting...")
                click_and_sleep(
                    talent,
                    screenshot,
                    window_location,
                    threshold=0.7,
                    sleep_time=2.5,
                )
                break

    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked. Overrides the parent method."""

        # Before playing cards, first:
        # 1. Read the phase we're in
        # 2. Make sure to click on the correct dog (right/left) depending on the phase
        # empty_card_slots = self.count_empty_card_slots(screenshot)

        self.play_cards()

    def _identify_phase(self, screenshot: np.ndarray):
        """Read the screenshot and identify the phase we're currently in"""
        if find(vio.phase_2, screenshot, threshold=0.8):
            return 2
        elif find(vio.phase_3, screenshot, threshold=0.8):
            return 3

        # Default to phase 1 in case we don't see anything
        return 1

    def fight_complete_state(self):

        screenshot, window_location = capture_window()

        find_and_click(vio.daily_quest_info, screenshot, window_location)

        # Click on the OK button to end the fight
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # Only consider the fight complete if we see the loading screen, in case we need to click OK multiple times
        if find(vio.db_loading_screen, screenshot):
            self.complete_callback(victory=True)
            self.exit_thread = True

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.daily_quest_info, screenshot, window_location)

        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We're going back to the main bird menu, let's end this thread
            self.complete_callback(victory=False, phase=IFighter.current_phase)
            self.exit_thread = True

    @IFighter.run_wrapper
    def run(self, floor_num=1):

        # First, set the floor number
        IFighter.current_floor = floor_num

        print(f"Fighting very hard on floor {IFighter.current_floor}...")

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.FIGHTING_COMPLETE:
                self.fight_complete_state()

            elif self.current_state == FightingStates.DEFEAT:
                self.defeat_state()

            if self.exit_thread:
                print("Closing Fighter thread!")
                return

            time.sleep(0.5)
