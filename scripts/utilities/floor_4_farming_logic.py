import os
import threading
import time
from collections import defaultdict
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import MINUTES_TO_WAIT_BEFORE_LOGIN, IFarmer
from utilities.general_farmer_interface import States as GlobalStates
from utilities.general_fighter_interface import IFighter
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
    screenshot_testing,
)

logger = LoggerWrapper("Floor4Logger", log_file="floor_4.log")


class States(Enum):
    PROCEED_TO_FLOOR = 0
    FIGHTING = 1
    READY_TO_FIGHT = 2
    EXIT_FARMER = 3
    GOING_TO_DB = 4


class IFloor4Farmer(IFarmer):

    # Need to be static across instances
    success_count = 0
    total_count = 0
    dict_of_defeats = defaultdict(int)

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state: States,
        max_runs="inf",
        demonic_beast_image: vio.Vision | None = None,
        password: str | None = None,
    ):

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {MINUTES_TO_WAIT_BEFORE_LOGIN} mins. before attempting a log in.")

        self.max_runs = float(max_runs)
        if self.max_runs < float("inf"):
            print(f"We're gonna clear Floor4 {int(self.max_runs)} times.")

        # Store internally the image of the DemonicBeast we want to fight (Bird/Deer for now)
        self.db_image = demonic_beast_image

        # For type helping
        self.current_state = starting_state
        # We will need to develop a specific battle strategy for it
        self.battle_strategy = battle_strategy

        # Placeholder for the thread that will call the fighter logic
        self.fight_thread = None

        # For the login/dailies
        IFarmer.daily_farmer.set_daily_pvp(False)
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

    def exit_message(self):
        super().exit_message()
        print(f"We beat Floor4 a total of {IFloor4Farmer.success_count} out of {IFloor4Farmer.total_count} times.")
        # Log the defeats
        if len(IFloor4Farmer.dict_of_defeats):
            defeat_msg = self._print_defeats()
            logger.info(defeat_msg)

    def _print_defeats(self):
        """Generate a string message to log"""
        str_msg = "Defeats:\n"
        for phase, count in IFloor4Farmer.dict_of_defeats.items():
            str_msg += f"* Phase {phase} -> Lost {count} times.\n"

        return str_msg

    def going_to_db_state(self):
        """This should be the original state. Let's go to the DemonicBeast menu"""
        screenshot, window_location = capture_window()

        # If we're back in the tavern, click on the battle menu.
        find_and_click(
            vio.main_menu,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("battle_menu"),
        )

        # If we're in the battle menu, click on Demonic Beast
        find_and_click(vio.demonic_beast, screenshot, window_location)

        # Go into the 'db' section
        find_and_click(self.db_image, screenshot, window_location)

        # Double-check that floor 3 is not cleared
        if find(vio.floor_3_cleared_db, screenshot):
            print("Going to fight the DemonicBeast!")
            self.current_state = States.PROCEED_TO_FLOOR

    def proceed_to_floor_state(self):

        screenshot, window_location = capture_window()

        # In case we need to unlock the floor
        find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.6)

        # Click on floor 4 if it's available
        find_and_click(vio.floor_3_cleared_db, screenshot, window_location, threshold=0.7)

        if find(vio.startbutton, screenshot):
            # We can move to the next state
            print("Let's GET READY to fight.")
            self.current_state = States.READY_TO_FIGHT

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # Restore stamina if we need to
        if find_and_click(vio.restore_stamina, screenshot, window_location, threshold=0.8):
            IFarmer.stamina_pots += 1
            # screenshot_testing(screenshot, vio.restore_stamina)
            return

        # Try to start the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot) or find(vio.tavern_loading_screen, screenshot):
            # We can move to the next state
            print("Moving to FIGHTING!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location)

        # Set the fighter thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            print("Floor4 fight started!")
            self.fight_thread = threading.Thread(target=self.fighter.run, name="Floor4FighterThread", daemon=True)
            self.fight_thread.start()

    def fight_complete_callback(self, victory=True, **kwargs):
        """Called when the fight logic completes."""

        IFloor4Farmer.total_count += 1
        if victory:
            # Transition to another state or perform clean-up actions
            IFloor4Farmer.success_count += 1
            print("FLOOR 4 COMPLETE, WOOO!")
        else:
            phase = kwargs.get("phase", None)
            print(f"The fighter told me they lost{f' on phase {phase}' if phase is not None else ''}... :/")
            # Increment the defeat count of the corresponding phase
            if phase is not None:
                IFloor4Farmer.dict_of_defeats[phase] += 1

        fight_complete_msg = (
            f"We beat Floor4 a total of {IFloor4Farmer.success_count}/{IFloor4Farmer.total_count} times."
        )
        logger.info(fight_complete_msg)
        if IFloor4Farmer.success_count >= self.max_runs:
            print("Reached maximum number of clears, exiting farmer.")
            self.current_state = States.EXIT_FARMER
            return

        # Don't log the defeats here, only on `exit_message()`
        self.exit_message()

        # Go straight to the original states
        self.current_state = States.PROCEED_TO_FLOOR

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to regular farming"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming Floor 4.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DB

    def run(self):

        print(f"Fighting Floor 4 hard, starting in state {self.current_state}.")

        while True:

            check_for_reconnect()

            # Check if we need to log in again!
            self.check_for_login_state()

            if self.current_state == States.GOING_TO_DB:
                self.going_to_db_state()

            elif self.current_state == States.PROCEED_TO_FLOOR:
                self.proceed_to_floor_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == GlobalStates.DAILY_RESET:
                self.daily_reset_state()

            elif self.current_state == GlobalStates.CHECK_IN:
                self.check_in_state(initial_state=States.GOING_TO_DB)

            elif self.current_state == GlobalStates.DAILIES_STATE:
                self.dailies_state()

            elif self.current_state == GlobalStates.FORTUNE_CARD:
                self.fortune_card_state()

            elif self.current_state == GlobalStates.LOGIN_SCREEN:
                self.login_screen_state(initial_state=States.GOING_TO_DB)

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.8)
