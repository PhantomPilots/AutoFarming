import abc
import threading
import time
from enum import Enum

import pyautogui as pyautogui
import utilities.vision_images as vio

# Import all images
from utilities.general_farmer_interface import MINUTES_TO_WAIT_BEFORE_LOGIN, IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    determine_db_floor,
    find,
    find_and_click,
    find_floor_coordinates,
)

logger = LoggerWrapper("DBLogger", log_file="demonic_beast_logger.log")


class States(Enum):
    GOING_TO_DB = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_DB = 4
    EXIT_FARMER = 5


class DemonicBeastFarmer(IFarmer, abc.ABC):

    current_floor = 3

    # Keep track of how many times we've defeated floor 3
    num_floor_3_victories = 0
    num_victories = 0
    num_losses = 0

    def __init__(
        self,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        max_floor_3_clears="inf",
        demonic_beast_image: vio.Vision | None = None,
        reset_after_defeat=False,
        logger=logger,
        password: str | None = None,
    ):
        # NOTE: In derived classes, make sure to initialize a `self.fighter` instance with the desired fighter and battle strategy

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {MINUTES_TO_WAIT_BEFORE_LOGIN} mins. before attempting a log in.")

        # Save the image we want
        self.db_image = demonic_beast_image

        # Save the logger
        self.logger = logger

        # After we lose, should we reset the Demonic Beast?
        self.reset_after_defeat = reset_after_defeat
        if reset_after_defeat:
            print("We're gonna reset the DB if we lose.")

        # Initialize the current state
        self.current_state = starting_state

        # Placeholder for the fight thread
        self.fight_thread = None

        # Ending conditions:
        # * One will just stop using stamina pots and wait till enough stamina is available.
        # * The other will exit the farmer when enough floor 3 clears have been reached (especially useful for floor 4's)
        self.max_stamina_pots = float(max_stamina_pots)
        if self.max_stamina_pots < float("inf"):
            print(f"We're gonna use at most {self.max_stamina_pots} stamina pots.")

        self.max_floor_3_clears = float(max_floor_3_clears)
        if self.max_floor_3_clears < float("inf"):
            print(f"We're gonna clear floor 3 at most {int(self.max_floor_3_clears)} times.")

    def exit_message(self):
        self.logger.info(
            f"We beat {DemonicBeastFarmer.num_victories} floors, {DemonicBeastFarmer.num_floor_3_victories} times floor 3, and lost {DemonicBeastFarmer.num_losses} times."
        )
        self.logger.info(f"We used {IFarmer.stamina_pots} stamina pots.")

        self.print_defeats()

    def going_to_db_state(self):
        """This should be the original state. Let's go to the Demonic Beast menu"""
        screenshot, window_location = capture_window()

        # TODO: Implement, currently not working
        # # First of all, if we have a dead unit, reset the demonic beast!
        # if find(vio.dead_unit, screenshot, threshold=0.6):
        #     self.logger.info("We have a dead unit! Resetting the demonic beast.")
        #     self.current_state = States.RESETTING_DB
        #     return

        # Go into the 'Demonic Beast' section
        if find_and_click(self.db_image, screenshot, window_location):
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
        find_and_click(vio.save_party, screenshot, window_location)

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
            with IFarmer._lock:
                DemonicBeastFarmer.current_floor = determine_db_floor(screenshot)

        # Click on start
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # The 'Start' button went through, fight starting!
            print("Moving to state FIGHTING_FLOOR")
            self.current_state = States.FIGHTING_FLOOR

    def fighting_floor(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        # Skip the Demonic Beast screen
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.6)

        # In case we see a 'Close' pop-up
        find_and_click(vio.close, screenshot, window_location, threshold=0.8)

        # If first reward
        find_and_click(vio.first_reward, screenshot, window_location)

        # Set the fight thread ONLY if we haven't changed the current state (due to a callback, for instance!)
        if (self.fight_thread is None or not self.fight_thread.is_alive()) and (
            self.current_state == States.FIGHTING_FLOOR
        ):
            self.fight_thread = threading.Thread(
                target=self.fighter.run, daemon=True, args=(DemonicBeastFarmer.current_floor,)
            )
            self.fight_thread.start()
            print("DemonicBeast fighter started!")

    def fight_complete_callback(self, victory=True, phase="unknown"):
        """Called when the fight logic completes."""

        with IFarmer._lock:
            if victory:
                DemonicBeastFarmer.num_victories += 1

                print(f"Floor {DemonicBeastFarmer.current_floor} complete!")

                # Update the floor number
                DemonicBeastFarmer.current_floor = (DemonicBeastFarmer.current_floor % 3) + 1

                # Transition to another state or perform clean-up actions
                if DemonicBeastFarmer.current_floor == 1:  # Since we updated it already beforehand!
                    DemonicBeastFarmer.num_floor_3_victories += 1

                    # Check if we need to exit the farmer due to reaching the max number of desired floor 3 clears
                    if DemonicBeastFarmer.num_floor_3_victories >= self.max_floor_3_clears:
                        print("We've reached the desired number of floor 3 clears, closing the farmer.")
                        self.current_state = States.EXIT_FARMER
                    else:
                        # Just reset the team
                        print("We defeated all 3 floors, gotta reset the DB.")
                        self.current_state = States.RESETTING_DB

                else:
                    # Go straight to the original states
                    print("Moving to GOING_TO_DB")
                    self.current_state = States.GOING_TO_DB

            else:
                print("The Demonic Beast fighter told me we lost... :/")
                # print("Resetting the team in case the saved team has very little health")
                DemonicBeastFarmer.num_losses += 1
                IFarmer.dict_of_defeats[f"Floor {DemonicBeastFarmer.current_floor} Phase {phase}"] += 1

                if self.reset_after_defeat:
                    self.current_state = States.RESETTING_DB
                else:
                    self.current_state = States.GOING_TO_DB

            self.exit_message()

    def resetting_db_state(self):
        """If we've finished floor 3, we need to reset the Demonic Beast"""

        screenshot, window_location = capture_window()

        # Click on the confirmation window...
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # Click on the 'reset' button
        find_and_click(vio.reset_demonic_beast, screenshot, window_location, threshold=0.6)

        # Once we see the main Demonic Beast screen again, we can move the the original state
        if find(vio.empty_party, screenshot):
            print("Moving to the original state, GOING_TO_DB")
            self.current_state = States.GOING_TO_DB

    def run(self):

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_DB:
                self.going_to_db_state()

            elif self.current_state == States.SET_PARTY:
                self.set_party_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.proceed_to_floor_state()

            elif self.current_state == States.FIGHTING_FLOOR:
                self.fighting_floor()

            elif self.current_state == States.RESETTING_DB:
                self.resetting_db_state()

            elif self.current_floor == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.8)
