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
    click_im,
    draw_rectangles,
    find,
    find_and_click,
)
from utilities.vision import Vision


class DogsFighter(IFighter):
    # Start by assuming we're on phase 1... but then make sure to read it every time the turn starts
    current_phase = None
    # Keep track of what floor has been defeated
    floor_defeated = None

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
        # To skip quickly to the rewards when the fight is done
        find_and_click(vio.creature_destroyed, screenshot, window_location)

        if find(vio.finished_fight_ok, screenshot):
            # Fight is complete
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif find(vio.defeat, screenshot):
            # I may have lost though...
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT

        elif (available_card_slots := self.count_empty_card_slots(screenshot)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.8):
        """Count how many empty card slots are there for DOGS"""
        rectangles = []
        for i in range(1, 10):
            vio_image: Vision = getattr(vio, f"empty_slot_{i}")
            temp_rectangles, _ = vio_image.find_all_rectangles(screenshot, threshold=threshold)
            rectangles.extend(temp_rectangles)

        # Group all rectangles
        grouped_rectangles, _ = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)
        # if len(grouped_rectangles):
        #     rectangles_fig = draw_rectangles(screenshot, grouped_rectangles)
        #     cv2.imshow("rectangles", rectangles_fig)
        #     cv2.waitKey(0)
        return len(grouped_rectangles)

    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked. Overrides the parent method."""
        screenshot, window_location = capture_window()

        # Before playing cards, first:
        # 1. Read the phase we're in
        # 2. Make sure to click on the correct dog (right/left) depending on the phase
        empty_card_slots = self.count_empty_card_slots(screenshot)

        if find(vio.phase_1, screenshot) and DogsFighter.current_phase != 1:
            # Click on light dog
            click_im(Coordinates.get_coordinates("light_dog"), window_location)
            DogsFighter.current_phase = 1
        elif find(vio.phase_2, screenshot) and DogsFighter.current_phase != 2:
            # Click on dark dog
            click_im(Coordinates.get_coordinates("dark_dog"), window_location)
            DogsFighter.current_phase = 2
        elif find(vio.phase_3, screenshot) and DogsFighter.current_phase != 3:
            # Click on dark dog
            DogsFighter.current_phase = 3
            click_im(Coordinates.get_coordinates("dark_dog"), window_location)

        # 'pick_cards' will take a screenshot and extract the required features specific to that fighting strategy
        if self.current_hand is None:
            self.current_hand = self.battle_strategy.pick_cards()

        # We have the cards now, click on them
        self.play_cards(self.current_hand)

        if not self.count_empty_card_slots(screenshot):
            print("Finished my turn, going back to FIGHTING")
            self.current_state = FightingStates.FIGHTING
            # Reset the hand
            self.current_hand = None

    def fight_complete_state(self):

        screenshot, window_location = capture_window()

        if find(vio.guaranteed_reward, screenshot):
            DogsFighter.floor_defeated = 3

        # Click on the OK button to end the fight
        find_and_click(vio.finished_fight_ok, screenshot, window_location)

        # Only consider the fight complete if we see the loading screen, in case we need to click OK multiple times
        if find(vio.db_loading_screen, screenshot):
            self.complete_callback(victory=True, floor_defeated=DogsFighter.floor_defeated)
            self.exit_thread = True
            # Reset the defeated floor
            DogsFighter.floor_defeated = None

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.ok_bird_defeat, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We're going back to the main bird menu, let's end this thread
            self.complete_callback(victory=False)
            self.exit_thread = True

    @IFighter.run_wrapper
    def run(self):

        print("Fighting very hard...")

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

            time.sleep(0.7)
