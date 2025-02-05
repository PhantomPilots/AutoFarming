import threading
import time
from collections import defaultdict
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.dogs_fighter import DogsFighter, IFighter
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    determine_db_floor,
    find,
    find_and_click,
    find_floor_coordinates,
)

logger = LoggerWrapper("DogsLogger", log_file="dogs_logger.log")


class States(Enum):
    GOING_TO_DOGS = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_DOGS = 4


class DogsFarmer(IFarmer):

    # Keep track of how many times we've defeated floor 3
    num_floor_3_victories = 0
    num_losses = 0
    current_floor = 1

    def __init__(self, battle_strategy: IBattleStrategy, starting_state=States.GOING_TO_DOGS, max_stamina_pots="inf"):

        # Initialize the current state
        self.current_state = starting_state

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        # Using the previous BirdFighter!
        self.fighter: IFighter = DogsFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

        # Placeholder for the fight thread
        self.fight_thread = None

        self.max_stamina_pots = float(max_stamina_pots)
        if self.max_stamina_pots < float("inf"):
            print(f"We're gonna use at most {self.max_stamina_pots} stamina pots.")

    def exit_message(self):
        logger.info(
            f"We beat at least {DogsFarmer.num_floor_3_victories*3} floors and lost {DogsFarmer.num_losses} times."
        )
        logger.info(f"We used {IFarmer.stamina_pots} stamina pots.")

        self.print_defeats()

    def going_to_dogs_state(self):
        """This should be the original state. Let's go to the dogs menu"""
        screenshot, window_location = capture_window()

        # Go into the 'Dogs' section
        if find_and_click(vio.skollandhati, screenshot, window_location):
            return

        if find(vio.empty_party, screenshot):
            # We have to set the party.
            print("Moving to state SET_PARTY")
            self.current_state = States.SET_PARTY

        elif find(vio.available_floor, screenshot, threshold=0.8):
            # We're in the Bird screen, but assuming the party is set. Go to READY FIGHT FLOOR 1 state!
            print("Moving to state READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT

    def set_party_state(self):

        screenshot, window_location = capture_window()

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            # We're ready to start fighting floor 1!
            print("Moving to state READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT
            return

        # Click on "set party"
        find_and_click(vio.empty_party, screenshot, window_location)

        # Save the party
        find_and_click(vio.save_party, screenshot, window_location, threshold=0.8)

    def proceed_to_floor_state(self):
        """Start the floor fight!"""

        screenshot, window_location = capture_window()

        # In case we didn't properly click it
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # Get the floor coordinates of the available floor, and click on the corresponding floor
        if floor_coordinates := find_floor_coordinates(screenshot, window_location):
            find_and_click(
                vio.available_floor,
                screenshot,
                window_location,
                point_coordinates=floor_coordinates,
                threshold=0.8,
            )

        # We may need to restore stamina
        if IFarmer.stamina_pots < self.max_stamina_pots and find_and_click(
            vio.restore_stamina, screenshot, window_location
        ):
            # Keep track of how many stamina pots we used
            IFarmer.stamina_pots += 1
            return
        elif find(vio.restore_stamina, screenshot):
            print(f"We reached the max number of {self.max_stamina_pots} stamina pots, not restoring stamina.")

        if find(vio.startbutton, screenshot):
            # We can determine the floor number!
            DogsFarmer.current_floor = determine_db_floor(screenshot)

        # Click on start
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # The 'Start' button went through, fight starting!
            print("Moving to state FIGHTING_FLOOR")
            self.current_state = States.FIGHTING_FLOOR

    def fighting_floor(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        # Skip the dogs screen
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.8)

        # In case we see a 'Close' pop-up
        find_and_click(vio.close, screenshot, window_location, threshold=0.8)

        # Set the fight thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            print("Dogs fighter started!")
            self.fight_thread = threading.Thread(target=self.fighter.run, daemon=True, args=(self.current_floor,))
            self.fight_thread.start()

    def fight_complete_callback(self, victory=True, phase="unknown", **kwargs):
        """Called when the fight logic completes."""

        if victory:
            # Transition to another state or perform clean-up actions
            print(f"Floor {DogsFarmer.current_floor} complete! Going back to the original state")
            if DogsFarmer.current_floor == 3:
                print("We defeated all 3 floors, gotta reset the DB.")
                self.current_state = States.RESETTING_DOGS
                DogsFarmer.num_floor_3_victories += 1
            else:
                # Go straight to the original states
                print("Moving to GOING_TO_DOGS")
                self.current_state = States.GOING_TO_DOGS

        else:
            DogsFarmer.num_losses += 1
            print("We lost :(")
            # Update the dictionary of defeats
            IFarmer.dict_of_defeats[f"Floor {DogsFarmer.current_floor} Phase {phase}"] += 1
            self.current_state = States.RESETTING_DOGS

        print(f"We beat {DogsFarmer.num_floor_3_victories} times Floor 3 and lost {DogsFarmer.num_losses} times.")
        print(f"We've used {IFarmer.stamina_pots} stamina pots so far.")
        self.print_defeats()

    def resetting_dogs_state(self):
        """If we've finished floor 3, we need to reset the dogs"""

        screenshot, window_location = capture_window()

        # Click on the confirmation window...
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # Click on the 'reset' button
        find_and_click(vio.reset_demonic_beast, screenshot, window_location, threshold=0.6)

        # Once we see the main dogs screen again, we can move the the original state
        if find(vio.empty_party, screenshot):
            print("Moving to the original state, GOING_TO_DOGS")
            self.current_state = States.GOING_TO_DOGS

    def run(self):

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_DOGS:
                self.going_to_dogs_state()

            elif self.current_state == States.SET_PARTY:
                self.set_party_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.proceed_to_floor_state()

            elif self.current_state == States.FIGHTING_FLOOR:
                self.fighting_floor()

            elif self.current_state == States.RESETTING_DOGS:
                self.resetting_dogs_state()

            time.sleep(0.8)
