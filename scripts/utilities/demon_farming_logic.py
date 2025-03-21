import threading
import time
from datetime import datetime
from enum import Enum

import numpy as np
import pyautogui as pyautogui
import pytz
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.daily_farming_logic import DailyFarmer
from utilities.daily_farming_logic import States as DailyFarmerStates
from utilities.general_farmer_interface import IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    drag_im,
    find,
    find_and_click,
    press_key,
    type_word,
)
from utilities.vision import Vision

# Some constants
PACIFIC_TIMEZONE = pytz.timezone("America/Los_Angeles")
CHECK_IN_HOUR = 2
MINUTES_TO_WAIT_BEFORE_LOGIN = 30

logger = LoggerWrapper(name="DemonLogger", log_file="demon_farmer.log")


class States(Enum):
    GOING_TO_DEMONS = 0
    LOOKING_FOR_DEMON = 1
    READY_TO_FIGHT = 2
    FIGHTING_DEMON = 3
    DAILY_RESET = 4
    CHECK_IN = 5
    DAILIES_STATE = 6
    FORTUNE_CARD = 7
    LOGIN_SCREEN = 8


class IDemonFarmer(IFarmer):

    # Needs to be static in case we restart the instance
    demons_destroyed = 0

    # We need to keep track if 'auto' is clicked or not...
    auto = False

    # Keep track if we've done the daily check in
    daily_checkin = False

    # The thread for doing dailies
    dailies_thread = None

    # Keep track of when we've been logged out
    logged_out_time = time.time()

    # For sending an emoji
    sent_emoji = False

    # For checking if we've seen and missed an invite
    not_seen_invite = False
    start_time_without_invite = time.time()

    # To avoid waiting to log in if it's the first time
    first_login = True

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demon_to_farm: Vision = vio.og_demon,
        time_to_sleep=9.3,
        do_dailies=False,
        do_daily_pvp=False,
        password: str = None,
    ):
        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {MINUTES_TO_WAIT_BEFORE_LOGIN} mins. before attempting a log in.")

        # Starting state
        self.current_state = starting_state

        # Demon to farm
        self.demon_to_farm = demon_to_farm

        # No battle strategy needed, we'll auto
        self.battle_strategy = battle_strategy

        # How much time to sleep before accepting the invitation -- May need to me hand-tuned
        self.sleep_before_accept = time_to_sleep

        # Thread that will do the dailies
        self.do_dailies = do_dailies
        self.daily_farmer = DailyFarmer(
            starting_state=DailyFarmerStates.IN_TAVERN_STATE,
            do_daily_pvp=do_daily_pvp,
            complete_callback=self.dailies_complete_callback,
        )
        if self.do_dailies:
            print(f"We'll stop farming to do daily missions at {CHECK_IN_HOUR}h PST.")

    def exit_message(self):
        """Final message!"""
        print(f"We destroyed {IDemonFarmer.demons_destroyed} demons.")

    def check_for_login_state(self):
        """Check whether we need to switch to the login state"""
        if IFarmer.password is None:
            # Skip the checks if we don't have a password
            return

        screenshot, _ = capture_window()

        if find(vio.password, screenshot) and self.current_state != States.LOGIN_SCREEN:
            self.current_state = States.LOGIN_SCREEN
            IDemonFarmer.logged_out_time = time.time()
            print(
                f"We've been logged out! Need to log in again, waiting for the {MINUTES_TO_WAIT_BEFORE_LOGIN} min timeout..."
            )

    def login_screen_state(self):
        """We're at the login screen, need to login!"""
        screenshot, window_location = capture_window()

        # Only try to log in if certain time has passed since we detected te login
        if (
            not IDemonFarmer.first_login
            and time.time() - IDemonFarmer.logged_out_time < MINUTES_TO_WAIT_BEFORE_LOGIN * 60
        ):  # Wait X minutes
            time.sleep(1)
            IDemonFarmer.first_login = False
            return

        # In case we have an update
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.tavern, screenshot):
            print("Logged in successfully! Going back to farming demons...")
            self.current_state = States.GOING_TO_DEMONS

        elif find(vio.skip, screenshot, threshold=0.6) or find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a daily reset!")
            self.current_state = States.DAILY_RESET

        # In case the game needs to update
        elif find_and_click(vio.yes, screenshot, window_location):
            print("Downloading update...")

        elif find_and_click(
            vio.global_server,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("center_screen"),
        ):
            print("Trying to log back in...")

        # Click on the password field
        elif find_and_click(vio.password, screenshot, window_location):
            # Type the password, and press enter
            type_word(IFarmer.password)
            press_key("enter")

    def going_to_demons_state(self):
        """Go to the demons page"""
        screenshot, window_location = capture_window()

        if find(vio.preparation_incomplete, screenshot):
            # We're waiting to click on preparation incomplete!
            self.current_state = States.READY_TO_FIGHT
            print(f"Moving to {self.current_state}.")
            return

        # If we see a 'CANCEL', change the state
        if find(vio.cancel_realtime, screenshot):
            self.current_state = States.LOOKING_FOR_DEMON
            print(f"Moving to {self.current_state}.")
            return

        # We may be in the 'daily reset' state!
        if find(vio.skip, screenshot, threshold=0.6) or find(vio.fortune_card, screenshot, threshold=0.8):
            logger.info("We entered the daily reset state!")
            self.current_state = States.DAILY_RESET
            return

        # Click OK if we see it (?)
        if find(vio.ok_main_button, screenshot) and not find(self.demon_to_farm, screenshot):
            click_and_sleep(vio.ok_main_button, screenshot, window_location, threshold=0.7)

        # Go to battle menu
        click_and_sleep(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # Go to demons
        click_and_sleep(vio.boss_menu, screenshot, window_location)

        # Click on real-time menu
        click_and_sleep(vio.real_time, screenshot, window_location, threshold=0.6)

        # Click on the demon to farm (if it's not Red, since Red is by default)
        if "red" not in self.demon_to_farm.image_name.lower():
            click_and_sleep(self.demon_to_farm, screenshot, window_location)

        # Click on the difficuly -- ONLY HELL
        find_and_click(vio.demon_hell_diff, screenshot, window_location, threshold=0.6)

    def looking_for_demon_state(self):
        """Waiting for someone to send us a demon"""
        screenshot, window_location = capture_window()

        # First, if it's time to check in, do it
        now = datetime.now(PACIFIC_TIMEZONE)
        if not IDemonFarmer.daily_checkin and now.hour == CHECK_IN_HOUR and find(vio.cancel_realtime, screenshot):
            print("Going to CHECK IN!")
            self.current_state = States.DAILY_RESET
            return
        # Reset the daily check in flag
        if now.hour > CHECK_IN_HOUR and IDemonFarmer.daily_checkin:
            print("Resetting daily checkin")
            IDemonFarmer.daily_checkin = False
            # Allow fast login the next time we're logged out
            IDemonFarmer.first_login = True

        if find(vio.accept_invitation, screenshot, threshold=0.6):
            # We've found an invitation, gotta wait before clicking on it!
            print("Found a raid! Waiting before clicking...")
            time.sleep(self.sleep_before_accept)
            # Need to re-check if 'accept invitation' is there
            screenshot, window_location = capture_window()
            click_and_sleep(vio.accept_invitation, screenshot, window_location, threshold=0.6, sleep_time=4)
            return

        if find(vio.demons_loading_screen, screenshot) or find(vio.preparation_incomplete, screenshot):
            # Going to the raid screen
            self.current_state = States.READY_TO_FIGHT
            print(f"Moving to {self.current_state}.")
            return

        if not find(vio.cancel_realtime, screenshot):
            if not IDemonFarmer.not_seen_invite:
                IDemonFarmer.start_time_without_invite = time.time()
                IDemonFarmer.not_seen_invite = True

            if time.time() - IDemonFarmer.start_time_without_invite > 2:  # Only wait 2 seconds
                self.current_state = States.GOING_TO_DEMONS
                IDemonFarmer.not_seen_invite = False

    def ready_to_fight_state(self):
        """We've accepted a raid!"""
        screenshot, window_location = capture_window()

        # If we're ready to fight, send an emoji *only once*
        if not IDemonFarmer.sent_emoji and find(vio.cancel_preparation, screenshot):
            click_and_sleep(
                vio.cancel_preparation,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("stamp_box"),
            )
            click_and_sleep(
                vio.cancel_preparation,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("first_stamp"),
            )
            IDemonFarmer.sent_emoji = True

        # Click on the "preparation"
        click_and_sleep(vio.preparation_incomplete, screenshot, window_location, threshold=0.8)

        # We may have been kicked, move to initial state if so
        if find(vio.ok_main_button, screenshot):
            self.current_state = States.GOING_TO_DEMONS
            print(f"We've been kicked out... Moving to {self.current_state}.")
            return

        if find(vio.demons_auto, screenshot):
            # Going to the fight!
            self.current_state = States.FIGHTING_DEMON
            print(f"Moving to {self.current_state}.")

    def fighting_demon_state(self):
        # sourcery skip: extract-duplicate-method, split-or-ifs
        """Fighting the demon hard..."""
        screenshot, window_location = capture_window()

        if not IDemonFarmer.auto and find_and_click(vio.demons_auto, screenshot, window_location, threshold=0.7):
            IDemonFarmer.auto = True
            IDemonFarmer.sent_emoji = False

        # # Click on network instability OK, then move to GOING_TO_DEMONS
        # if find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.7):
        #     print("Network instability, exiting fight...")
        # if find(vio.tavern_loading_screen, screenshot):
        #     print("Seeing a loading screen, moving to GOING_TO_DEMONS")
        #     self.current_state = States.GOING_TO_DEMONS
        #     return

        # If we see a skip
        find_and_click(vio.skip_bird, screenshot, window_location)

        # When we've destroyed the demon
        find_and_click(vio.demons_destroyed, screenshot, window_location)

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            if find(vio.victory, screenshot):
                print("Demon destroyed!")
                IDemonFarmer.demons_destroyed += 1
            else:
                print("Couldn't defeat this demon :(")

            IDemonFarmer.auto = False
            self.current_state = States.GOING_TO_DEMONS
            print(f"We've destroyed {IDemonFarmer.demons_destroyed} demons.")
            print(f"Moving to {self.current_state}.")

    def fortune_card_state(self):
        """Open the fortune card"""
        screenshot, window_location = capture_window()

        if find(vio.ok_main_button, screenshot, threshold=0.6):
            print("Got a good fortune? Going back to daily reset state")
            self.current_state = States.DAILY_RESET
            return

        drag_im(
            Coordinates.get_coordinates("daily_fortune_bottom"),
            Coordinates.get_coordinates("daily_fortune_top"),
            window_location,
        )

    def daily_reset_state(self):
        """Click on skip as much as needed, check in, then go back to GOING_TO_DEMONS"""
        screenshot, window_location = capture_window()

        if find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a fortune card!")
            self.current_state = States.FORTUNE_CARD
            return

        # Cancel the demon search
        click_and_sleep(vio.cancel_realtime, screenshot, window_location)

        # We may be receiving the daily rewards now
        click_and_sleep(vio.skip, screenshot, window_location, threshold=0.6)

        # Go to CHECK IN state
        if find(vio.knighthood, screenshot):
            print("Going to CHECK IN state")
            self.current_state = States.CHECK_IN
            return

        # Click on "Knighthood"
        if click_and_sleep(
            vio.battle_menu,
            screenshot,
            window_location,
            threshold=0.6,
            point_coordinates=Coordinates.get_coordinates("knighthood"),
        ):
            return

        # In case we have a "Start" mission
        find_and_click(vio.start_quest, screenshot, window_location)

        # In case an OK pop-up shows up
        find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.6)

        # Go to tavern
        find_and_click(vio.tavern, screenshot, window_location)

    def check_in_state(self):
        """Check in, and go back to"""
        screenshot, window_location = capture_window()

        # Check in
        if click_and_sleep(vio.check_in, screenshot, window_location, sleep_time=2):
            logger.info("Checked in successfully!")

        # Click on the reward
        click_and_sleep(vio.check_in_reward, screenshot, window_location)

        # Exit the knighthood after checking in...
        if find(vio.check_in_complete, screenshot):
            press_key("esc")

        if find(vio.battle_menu, screenshot, threshold=0.6):
            IDemonFarmer.daily_checkin = True
            if self.do_dailies:
                print("Going to do all dailies!")
                self.current_state = States.DAILIES_STATE
            else:
                print("Back to GOING_TO_DEMONS!")
                self.current_state = States.GOING_TO_DEMONS

    def dailies_state(self):
        """Run the thread to do all dailies"""
        with IFarmer._lock:
            if (
                IDemonFarmer.dailies_thread is None or not IDemonFarmer.dailies_thread.is_alive()
            ) and self.current_state == States.DAILIES_STATE:
                IDemonFarmer.dailies_thread = threading.Thread(target=self.daily_farmer.run, daemon=True)
                IDemonFarmer.dailies_thread.start()
                print("Dailies farmer started!")

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to farming demons"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming demons.")
            IDemonFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DEMONS

    def run(self):
        raise NotImplementedError("Virtual method. Need to implement this method in a derived class.")


class DemonFarmer(IDemonFarmer):
    """This class resets the demon to farm every X hours"""

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demons_to_farm: list[Vision] = None,
        time_to_sleep=9.4,
        time_between_demons=2,
        do_dailies=False,  # Do we halt demon farming to do dailies?
        do_daily_pvp=False,  # If we do dailies, do we do PVP?
        password: str = None,
    ):
        if demons_to_farm is None:
            demons_to_farm = [vio.og_demon]

        # Initialize the DemonFarmer with the first demon of the list
        super().__init__(
            battle_strategy,
            starting_state,
            demons_to_farm[0],
            time_to_sleep,
            do_dailies=do_dailies,
            do_daily_pvp=do_daily_pvp,
            password=password,
        )

        # Every how many hours to switch between demons
        self.time_between_demons = time_between_demons

        # Roulette of demons
        self.demon_roulette = demons_to_farm
        self.start_time = time.time()

    def rotate_demon(self):
        """Rotate a demon if X hours have passed"""

        if time.time() - self.start_time > self.time_between_demons * 3600:
            # Increase the index by one
            demon_names: list[str] = [demon.image_name for demon in self.demon_roulette]
            demon_idx = np.where(np.array(demon_names) == self.demon_to_farm.image_name)[0] + 1
            demon_idx = int(demon_idx % len(self.demon_roulette))

            # Update the new demon to farm
            new_demon_to_farm = self.demon_roulette[demon_idx]
            if new_demon_to_farm != self.demon_to_farm:
                self.demon_to_farm = new_demon_to_farm
                logger.info(f"Switched demon to {self.demon_to_farm.image_name}")

            # Record the new time
            self.start_time = time.time()

    def run(self):

        print(f"Farming demons, starting from {self.current_state}.")
        print(f"We'll be farming {[demon.image_name for demon in self.demon_roulette]} demon(s).")

        while True:
            # Try to reconnect first
            check_for_reconnect()

            # Check if to change the demon to farm
            self.rotate_demon()

            # Check if we need to log in again!
            self.check_for_login_state()

            if self.current_state == States.GOING_TO_DEMONS:
                self.going_to_demons_state()

            elif self.current_state == States.LOOKING_FOR_DEMON:
                self.looking_for_demon_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.DAILY_RESET:
                self.daily_reset_state()

            elif self.current_state == States.CHECK_IN:
                self.check_in_state()

            elif self.current_state == States.DAILIES_STATE:
                self.dailies_state()

            elif self.current_state == States.FORTUNE_CARD:
                self.fortune_card_state()

            elif self.current_state == States.LOGIN_SCREEN:
                self.login_screen_state()

            elif self.current_state == States.FIGHTING_DEMON:
                self.fighting_demon_state()
                time.sleep(1)

            # We need the loop to run very fast
            time.sleep(0.01)
