import sys
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
    find_floor_coordinates,
)


class States(Enum):
    READY_TO_FIGHT = 1
    FIGHTING = 2
    EXIT_FARMER = 3


class TowerTrialsFarmer(IFarmer):

    def __init__(self, battle_strategy: IBattleStrategy | None = None, starting_state=States.READY_TO_FIGHT, **kwargs):

        # Initialize the current state
        self.current_state = starting_state

        # TODO: Unused, bad coding -- Make this default somehow?
        self.fighter = battle_strategy

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Get the floor coordinates of the available floor, and click on the corresponding floor
        if floor_coordinates := find_floor_coordinates(screenshot, window_location):
            find_and_click(
                vio.available_floor,
                screenshot,
                window_location,
                point_coordinates=floor_coordinates,
                threshold=0.8,
            )

        # Click on START to begin the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        # If we see a SKIP button
        if (
            find(vio.skip, screenshot, threshold=0.7)
            or find(vio.fb_aut_off, screenshot)
            or find(vio.pause_fight, screenshot)
        ):
            # Go to fight!
            print("Moving to FIGHTING")
            self.current_state = States.FIGHTING
            return

    def fighting_state(self):

        screenshot, window_location = capture_window()

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Click on "again"
        if find_and_click(vio.continue_fight, screenshot, window_location):
            return

        # For when we've cleared an episode
        find_and_click(vio.episode_clear, screenshot, window_location)

        # # If there's an OK button, click it
        # if find_and_click(vio.ok_main_button, screenshot, window_location):
        #     print("It seems we've finished the Tower of Trials! Exiting the farmer.")
        #     self.current_state = States.EXIT_FARMER
        #     return

        # Skip to the fight
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.6)

        # Ensure AUTO is on
        find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.9)

    def run(self):

        while True:

            check_for_reconnect()

            if self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == States.EXIT_FARMER:
                return

            time.sleep(0.8)
