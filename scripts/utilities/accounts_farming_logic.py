import threading
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
    WAITING_FOR_LOGIN = auto()


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

    account_list: list[dict[str, str]] | None = None

    # The thread for doing dailies
    dailies_thread: threading.Thread | None = None

    # The thread for doing weeklies
    weeklies_thread: threading.Thread | None = None

    _lock = Lock()  # To ensure thread safety when accessing shared resources

    def __init__(
        self,
        starting_state: States = States.SWITCH_ACCOUNT,
        battle_strategy: IBattleStrategy | None = None,  # UNUSED
        do_weeklies: bool = False,
        **kwargs,  # UNUSED
    ):
        self.current_account: dict[str, str] = None  # Dict with {"user":..., "sync":..., "password":...}

        if ManyAccountsFarmer.account_list is None:
            ManyAccountsFarmer.account_list = self.load_accounts()
            print("Farmer started for the following accounts:")
            for i, account in enumerate(ManyAccountsFarmer.account_list):
                print(f"{account['user']}", end=", " if i < len(self.account_list) - 1 else "")
            print("\n")

            # And let's initialize the current account, only once
            self.pick_next_account()

        self.do_weeklies = do_weeklies

        self.account_list = ManyAccountsFarmer.account_list  # instance-level access to shared list

        # We always want to initialize in the daily quests state
        self.current_state: States = starting_state

        # For the daily farmer
        ManyAccountsFarmer.daily_farmer.add_complete_callback(self.dailies_done)

        # For the weekly farmer
        ManyAccountsFarmer.weekly_farmer.add_complete_callback(self.weeklies_done)

    def load_accounts(self) -> list[dict[str, str]]:
        """Load accounts from a configuration file"""
        return load_yaml_config("config/accounts.yaml")["accounts"]

    def exit_message(self):
        """Final message to display on the screen farming is done"""

    def pick_next_account(self):
        """Pick the next account to work on"""
        if not len(self.account_list):
            raise KeyboardInterrupt("Finished farming all accounts! Nothing else to do.")

        # Get next account to work on
        self.current_account = self.account_list.pop(0)
        print(f"Picked next account: {self.current_account['user']}")

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
                point_coordinates=Coordinates.get_coordinates("sync_code"),
            )
            type_word(self.current_account["sync"])

            # Then, password
            find_and_click(vio.password, screenshot, window_location)
            # Type the password and press enter
            type_word(self.current_account["password"])
            press_key("enter")

            # Kill the farmers, in case they are running for some reason
            if ManyAccountsFarmer.dailies_thread is not None and ManyAccountsFarmer.dailies_thread.is_alive():
                ManyAccountsFarmer.daily_farmer.kill_farmer()
            if ManyAccountsFarmer.weeklies_thread is not None and ManyAccountsFarmer.weeklies_thread.is_alive():
                ManyAccountsFarmer.weekly_farmer.kill_farmer()

            time.sleep(3)  # Wait for proper login

    def daily_quests_state(self):
        """Doing dailies for the current account"""
        # TODO Probably set up the Dailies farmer here?
        with ManyAccountsFarmer._lock:
            if (
                ManyAccountsFarmer.dailies_thread is None or not ManyAccountsFarmer.dailies_thread.is_alive()
            ) and self.current_state == States.DAILY_QUESTS:
                ManyAccountsFarmer.dailies_thread = threading.Thread(target=self.daily_farmer.run, daemon=True)
                ManyAccountsFarmer.dailies_thread.start()
                print("Dailies farmer started!")

    def weekly_quests_state(self):
        """Doing weeklies for the current account"""

        if not self.do_weeklies:
            print("Skipping weeklies.")

        self.weeklies_done()

    def dailies_done(self):
        """Callback to receive when the dailies farmer has finished for the current account"""

        print("Finished dailies for account:", self.current_account["user"])
        self.current_state = States.WEEKLY_QUESTS

    def weeklies_done(self):
        """Callback to receive when the weeklies farmer has finished for the current account"""

        print("Finished weeklies for account:", self.current_account["user"])

        # Close the game
        close_game()
        # And let's wait for the game to re-open properly
        self.current_state = States.WAITING_FOR_LOGIN

    def waiting_for_login_state(self):
        """State to wait for the login screen to appear"""
        screenshot, _ = capture_window()

        # Switch to next account only when we see the login screen
        if find(vio.sync_code, screenshot):
            # Pick next account
            self.pick_next_account()

            print("Switching to next account...")
            self.current_state = States.SWITCH_ACCOUNT

    def check_for_login(self):
        """Check whether we need to switch to the login state"""
        screenshot, window_location = capture_window()

        # Check if duplicate connection, if so click on 'ok_main_button'
        if find(vio.duplicate_connection, screenshot):
            print("Duplicate connection detected!")
            find_and_click(vio.ok_main_button, screenshot, window_location)

        elif find(vio.password, screenshot) and self.current_state not in {
            States.SWITCH_ACCOUNT,
            States.WAITING_FOR_LOGIN,
        }:
            self.current_state = States.SWITCH_ACCOUNT
            print(f"We've been logged out! Tell {self.current_account['user']} that we're logging back in.")

    def run(self):

        while True:

            self.check_for_login()

            if self.current_state == States.DAILY_QUESTS:
                self.daily_quests_state()
            elif self.current_state == States.WEEKLY_QUESTS:
                self.weekly_quests_state()
            elif self.current_state == States.SWITCH_ACCOUNT:
                self.switch_account_state()
            elif self.current_state == States.WAITING_FOR_LOGIN:
                self.waiting_for_login_state()

            time.sleep(1)
