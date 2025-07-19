import time
from enum import Enum, auto
from threading import Lock
from typing import Callable

import numpy as np
import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.daily_farming_logic import DailyFarmer
from utilities.daily_farming_logic import States as DailyFarmerStates
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    click_and_sleep,
    close_game,
    crop_image,
    find,
    find_and_click,
    load_yaml_config,
    press_key,
    type_word,
)
from utilities.vision import Vision
from utilities.weekly_farming_logic import States as WeeklyFarmerStates
from utilities.weekly_farming_logic import WeeklyFarmer


class States(Enum):
    """States for the Accounts farmer"""

    DAILY_QUESTS = auto()
    WEEKLY_QUESTS = auto()
    SWITCH_ACCOUNT = auto()


class ManyAccountsFarmer:
    """Farmer for managing dailies and weeklies of a set of accounts"""

    daily_farmer = DailyFarmer(
        starting_state=DailyFarmerStates.IN_TAVERN_STATE,
        do_daily_pvp=True,  # ALWAYS do daily PvP. Not my fault if you lose!
        complete_callback=None,
    )

    weekly_farmer = WeeklyFarmer(
        starting_state=WeeklyFarmerStates.IN_TAVERN_STATE,
        complete_callback=None,
    )

    def __init__(self):

        self.account_list = self.load_accounts()
        self.current_account: dict[str, str] = None  # Stores "username": "password"

        # We always want to initialize in the daily quests state
        self.current_state: States = States.DAILY_QUESTS

        # For the daily farmer
        ManyAccountsFarmer.daily_farmer.add_complete_callback(self.dailies_done)

        # For the weekly farmer
        ManyAccountsFarmer.weekly_farmer.add_complete_callback(self.weeklies_done)

    def load_accounts(self) -> list[dict[str, str]]:
        """Load accounts from a configuration file"""
        return load_yaml_config("config/accounts.yaml")["accounts"]

    def pick_next_account(self):
        """Pick the next account to work on"""
        if not len(self.account_list):
            raise KeyboardInterrupt("Finished farming all accounts! Nothing else to do.")

        # Get next account to work on
        self.current_account = self.account_list.pop(0)
        print(f"Picked next account: {self.current_account['username']}")

    def switch_account_state(self):  # sourcery skip: extract-method
        """After we've picked the next account, we need to close the game and re-open it"""
        # TODO How to handle "re-logging in" to the new account? We cannot use the IFarmer interface here
        screenshot, window_location = capture_window()

        # First of all, if we have a 'cancel', click that first!
        if find_and_click(vio.cancel, screenshot, window_location):
            return

        if find(vio.tavern, screenshot):
            print("Logged in successfully! Going back to the previous state...")
            self.current_state = States.DAILY_QUESTS
        elif find(vio.connection_confrm_expired, screenshot):
            print("Connection confirmation expired!")
            close_game()
            return

        # In case we have an update
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.skip, screenshot, threshold=0.6) or find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a daily reset!")
            self.current_state = States.DAILY_RESET
            login_attempted = True

        elif find_and_click(vio.yes, screenshot, window_location):
            print("Downloading update...")

        elif find_and_click(
            vio.global_server,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("center_screen"),
        ):
            print("Trying to log back in...")

        elif find(vio.sync_code, screenshot):
            # First, username
            find_and_click(
                vio.sync_code,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("username"),
            )
            type_word(self.current_account["username"])
            time.sleep(0.5)

            # Then, password
            find_and_click(vio.password, screenshot, window_location)
            # Type the password and press enter
            type_word(self.current_account["password"])
            press_key("enter")

    def daily_quests_state(self):
        """Doing dailies for the current account"""
        # TODO Probably set up the Dailies farmer here?

        self.dailies_done()

    def weekly_quests_state(self):
        """Doing weeklies for the current account"""

        self.weeklies_done()

    def dailies_done(self):
        """Callback to receive when the dailies farmer has finished for the current account"""

        print("Finished dailies for account:", self.current_account["username"])
        self.current_state = States.WEEKLY_QUESTS

    def weeklies_done(self):
        """Callback to receive when the weeklies farmer has finished for the current account"""

        print("Finished weeklies for account:", self.current_account["username"])
        # Pick next account
        self.pick_next_account()
        # Close the game
        close_game()
        # Switch to next account
        self.current_state = States.SWITCH_ACCOUNT

    def run(self):

        print("Farmer started for the following accounts:")
        for account in self.account_list:
            print(f"Account: {account['username']}", end=", ")
        print("\n")

        while True:

            if self.current_state == States.DAILY_QUESTS:
                self.daily_quests_state()
            elif self.current_state == States.WEEKLY_QUESTS:
                self.weekly_quests_state()
            elif self.current_state == States.SWITCH_ACCOUNT:
                self.switch_account_state()

            time.sleep(1)
