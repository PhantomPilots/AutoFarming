import threading
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.snake_fighter import IFighter, SnakeFighter
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    determine_db_floor,
    find,
    find_and_click,
    find_floor_coordinates,
)

logger = LoggerWrapper("SnakeLogger", log_file="snake_logger.log")


class States(Enum):
    GOING_TO_SNAKE = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_SNAKE = 4


class SnakeFarmer(IFarmer):

    current_floor = 1

    # Keep track of how many times we've defeated floor 3
    num_floor_3_victories = 0
    num_losses = 0

    def __init__(self, battle_strategy: IBattleStrategy, starting_state=States.GOING_TO_SNAKE):

        # Initialize the current state
        self.current_state = starting_state

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        # Using the previous BirdFighter!
        self.fighter: IFighter = SnakeFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

        # Placeholder for the fight thread
        self.fight_thread = None

    def exit_message(self):
        logger.info(
            f"We beat at least {SnakeFarmer.num_floor_3_victories*3} floors and lost {SnakeFarmer.num_losses} times."
        )
        logger.info(f"We used {IFarmer.stamina_pots} stamina pots.")

    def going_to_snake_state(self):
        """This should be the original state. Let's go to the snake menu"""
        screenshot, window_location = capture_window()

        # Go into the 'Snake' section
        if find_and_click(vio.nidhoggr, screenshot, window_location):
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

        if find_and_click(vio.ok_save_party, screenshot, window_location):
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

        #

        # In case we didn't properly click it
        find_and_click(vio.ok_save_party, screenshot, window_location)

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
            # Keep track of how many stamina pots we used
            IFarmer.stamina_pots += 1
            return

        if find(vio.startbutton, screenshot):
            # We can determine the floor number!
            SnakeFarmer.current_floor = determine_db_floor(screenshot)
            print(f"We're gonna fight floor {SnakeFarmer.current_floor}")

        # Click on start
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # The 'Start' button went through, fight starting!
            print("Moving to state FIGHTING_FLOOR")
            self.current_state = States.FIGHTING_FLOOR

    def fighting_floor(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        # Skip the snake screen
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.8)

        # In case we see a 'Close' pop-up
        find_and_click(vio.close, screenshot, window_location, threshold=0.8)

        # Set the fight thread
        if self.fight_thread is None or not self.fight_thread.is_alive():
            # TODO: Enable when the rest of the farming logic is done
            self.fight_thread = threading.Thread(
                target=self.fighter.run, daemon=True, args=(SnakeFarmer.current_floor,)
            )
            self.fight_thread.start()
            print("Snake fighter started!")

    def fight_complete_callback(self, victory=True, floor_defeated=None):
        """Called when the fight logic completes."""

        if victory:
            # Transition to another state or perform clean-up actions
            print("Floor complete! Going back to the original state")
            if floor_defeated == 3:
                print("We defeated all 3 floors, gotta reset the DB.")
                self.current_state = States.RESETTING_SNAKE
                SnakeFarmer.num_floor_3_victories += 1
                print(f"We beat {SnakeFarmer.num_floor_3_victories*3} floors and lost {SnakeFarmer.num_losses} times")
                return

            # Go straight to the original states
            print("Moving to GOING_TO_SNAKE")
            self.current_state = States.GOING_TO_SNAKE

        else:
            print("The Snake fighter told me we lost... :/")
            print("Resetting the team in case the saved team has very little health")
            SnakeFarmer.num_losses += 1
            print(
                f"We lost... We beat {SnakeFarmer.num_floor_3_victories*3} floors and lost {SnakeFarmer.num_losses} times."
            )
            self.current_state = States.RESETTING_SNAKE

    def resetting_snake_state(self):
        """If we've finished floor 3, we need to reset the Snake"""

        screenshot, window_location = capture_window()

        # Click on the confirmation window...
        find_and_click(vio.bird_okay, screenshot, window_location)

        # Click on the 'reset' button
        find_and_click(vio.reset_demonic_beast, screenshot, window_location, threshold=0.6)

        # Once we see the main Snake screen again, we can move the the original state
        if find(vio.empty_party, screenshot):
            print("Moving to the original state, GOING_TO_SNAKE")
            self.current_state = States.GOING_TO_SNAKE

    def run(self):

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_SNAKE:
                self.going_to_snake_state()

            elif self.current_state == States.SET_PARTY:
                self.set_party_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.proceed_to_floor_state()

            elif self.current_state == States.FIGHTING_FLOOR:
                self.fighting_floor()

            elif self.current_state == States.RESETTING_SNAKE:
                self.resetting_snake_state()

            time.sleep(0.8)
