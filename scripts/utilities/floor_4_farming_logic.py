import logging
import os
import threading
import time
from collections import defaultdict
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter, IFighter
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
)

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    filename=os.path.join("logs", "floor_4.log"),
    filemode="a",  # 'a' for append mode if you want to continue logging to the same file
)

# Create a logger instance
logger = logging.getLogger()


class States(Enum):
    GOING_TO_FLOOR = 0
    FIGHTING = 1
    READY_TO_FIGHT = 2


class Floor4Farmer(IFarmer):

    def __init__(self, battle_strategy: IBattleStrategy, starting_state: States, **kargs):

        # For type helping
        self.current_state = starting_state
        # We will need to develop a specific battle strategy for it
        self.battle_strategy = battle_strategy

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete
        self.bird_fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

        # Placeholder for the thread that will call the fighter logic
        self.fight_thread = None

        # Keep track of how many times we've beat/lost the fight
        self.success_count = 0
        self.total_count = 0
        self.dict_of_defeats = defaultdict(int)

    def exit_message(self):
        print(f"We've beat Floor 4 of Bird {self.success_count} out of {self.total_count} times.")
        # Log the defeats
        defeat_msg = self._print_defeats()
        logger.info(defeat_msg)

    def stop_fighter_thread(self):
        """Stop the fighter thread!"""
        self.bird_fighter.stop_fighter()

    def _print_defeats(self):
        """Generate a string message to log"""
        str_msg = "Defeats:\n"
        for phase, count in self.dict_of_defeats.items():
            str_msg += f"* Phase {phase} -> Lost {count} times.\n"

        print(str_msg)
        return str_msg

    def going_to_floor_state(self):

        screenshot, window_location = capture_window()

        # In case we need to unlock the floor
        find_and_click(vio.fb_ok_button, screenshot, window_location)

        # Click on floor 4 if it's available
        find_and_click(vio.floor_3_cleard_bird, screenshot, window_location)
        find_and_click(vio.floor_3_cleard_2_bird, screenshot, window_location)

        if find(vio.startbutton, screenshot):
            # We can move to the next state
            print("Let's GET READY to fight.")
            self.current_state = States.READY_TO_FIGHT

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # Restore stamina if we need to
        find_and_click(vio.restore_stamina, screenshot, window_location)

        # Try to start the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We can move to the next state
            print("Moving to FIGHTING!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location)

        # Set the fighter thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            print("Bird fight started!")
            self.fight_thread = threading.Thread(target=self.bird_fighter.run, name="Floor4FighterThread", daemon=True)
            self.fight_thread.start()

    def fight_complete_callback(self, victory=True, **kwargs):
        """Called when the fight logic completes."""

        self.total_count += 1
        if victory:
            # Transition to another state or perform clean-up actions
            self.success_count += 1
            print("FLOOR 4 COMPLETE, WOOO!")
        else:
            phase = kwargs.get("phase", None)
            print(f"The bird fighter told me they lost{f' on phase {phase}' if phase is not None else ''}... :/")
            # Increment the defeat count of the corresponding phase
            if phase is not None:
                self.dict_of_defeats[phase] += 1

        fight_complete_msg = f"We beat the bird {self.success_count}/{self.total_count} times."
        print(fight_complete_msg)
        logger.info(fight_complete_msg)

        # Don't log the defeats here, only on `exit_message()`
        self._print_defeats()

        # Go straight to the original states
        self.current_state = States.GOING_TO_FLOOR

    def run(self):

        print(f"Fighting Floor 4 hard, starting in state {self.current_state}.")

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_FLOOR:
                self.going_to_floor_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            time.sleep(0.8)
