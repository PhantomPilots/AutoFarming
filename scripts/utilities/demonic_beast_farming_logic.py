import abc
import threading
import time
from enum import Enum

import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import (
    CHECK_IN_HOUR,
    MINUTES_TO_WAIT_BEFORE_LOGIN,
    IFarmer,
)
from utilities.general_farmer_interface import States as GlobalStates
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    crop_image,
    drag_im,
    find,
    find_and_click,
    find_floor_coordinates,
    screenshot_testing,
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

    current_floor = 1

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
        password: str | None = None,
        do_dailies=False,
        logger=logger,
    ):
        super().__init__()

        # NOTE: In derived classes, make sure to initialize a `self.fighter` instance with the desired fighter and battle strategy

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {MINUTES_TO_WAIT_BEFORE_LOGIN} mins. before attempting a log in.")

        # In case we want to do dailies at the specified hour
        self.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming DemonicBeast at {CHECK_IN_HOUR} PT to do our dailies!")

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

        # For the login/dailies
        IFarmer.daily_farmer.set_daily_pvp(True)
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

    def exit_message(self):
        self.logger.info(
            f"We beat {DemonicBeastFarmer.num_victories} floors, {DemonicBeastFarmer.num_floor_3_victories} times floor 3, and lost {DemonicBeastFarmer.num_losses} times."
        )
        self.logger.info(f"We used {IFarmer.stamina_pots} stamina pots.")

        self.print_defeats()

    def going_to_db_state(self):
        """This should be the original state. Let's go to the Demonic Beast menu"""
        screenshot, window_location = capture_window()

        # First of all, check whether it's time to do our dailies!
        if self.check_for_dailies():
            return
        self.maybe_reset_daily_checkin_flag()

        # When coming from 'resetting DB'
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # If we're back in the tavern, click on the battle menu.
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # If we're in the battle menu, click on Demonic Beast
        find_and_click(vio.demonic_beast, screenshot, window_location)

        # If we see we're inside the DB selection screen but don't see our DemonicBeast,
        # swipe right and try again
        if find(vio.demonic_beast_battle, screenshot) and not find(self.db_image, screenshot):
            # Swipe to the right!
            print("Wrong demonic beast, searching the right one...")
            drag_im(
                Coordinates.get_coordinates("right_swipe"),
                Coordinates.get_coordinates("left_swipe"),
                window_location,
            )
            time.sleep(0.5)
            return

        # Go into the 'Demonic Beast' section
        find_and_click(self.db_image, screenshot, window_location)

        if find(vio.empty_party, screenshot) or find(vio.save_party, screenshot):
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

    def determine_db_floor(self, screenshot: np.ndarray, threshold=0.9) -> int:
        """Determine the Demonic Beast floor"""
        # sourcery skip: assign-if-exp, reintroduce-else
        floor_img_region = crop_image(
            screenshot,
            Coordinates.get_coordinates("floor_top_left"),
            Coordinates.get_coordinates("floor_bottom_right"),
        )

        # display_image(floor_img_region)
        # screenshot_testing(floor_img_region, vio.floor2, threshold=threshold)

        # Default
        db_floor = -1

        if find(vio.floor2, floor_img_region, threshold=threshold):
            db_floor = 2
        elif find(vio.floor3, floor_img_region, threshold=threshold):
            db_floor = 3
        elif find(vio.floor1, floor_img_region, threshold=threshold):
            db_floor = 1

        print(f"We're gonna fight floor {db_floor}.")

        return db_floor

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
                DemonicBeastFarmer.current_floor = self.determine_db_floor(screenshot)

            # We need to reset the DB fighter if we entered the wrong floor
            if DemonicBeastFarmer.current_floor == -1:
                print("We entered the wrong floor! Resetting DB...")
                if find_and_click(vio.back, screenshot, window_location):
                    self.current_state = States.RESETTING_DB
                return

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

        # We may have finished the fight already, let's check if we need to go back to the main screen
        if find(vio.available_floor, screenshot, threshold=0.9):
            # We finished the fight, let's go back to the main screen
            print("We finished the fight but are still fighting? Get outta here!")
            self.stop_fighter_thread()
            self.current_state = States.READY_TO_FIGHT

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
        if find_and_click(vio.ok_main_button, screenshot, window_location) or find(vio.set_db_party, screenshot):
            print("Moving to the original state, GOING_TO_DB")
            self.current_state = States.GOING_TO_DB
            return

        # Click on the 'reset' button
        find_and_click(vio.reset_demonic_beast, screenshot, window_location, threshold=0.6)

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to regular farming"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming DemoncBeast.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DB

    def run(self):

        while True:

            check_for_reconnect()

            # Check if we need to log in again!
            self.check_for_login_state()

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

            elif self.current_state == GlobalStates.DAILY_RESET:
                self.daily_reset_state()

            elif self.current_state == GlobalStates.CHECK_IN:
                self.check_in_state()

            elif self.current_state == GlobalStates.DAILIES_STATE:
                self.dailies_state()

            elif self.current_state == GlobalStates.FORTUNE_CARD:
                self.fortune_card_state()

            elif self.current_state == GlobalStates.LOGIN_SCREEN:
                self.login_screen_state(initial_state=States.GOING_TO_DB)

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.6)
