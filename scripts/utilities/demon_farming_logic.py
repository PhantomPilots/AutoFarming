import threading
import time
from datetime import datetime
from enum import Enum

import numpy as np
import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    find,
    find_and_click,
    find_floor_coordinates,
    press_key,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DemonLogger", log_file="demon_farmer.log")


class States(Enum):
    GOING_TO_DEMONS = 0
    LOOKING_FOR_DEMON = 1
    READY_TO_FIGHT = 2
    FIGHTING_DEMON = 3
    DAILY_RESET = 4
    CHECK_IN = 5


class DemonFarmer(IFarmer):

    # Needs to be static in case we restart the instance
    demons_destroyed = 0

    # We need to keep track if 'auto' is clicked or not...
    auto = False

    # Keep track if we've done the daily check in
    daily_checkin = False

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demon_to_farm: Vision = vio.og_demon,
        time_to_sleep=9.4,
    ):

        # Starting state
        self.current_state = starting_state

        # Demon to farm
        self.demon_to_farm = demon_to_farm

        # No battle strategy needed, we'll auto
        self.battle_strategy = battle_strategy

        # How much time to sleep before accepting the invitation -- May need to me hand-tuned
        self.sleep_before_accept = time_to_sleep

    def exit_message(self):
        """Final message!"""
        print(f"We destroyed {DemonFarmer.demons_destroyed} demons.")

    def going_to_demons_state(self):
        """Go to the demons page"""
        screenshot, window_location = capture_window()

        # If we see a 'CANCEL', change the state
        if find(vio.cancel_realtime, screenshot):
            self.current_state = States.LOOKING_FOR_DEMON
            print(f"Moving to {self.current_state}.")
            return

        # We may be in the 'daily reset' state!
        if click_and_sleep(vio.skip, screenshot, window_location, threshold=0.6):
            logger.info("We entered the daily reset state!")
            return

        # Click OK if we see it (?)
        click_and_sleep(vio.demon_ok, screenshot, window_location)
        click_and_sleep(vio.demon_defeat_ok, screenshot, window_location)
        click_and_sleep(vio.demon_kicked_ok, screenshot, window_location)

        # Go to battle menu
        click_and_sleep(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # Go to demons
        click_and_sleep(vio.boss_menu, screenshot, window_location)

        # Click on real-time menu
        click_and_sleep(vio.real_time, screenshot, window_location, threshold=0.6)

        # Click on the demon to farm
        click_and_sleep(self.demon_to_farm, screenshot, window_location)

        # Click on the difficuly -- ONLY HELL
        find_and_click(vio.demon_hell_diff, screenshot, window_location, threshold=0.6)

    def looking_for_demon_state(self):
        """Waiting for someone to send us a demon"""
        screenshot, window_location = capture_window()

        # First, if it's time to check in, do it
        if not DemonFarmer.daily_checkin:
            now = datetime.now()
            if now.hour == 7 and find(vio.cancel_realtime, screenshot):
                print("Going to CHECK IN!")
                self.current_state = States.DAILY_RESET
                return

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

        # We need a backup in case the matchmaking gets cancelled
        if not find(vio.join_request, screenshot):
            find_and_click(vio.real_time, screenshot, window_location, threshold=0.6)
        if find(self.demon_to_farm, screenshot):
            # The matchmaking got cancelled, change states
            self.current_state = States.GOING_TO_DEMONS
            print("Seems the matchmaking got cancelled...")
            print(f"Moving to {self.current_state}.")

    def ready_to_fight_state(self):
        """We've accepted a raid!"""
        screenshot, window_location = capture_window()

        # Click on the "preparation"
        click_and_sleep(vio.preparation_incomplete, screenshot, window_location, threshold=0.8)

        # We may have been kicked, move to initial state if so
        if find(vio.demon_kicked_ok, screenshot):
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

        if not DemonFarmer.auto and find_and_click(vio.demons_auto, screenshot, window_location, threshold=0.7):
            DemonFarmer.auto = True

        # If we see a skip
        find_and_click(vio.skip_bird, screenshot, window_location)

        # When we've destroyed the demon
        find_and_click(vio.demons_destroyed, screenshot, window_location)

        if find(vio.demon_ok, screenshot) or find(vio.demon_defeat_ok, screenshot):
            # Finished the fight!
            if find(vio.demon_ok, screenshot):
                print("DEMON DESTROYED!")
                DemonFarmer.demons_destroyed += 1
            DemonFarmer.auto = False
            self.current_state = States.GOING_TO_DEMONS
            print(f"We've destroyed {DemonFarmer.demons_destroyed} demons.")
            print(f"Moving to {self.current_state}.")

    def daily_reset_state(self):
        """Click on skip as much as needed, check in, then go back to GOING_TO_DEMONS"""
        screenshot, window_location = capture_window()

        # Cancel the demon search
        click_and_sleep(vio.cancel_realtime, screenshot, window_location)

        # We may be receiving the daily rewards now
        click_and_sleep(vio.skip, screenshot, window_location, threshold=0.6)

        # Go to CHECKIN state
        if find(vio.knighthood, screenshot):
            print("Going to CHECK IN state")
            self.current_state = States.CHECK_IN
            return

        # Click on "Knighthood"
        if click_and_sleep(
            vio.battle_menu,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("knighthood"),
        ):
            return

        # Go to tavern
        click_and_sleep(vio.tavern, screenshot, window_location)

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

        if find(vio.battle_menu, screenshot):
            DemonFarmer.daily_checkin = True
            print("Back to GOING_TO_DEMONS!")
            self.current_state = States.GOING_TO_DEMONS

    def run(self):

        print(f"Farming demons, starting from {self.current_state}.")
        print(f"We'll be farming {self.demon_to_farm.image_name} demon.")

        while True:
            # Try to reconnect first
            check_for_reconnect()

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

            elif self.current_state == States.FIGHTING_DEMON:
                self.fighting_demon_state()
                time.sleep(1)

            # We need the loop to run very fast
            time.sleep(0.1)


class DemonRouletteFarmer(DemonFarmer):
    """This class resets the demon to farm every X hours"""

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demons_to_farm: list[Vision] = None,
        time_to_sleep=9.4,
        time_between_demons=2,
    ):
        if demons_to_farm is None:
            demons_to_farm = [vio.og_demon]

        # Initialize the DemonFarmer with the first demon of the list
        super().__init__(battle_strategy, starting_state, demons_to_farm[0], time_to_sleep)

        # Every how many hours to switch between demons
        self.time_between_demons = time_between_demons

        # Roulette of demons
        self.demon_roulette = demons_to_farm
        self.start_time = time.time()

    def rotate_demon(self):
        """Rotate a demon if X hours have passed"""

        if time.time() - self.start_time > self.time_between_demons * 3600:
            # Increase the index by one
            demon_names = [demon.image_name for demon in self.demon_roulette]
            demon_idx = np.where(np.array(demon_names) == self.demon_to_farm.image_name)[0] + 1
            demon_idx = int(demon_idx % len(self.demon_roulette))

            # Get the new demon
            self.demon_to_farm = self.demon_roulette[demon_idx]
            logger.info(f"Switched demon to {self.demon_to_farm.image_name}")

            # Record the new time
            self.start_time = time.time()

    def run(self):

        print(f"Farming demons, starting from {self.current_state}.")
        print(f"We'll be farming {self.demon_to_farm.image_name} demon.")

        while True:
            # Try to reconnect first
            check_for_reconnect()

            # Check if to change the demon to farm
            self.rotate_demon()

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

            elif self.current_state == States.FIGHTING_DEMON:
                self.fighting_demon_state()
                time.sleep(1)

            # We need the loop to run very fast
            time.sleep(0.1)
