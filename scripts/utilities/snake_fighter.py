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
    get_card_slot_region_image,
)
from utilities.vision import Vision


class SnakeFighter(IFighter):
    # Start by assuming we're on phase 1... but then make sure to read it every time the turn starts
    current_phase = None
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
        # To skip quickly to the rewards when the fight is done
        find_and_click(vio.creature_destroyed, screenshot, window_location)

        if find(vio.defeat, screenshot):
            # I may have lost though...
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT

        elif find(vio.finished_fight_ok, screenshot):
            # Fight is complete
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif (available_card_slots := SnakeFighter.count_empty_card_slots(screenshot, threshold=0.8)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6):
        """Count how many empty card slots are there for SNAKE"""
        rectangles, _ = vio.empty_card_slot.find_all_rectangles(screenshot, threshold=threshold)
        return len(rectangles)

    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked. Overrides the parent method."""
        screenshot, window_location = capture_window()

        # Before playing cards, first:
        # 1. Read the phase we're in
        # 2. Make sure to click on the correct dog (right/left) depending on the phase
        # empty_card_slots = self.count_empty_card_slots(screenshot)

        # TODO: Identify Snake phase here (like in Dogs)

        # 'pick_cards' will take a screenshot and extract the required features specific to that fighting strategy
        if self.current_hand is None:
            self.current_hand = self.battle_strategy.pick_cards()

        if finished_turn := self.play_cards(self.current_hand):
            print("Finished my turn, going back to FIGHTING")
            self.current_state = FightingStates.FIGHTING
            # Reset the hand
            self.current_hand = None

    def fight_complete_state(self):

        screenshot, window_location = capture_window()

        # if find(vio.guaranteed_reward, screenshot):
        #     SnakeFighter.floor_defeated = 3

        # Click on the OK button to end the fight
        find_and_click(vio.finished_fight_ok, screenshot, window_location)

        # Only consider the fight complete if we see the loading screen, in case we need to click OK multiple times
        if find(vio.db_loading_screen, screenshot):
            self.complete_callback(victory=True, floor_defeated=SnakeFighter.current_floor)
            self.exit_thread = True

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.ok_bird_defeat, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We're going back to the main bird menu, let's end this thread
            self.complete_callback(victory=False)
            self.exit_thread = True

    @IFighter.run_wrapper
    def run(self, floor_num: int):

        # First, set the floor number
        SnakeFighter.current_floor = floor_num

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
