import threading
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
)


class States(Enum):
    GOING_TO_FLOOR = 0
    FIGHTING = 1


class Floor4Farmer(IFarmer):

    def __init__(self, battle_strategy: IBattleStrategy, starting_state: States, **kargs):

        # For type helping
        self.current_state = starting_state
        # We will need to develop a specific battle strategy for it
        self.battle_strategy = battle_strategy

        # Keep track of how many times we've beat the fight
        self.success_count = 0

    def exit_message(self):
        print(f"We've beat FLoor 4 of Bird {self.success_count} times.")

    def going_to_floor_state(self):

        screenshot, window_location = capture_window()

        # Restore stamina if we need to
        find_and_click(vio.restore_stamina, screenshot, window_location)

        # Click on floor 4 if it's available
        find_and_click(vio.floor_3_cleard, screenshot, window_location)
        find_and_click(vio.floor_3_cleard_2, screenshot, window_location)
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We can move to the next state
            print("Moving to FIGHTING!")
            self.current_state = States.FIGHTING

    def fighting_state(self):

        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location)

        print("Fighting hard!")

    def fight_complete_callback(self, victory=True):
        """Called when the fight logic completes."""

        if victory:
            # Transition to another state or perform clean-up actions
            print("Floor 4 complete!")
            self.success_count += 1
        else:
            print("The bird fighter told me they lost... :/")

        # Go straight to the original states
        self.current_state = States.GOING_TO_FLOOR

    def run(self):

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_FLOOR:
                self.going_to_floor_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            time.sleep(0.8)
