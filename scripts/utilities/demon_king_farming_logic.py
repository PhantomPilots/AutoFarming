import sys
import threading
import time
from enum import Enum, auto

import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.card_data import CardColors
from utilities.constants import MINUTES_TO_WAIT_BEFORE_LOGIN
from utilities.coordinates import Coordinates
from utilities.dk_fighter import DemonKingFighter
from utilities.general_farmer_interface import CHECK_IN_HOUR, IFarmer
from utilities.general_farmer_interface import States as GlobalStates
from utilities.general_fighter_interface import IBattleStrategy, IFighter
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    click_im,
    crop_image,
    determine_unit_types,
    find,
    find_and_click,
    press_key,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DemonKingLogger", log_to_file=False)


class States(Enum):
    GOING_TO_DK = auto()
    OPEN_DK = auto()
    PREPARE_FIGHT = auto()
    FIGHTING = auto()


class DemonKingFarmer(IFarmer):

    num_fights = 0

    num_clears = 0

    dk_difficulty = "hell"

    unit_colors: list[CardColors] = []

    def __init__(
        self,
        starting_state=States.GOING_TO_DK,
        battle_strategy: IBattleStrategy = None,  # No need
        dk_difficulty: str = "hell",  # Demon King difficulty
        num_clears: str | float | int = 20,  # How many coins to use at most
        **kwargs,
    ):
        # To initialize the Daily Farmer thread
        super().__init__()

        self.current_state = starting_state

        if dk_difficulty != "hard":
            print("[WARN] Sorry, `hard` difficulty is the most efficient one! So the only one supported.")
            dk_difficulty = "hard"
        DemonKingFarmer.dk_difficulty = dk_difficulty

        self.max_clears = float(num_clears)
        if self.max_clears < float("inf"):
            print(f"We'll do at most {int(self.max_clears)} runs")

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete
        self.fighter: IFighter = DemonKingFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )
        self.dk_fighting_thread: threading.Thread = None

    def _click_difficulty(self, screenshot: np.ndarray, window_location: tuple):
        """Click on the desired difficulty"""
        if DemonKingFarmer.dk_difficulty == "hell":
            find_and_click(vio.dk_hell, screenshot, window_location)
        elif DemonKingFarmer.dk_difficulty == "extreme":
            find_and_click(vio.dk_extreme, screenshot, window_location)
        elif DemonKingFarmer.dk_difficulty == "hard":
            find_and_click(vio.dk_hard, screenshot, window_location)

    def going_to_dk_state(self):
        screenshot, window_location = capture_window()

        # In case we come from a complete fight
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.register_coins, screenshot):
            self.current_state = States.OPEN_DK
            print(f"Going to {self.current_state}")
            return

        if find(vio.startbutton, screenshot):
            self.current_state = States.FIGHTING
            print(f"Going to {self.current_state}")
            return

        self._click_difficulty(screenshot, window_location)

        find_and_click(vio.demon_king, screenshot, window_location, threshold=0.8)
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

    def open_dk_state(self):
        """Open the DK fight"""
        screenshot, window_location = capture_window()

        time.sleep(1.5)
        click_and_sleep(vio.x3, screenshot, window_location, threshold=0.8, sleep_time=1)
        click_and_sleep(vio.register_coins, screenshot, window_location, sleep_time=1)
        if find_and_click(vio.apply, screenshot, window_location):
            self.current_state = States.PREPARE_FIGHT
            print(f"Going to {self.current_state}")

    def prepare_fight_state(self):
        """Let's prepare the fight"""
        screenshot, window_location = capture_window()

        if find(vio.apply, screenshot):
            print("We haven't successfully opened the DK fight, let's try again...")
            self.current_state = States.OPEN_DK
            return

        self._click_difficulty(screenshot, window_location)

        if find(vio.startbutton, screenshot):
            self.current_state = States.FIGHTING
            print(f"Going to {self.current_state}")

    def store_unit_types(self):
        """Let's store the colors for each unit in our dictionary..."""
        unit_colors_team_a = determine_unit_types()
        DemonKingFarmer.unit_colors = unit_colors_team_a
        print(f"Stored these unit types: {[utype.name for utype in DemonKingFarmer.unit_colors]}")

    def fighting_state(self):
        """Currently fighting... We should be using the DK fighter"""

        screenshot, window_location = capture_window()

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            logger.info(f"We've used {IFarmer.stamina_pots} stamina pots")
            return

        if find(vio.startbutton, screenshot):
            print("Let's store unit types...")
            self.store_unit_types()
            find_and_click(vio.startbutton, screenshot, window_location)

        find_and_click(vio.skip, screenshot, window_location)

        if self.dk_fighting_thread is None or not self.dk_fighting_thread.is_alive():
            print("Let's start the DK fight!")
            self.dk_fighting_thread = threading.Thread(
                target=self.fighter.run, daemon=True, args=(DemonKingFarmer.unit_colors,)
            )
            self.dk_fighting_thread.start()

    def fight_complete_callback(self, victory: bool = None):
        """Callback called by the DemonKingFighter when the fight is over (because we won or lost)"""

        if victory:
            DemonKingFarmer.num_clears += 1
            print(f"Fight complete! Cleared DK {DemonKingFarmer.num_clears} times.")
            if DemonKingFarmer.num_clears >= self.max_clears:
                raise KeyboardInterrupt("We've cleared the DK enough times, stopping the farming.")
        else:
            print("We lost :(")

        self.current_state = States.GOING_TO_DK

    def run(self):

        while True:
            # Try to reconnect first
            if not (success := check_for_reconnect()):
                # We had to restart the game! Let's log back in immediately
                print("Let's try to log back in immediately...")
                IFarmer.first_login = True

            # Check if we need to log in again!
            self.check_for_login_state()

            if self.current_state == States.GOING_TO_DK:
                self.going_to_dk_state()

            elif self.current_state == States.OPEN_DK:
                self.open_dk_state()

            elif self.current_state == States.PREPARE_FIGHT:
                self.prepare_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            # We need the loop to run very fast
            time.sleep(0.5)
