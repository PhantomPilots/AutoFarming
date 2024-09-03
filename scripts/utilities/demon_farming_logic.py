import threading
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
    find_floor_coordinates,
)


class States(Enum):
    GOING_TO_DEMONS = 0
    LOOKING_FOR_DEMON = 1
    READY_TO_FIGHT = 2
    FIGHTING_DEMON = 3


class DemonFarmer(IFarmer):

    def __init__(self, battle_strategy: IBattleStrategy = None, starting_state=States.GOING_TO_DEMONS):

        self.current_state = starting_state

        # No battle strategy needed, we'll auto
        self.battle_strategy = battle_strategy

        # Keep track of how many demons we've beat
        self.demons_destroyed = 0

    def exit_message(self):
        """Final message!"""
        print(f"We destroyed {self.demons_destroyed} demons.")

    def going_to_demons_state(self):
        """Go to the demons page"""

    def looking_for_demon_state(self):
        """Waiting for someone to send us a demon"""

    def ready_to_fight_state(self):
        """We've accepted a raid!"""

    def fighting_demon_state(self):
        """Fighting the demon hard..."""

    def run(self):

        print(f"Farming demons, starting from {self.current_state}")

        while True:
            # Try to reconnect first
            check_for_reconnect()

            if self.current_state == States.GOING_TO_DEMONS:
                self.going_to_demons_state()

            elif self.current_state == States.LOOKING_FOR_DEMON:
                self.looking_for_demon_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING_DEMON:
                self.fighting_demon_state()

            # We need the loop to run very fast
            time.sleep(0.1)
