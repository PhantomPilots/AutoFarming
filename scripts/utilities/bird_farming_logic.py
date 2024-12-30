import threading
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter, IFighter
from utilities.coordinates import Coordinates
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

logger = LoggerWrapper(name="BirdLogger", log_file="bird_logger.log")


class States(Enum):
    GOING_TO_BIRD = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_BIRD = 4
    EXIT_FARMER = 5


class BirdFarmer(IFarmer):

    # Need to be static in case we
    success_count = 0
    total_count = 0
    current_floor = 1

    # How many floor 3 clears we want
    num_floor_3_clears = "inf"

    def __init__(self, battle_strategy: IBattleStrategy, starting_state=States.GOING_TO_BIRD, num_floor_3_clears="inf"):

        # Initialize the current state
        self.current_state = starting_state

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        # Using the previous BirdFighter!
        self.fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

        BirdFarmer.num_floor_3_clears = float(num_floor_3_clears)
        if BirdFarmer.num_floor_3_clears < float("inf"):
            print(f"We're gonna clear floor 3 at most {num_floor_3_clears} times.")

        # Placeholder for the fight thread
        self.fight_thread = None

    def exit_message(self):
        # super().exit_message() # Not needed anymore due to the logger below
        logger.info(f"We beat floor 3 of bird {BirdFarmer.success_count}/{BirdFarmer.total_count} times.")
        logger.info(f"We used {IFarmer.stamina_pots} stamina pots.")

    def going_to_bird_state(self):
        """This should be the original state. Let's go to the bird menu"""
        screenshot, window_location = capture_window()

        # If we're back in the tavern, click on the battle menu.
        # TODO: Remove the hardcoded coordinates, or at least make them dynamic with respect to the window size
        find_and_click(
            vio.main_menu,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("battle_menu"),
            threshold=0.7,
        )

        # If we're in the battle menu, click on Demonic Beast
        find_and_click(vio.demonic_beast, screenshot, window_location)

        # Go into the 'Bird' section
        find_and_click(vio.hraesvelgr, screenshot, window_location)

        if find(vio.empty_party, screenshot):
            # We have to set the party.
            print("Moving to state SET_PARTY")
            self.current_state = States.SET_PARTY
            return

        elif find(vio.available_floor, screenshot, threshold=0.8):
            # We're in the Bird screen, but assuming the party is set. Go to READY FIGHT FLOOR 1 state!
            print("Moving to state READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT
            return

        # Double-check that floor 3 is not cleared
        elif find(vio.floor_3_cleard_bird, screenshot, threshold=0.8) or find(
            vio.floor_3_cleard_2_bird, screenshot, threshold=0.8
        ):
            print("Floor 3 is cleared, we need to reset the bird!")
            self.current_state = States.RESETTING_BIRD
            return

        # # In case we're not in the "path to the bird", but we see the tavern location
        # if find_and_click(vio.tavern, screenshot, window_location):
        #     print("We're not in the tavern yet, let's first go there...")

    def set_party_state(self):

        screenshot, window_location = capture_window()

        if find_and_click(vio.ok_save_party, screenshot, window_location):
            # We're ready to start fighting floor 1!
            print("Moving to state READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT
            return

        # Click on "set party"
        find_and_click(vio.empty_party, screenshot, window_location)

        # Save the party
        find_and_click(vio.save_party, screenshot, window_location)

    def proceed_to_floor_state(self):
        """Start the floor fight!"""

        screenshot, window_location = capture_window()

        # In case we didn't properly click it before
        find_and_click(vio.ok_save_party, screenshot, window_location)

        # First double-check that floor 3 is not cleared
        if find(vio.floor_3_cleard_bird, screenshot, threshold=0.8) or find(
            vio.floor_3_cleard_2_bird, screenshot, threshold=0.8
        ):
            print("Floor 3 is cleared, we need to reset the bird!")
            self.current_state = States.RESETTING_BIRD
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

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            # Return so that we don't try to click START right after
            IFarmer.stamina_pots += 1
            return

        if find(vio.startbutton, screenshot):
            # We can determine the floor number!
            BirdFarmer.current_floor = determine_db_floor(screenshot)

        # Click on start
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # The 'Start' button went through, fight starting!
            print("Moving to state FIGHTING_FLOOR")
            self.current_state = States.FIGHTING_FLOOR

    def fighting_floor(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        # Skip the bird screen
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.8)

        # If first reward
        find_and_click(vio.first_reward, screenshot, window_location)

        # Set the fight thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            print("Bird fight started!")
            self.fight_thread = threading.Thread(target=self.fighter.run, name="BirdFighterTread", daemon=True)
            self.fight_thread.start()

    def fight_complete_callback(self, victory=True, phase="unknown"):
        """Called when the fight logic completes."""

        if BirdFarmer.current_floor == 3:
            BirdFarmer.total_count += 1
            if victory:
                BirdFarmer.success_count += 1
            logger.info(f"We beat floor 3 of bird {BirdFarmer.success_count}/{BirdFarmer.total_count} times.")

            if BirdFarmer.success_count >= BirdFarmer.num_floor_3_clears:
                print("We've reached the desired number of floor 3 clears, closing the farmer.")
                self.current_state = States.EXIT_FARMER
                return

        if victory:
            print(f"Floor {BirdFarmer.current_floor} complete! Going back to the original state")

        else:
            print(f"The bird fighter told me they lost on phase {phase}... ")
            # Let's reset the bird
            self.current_state = States.RESETTING_BIRD
            return

        print(f"We've used {IFarmer.stamina_pots} stamina pots so far.")
        # Transition to the original states
        self.current_state = States.GOING_TO_BIRD

    def resetting_bird_state(self):
        """If we've finished floor 3, we need to reset the bird"""

        screenshot, window_location = capture_window()

        # Click on the confirmation window...
        find_and_click(vio.bird_okay, screenshot, window_location)

        # Click on the 'reset' button
        find_and_click(vio.reset_demonic_beast, screenshot, window_location, threshold=0.6)

        # Once we see the main bird screen again, we can move the the original state
        if find(vio.empty_party, screenshot):
            print("Moving to the original state, GOING_TO_BIRD")
            self.current_state = States.GOING_TO_BIRD

    def run(self):

        print(f"Farming floors 1-3 of Bird, starting in state {self.current_state}.")

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_BIRD:
                self.going_to_bird_state()

            elif self.current_state == States.SET_PARTY:
                self.set_party_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.proceed_to_floor_state()

            elif self.current_state == States.FIGHTING_FLOOR:
                self.fighting_floor()

            elif self.current_state == States.RESETTING_BIRD:
                self.resetting_bird_state()

            elif self.current_floor == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.8)
