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
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
    find_floor_coordinates,
)


class States(Enum):
    GOING_TO_BIRD = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_BIRD = 4


class BirdFarmer(IFarmer):

    # Need to be static in case we
    success_count = 0
    total_count = 0

    def __init__(self, battle_strategy: IBattleStrategy, starting_state=States.GOING_TO_BIRD):

        # Initialize the current state
        self.current_state = starting_state

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        # Using the previous BirdFighter!
        self.bird_fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

        # Placeholder for the fight thread
        self.fight_thread = None

        # Keep track of the next floor to fight on
        self.current_floor = 1

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

        elif find(vio.available_floor, screenshot):
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

            print("Resetting the floor counter to 1")
            self.current_floor = 1
            return

        # Click on "set party"
        find_and_click(vio.empty_party, screenshot, window_location)

        # Save the party
        find_and_click(vio.save_party, screenshot, window_location, threshold=0.8)

    def proceed_to_floor_state(self):
        """Start the floor fight!"""

        screenshot, window_location = capture_window()

        # First double-check that floor 3 is not cleared
        if find(vio.floor_3_cleard_bird, screenshot, threshold=0.8) or find(
            vio.floor_3_cleard_2_bird, screenshot, threshold=0.9
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
            )

        # We may need to restore stamina
        find_and_click(vio.restore_stamina, screenshot, window_location)

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

        # Set the fight thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            print("Bird fight started!")
            self.fight_thread = threading.Thread(target=self.bird_fighter.run, name="BirdFighterTread", daemon=True)
            self.fight_thread.start()

    def fight_complete_callback(self, victory=True):
        """Called when the fight logic completes."""

        if self.current_floor == 3:
            BirdFarmer.total_count += 1
            if victory:
                BirdFarmer.success_count += 1
            print(f"We beat the bird {BirdFarmer.success_count}/{BirdFarmer.total_count} times.")

        if victory:
            print(f"Floor {self.current_floor} complete! Going back to the original state")
            # Update the new bird floor
            self.current_floor = (self.current_floor % 3) + 1
        else:
            print("The bird fighter told me they lost... :/")

        # Transition to the original states
        self.current_state = States.GOING_TO_BIRD

    def resetting_bird_state(self):
        """If we've finished floor 3, we need to reset the bird"""

        screenshot, window_location = capture_window()

        # Click on the confirmation window...
        find_and_click(vio.bird_okay, screenshot, window_location)

        # Click on the 'reset' button
        find_and_click(vio.reset_bird, screenshot, window_location, threshold=0.6)

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
                # print("We've finished all 3 floors, exiting...")
                # return

            time.sleep(0.8)
