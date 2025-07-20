import time
from enum import Enum, auto
from threading import Lock
from typing import Callable

import numpy as np
import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    click_and_sleep,
    crop_image,
    find,
    find_and_click,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="WeeklyLogger", log_file="weekly_farmer_logger.log")


class States(Enum):
    IN_TAVERN_STATE = auto()
    EXIT_FARMER = auto()
    MISSION_COMPLETE_STATE = auto()
    KH_BOSS_BATTLE = auto()
    DEMONIC_BEAST = auto()


class WeeklyFarmer:

    # Current state should be a class variable, since this class runs in a separate thread
    current_state = None

    # Lock for thread safety, always necessary
    _lock = Lock()

    # To check if we should kill the farmer
    farmer_killed = False
    manual_kill = False

    def __init__(
        self,
        starting_state=States.IN_TAVERN_STATE,
        battle_strategy=None,  # TODO Find a way to remove this, not all farmers need a battle strategy
        logger=logger,
        complete_callback: Callable | None = None,
        **kwargs,
    ):

        if WeeklyFarmer.current_state is None:
            WeeklyFarmer.current_state = starting_state

        self.logger = logger

        # In case we're given a callback, call it upon exit
        self.add_complete_callback(complete_callback)

    def add_complete_callback(self, complete_callback):
        """Callback to call after Dailies are done"""
        self.complete_callback = complete_callback

    def kill_farmer(self):
        """Kill the daily farmer from a different thread"""
        with WeeklyFarmer._lock:
            self.logger.info("Manually trying to kill the dailies thread...")
            WeeklyFarmer.farmer_killed = True
            WeeklyFarmer.manual_kill = True

    def check_if_farmer_killed(self):
        """Check if the farmer was killed"""
        with WeeklyFarmer._lock:
            if WeeklyFarmer.farmer_killed:
                WeeklyFarmer.current_state = States.EXIT_FARMER
                self.logger.info("Gracefully killing the weekly farmer thread...")
                WeeklyFarmer.farmer_killed = False

    def exit_farmer_state(self) -> bool:  # sourcery skip: extract-duplicate-method, extract-method, split-or-ifs
        screenshot, window_location = capture_window()

        print("In EXIT FARMER state, trying to exit...")

        # First, ensure we're back on the tavern
        find_and_click(vio.back, screenshot, window_location)

        if find(vio.tavern, screenshot) or WeeklyFarmer.manual_kill:
            if self.complete_callback is not None:
                # Call the complete callback if needed
                self.complete_callback()
            # Reset the current state!
            WeeklyFarmer.current_state = States.IN_TAVERN_STATE
            # Reset the manual kill
            WeeklyFarmer.manual_kill = False
            return True

        return False

    def find_next_mission(self) -> States | None:
        """Identify the next mission to do, by scrolling if we can't find any match.
        If we don't find a match by "Take all" is available, click on it.
        Else, we're done with all the dailies.

        Returns:
            State | None: The next state to move to. `None` if we're staying in the tavern state for now.
        """
        screenshot, window_location = capture_window()

        # Get rewards
        if find(vio.daily_complete, screenshot):
            find_and_click(vio.take_all_rewards, screenshot, window_location, threshold=0.89)
            print("We have complete rewards, let's take them.")
            return

        if find(vio.kh_boss_battle, screenshot, threshold=0.89):
            print("Going to KH BOSS BATTLE state")
            return States.KH_BOSS_BATTLE
        if find(vio.daily_boss_battle, screenshot, threshold=0.89):
            print("Going to DEMONIC BEAST state")
            return States.DEMONIC_BEAST

        # If we're here, means we're done with all dailies.
        click_and_sleep(vio.tavern, screenshot, window_location, threshold=0.8, sleep_time=1)
        screenshot, _ = capture_window()
        find_and_click(vio.ok_main_button, screenshot, window_location)
        if find(vio.battle_menu, screenshot, threshold=0.6):
            print("No more weekly missions.")
            # Only go to the EXIT state if we're in the tavern already.
            return States.EXIT_FARMER

    def extract_mission_rectangle(self, vision_image: Vision, screenshot: np.ndarray):
        """Extract the part of the image that contains the mission information"""
        rectangle = vision_image.find(screenshot, threshold=0.89)

        if len(rectangle):
            return crop_image(screenshot, rectangle[:2], rectangle[:2] + rectangle[2:])
        return np.empty(0)

    def go_to_mission(
        self, vision_image: Vision, screenshot: np.ndarray, window_location: tuple[int, int], threshold=0.89
    ):
        """Click on 'Go Now' corresponding to the specific vision image"""
        # Extract the portion we want to click on
        rectangle = vision_image.find(screenshot, threshold=threshold)

        if len(rectangle):
            rectangle_image = crop_image(screenshot, rectangle[:2], rectangle[:2] + rectangle[2:])

            print(f"Going to the '{vision_image.image_name}' mission...")

            # Click on `Go Now`
            find_and_click(
                vio.go_now,
                rectangle_image,
                window_location=(window_location[0] + rectangle[0], window_location[1] + rectangle[1]),
            )

    def mission_complete_state(self):
        """We've complete a mission, go back to the tavern"""
        screenshot, window_location = capture_window()

        # If we can already go to the quest menu, go right away!
        if find(vio.quests, screenshot):
            print("Going back to the Quests menu")
            WeeklyFarmer.current_state = States.IN_TAVERN_STATE
            return

        # If there's any OK button
        find_and_click(vio.ok_main_button, screenshot, window_location)
        # In case we see a cross, exit
        find_and_click(vio.exit_cross, screenshot, window_location)
        # Patrol dispatched successfully
        find_and_click(vio.patrol_dispatched, screenshot, window_location)
        # Daily quest for when a battle happened
        find_and_click(vio.daily_quest_info, screenshot, window_location)
        # In case we need to cancel something
        find_and_click(vio.cancel, screenshot, window_location)
        # Click on the Result
        find_and_click(vio.daily_result, screenshot, window_location)
        # Go back
        find_and_click(vio.back, screenshot, window_location)

    def in_tavern_state(self):
        """We're in the tavern, go to the next task."""

        screenshot, window_location = capture_window()

        if find_and_click(vio.weekly_mission, screenshot, window_location):
            # Find the next mission and change the state accordingly
            print("Picking next daily to complete...")
            next_state = self.find_next_mission()
            if next_state is not None:
                print(f"Next state will be {next_state}")
            else:
                print("Finished all dailies!")
            WeeklyFarmer.current_state = next_state if next_state is not None else States.IN_TAVERN_STATE

        # Try to go to tasks
        elif not find_and_click(vio.tasks, screenshot, window_location):
            # Go to quests
            find_and_click(vio.quests, screenshot, window_location)

    def kh_boss_battle_state(self):
        """We need to beat the KH boss 3 timest"""
        screenshot, window_location = capture_window()

        WeeklyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def demonic_beast_state(self):
        """Just enter and leave the DemonicBeast screen. Need to handle the DB weekly reset."""
        screenshot, window_location = capture_window()

        WeeklyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def check_for_essette_shop(self):
        """Check if we have the Essette shop, and click on it if so to remove the popup"""
        screenshot, window_location = capture_window()
        find_and_click(vio.essette_shop, screenshot, window_location)

    def run(self):

        self.logger.info("Doing dailies!")

        while True:

            self.check_for_essette_shop()

            # In case we manually press the "kill switch"
            self.check_if_farmer_killed()

            if WeeklyFarmer.current_state == States.IN_TAVERN_STATE:
                self.in_tavern_state()

            elif WeeklyFarmer.current_state == States.KH_BOSS_BATTLE:
                self.kh_boss_battle_state()

            elif WeeklyFarmer.current_state == States.DEMONIC_BEAST:
                self.demonic_beast_state()

            elif WeeklyFarmer.current_state == States.MISSION_COMPLETE_STATE:
                self.mission_complete_state()

            elif WeeklyFarmer.current_state == States.EXIT_FARMER:
                if self.exit_farmer_state():
                    return

            time.sleep(1)
