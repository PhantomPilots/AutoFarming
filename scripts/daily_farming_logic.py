import threading
import time
from datetime import datetime
from enum import Enum, auto

import numpy as np
import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    find,
    find_and_click,
    find_floor_coordinates,
    press_key,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DailyLogger", log_file="daily_farmer_logger.log")


class States(Enum):
    IN_TAVERN = 0
    BOSS_STATE = auto()
    VANYA_ALE_STATE = auto()
    FORT_SOLRGESS_STATE = auto()
    PVP_STATE = auto()
    BRAWL_STATE = auto()
    PATROL_STATE = auto()
    FRIENDSHIP_COINS_STATE = auto()
    EXIT_FARMER = auto()


class DailyFarmer(IFarmer):

    exit_flag = False

    def __init__(self, battle_strategy=None, starting_state=States.IN_TAVERN, logger=logger):

        self.logger = logger
        self.current_state = starting_state
        # Not needed, remove?
        self.batle_strategy = battle_strategy

    def exit_farmer_state(self):

        # Cleanup before exiting
        DailyFarmer.exit_flag = True

    def find_next_mission(self) -> States | None:
        """Identify the next mission to do, by scrolling if we can't find any match.
        Returns a State or None if nothing can be found"""
        screenshot, window_location = capture_window()

    def in_tavern_state(self):
        """We're in the tavern, go to the next task."""

        screenshot, window_location = capture_window()

        # Click on the dailies menu

        # Click on the next "Go now" -> How to identify the next state from this?

    def boss_state(self):
        """Handle the boss state."""

    def vanya_ale_state(self):
        """Handle the Vanya Ale state."""

    def fort_solrgess_state(self):
        """Handle the Fort Solrgess state."""

    def pvp_state(self):
        """Handle the PvP state."""

    def brawl_state(self):
        """Handle the Brawl state."""

    def patrol_state(self):
        """Handle the Patrol state."""

    def friendship_coins_state(self):
        """Handle the Friendship Coins state."""

    def run(self):

        self.logger.info("Doing dailies!")

        while True:
            if self.current_state == States.IN_TAVERN:
                self.in_tavern_state()

            elif self.current_state == States.BOSS_STATE:
                self.boss_state()

            elif self.current_state == States.VANYA_ALE_STATE:
                self.vanya_ale_state()

            elif self.current_state == States.FORT_SOLRGESS_STATE:
                self.fort_solrgess_state()

            elif self.current_state == States.PVP_STATE:
                self.pvp_state()

            elif self.current_state == States.BRAWL_STATE:
                self.brawl_state()

            elif self.current_state == States.PATROL_STATE:
                self.patrol_state()

            elif self.current_state == States.FRIENDSHIP_COINS_STATE:
                self.friendship_coins_state()

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            # Close the daily farmer
            if DailyFarmer.exit_flag:
                break
