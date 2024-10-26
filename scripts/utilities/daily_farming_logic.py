import threading
import time
from datetime import datetime
from enum import Enum, auto

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
    crop_image,
    find,
    find_and_click,
    find_floor_coordinates,
    press_key,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DailyLogger", log_file="daily_farmer_logger.log")


class States(Enum):
    IN_TAVERN_STATE = 0
    BOSS_STATE = auto()
    VANYA_ALE_STATE = auto()
    FORT_SOLRGESS_STATE = auto()
    PVP_STATE = auto()
    BRAWL_STATE = auto()
    PATROL_STATE = auto()
    FRIENDSHIP_COINS_STATE = auto()
    EXIT_FARMER = auto()
    MISSION_COMPLETE_STATE = auto()


class DailyFarmer(IFarmer):

    exit_flag = False

    def __init__(
        self,
        battle_strategy=None,
        starting_state=States.IN_TAVERN_STATE,
        do_daily_pvp=False,
        logger=logger,
    ):

        self.logger = logger
        self.current_state = starting_state
        # Not needed, remove?
        self.batle_strategy = battle_strategy

        self.do_daily_pvp = do_daily_pvp

    def exit_farmer_state(self):
        screenshot, window_location = capture_window()

        # First, ensure we're back on the tavern
        find_and_click(vio.tavern, screenshot, window_location)

        # Cleanup before exiting
        DailyFarmer.exit_flag = True

    def find_next_mission(self) -> States | None:
        """Identify the next mission to do, by scrolling if we can't find any match.
        If we don't find a match by "Take all" is available, click on it.
        Else, we're done with all the dailies.

        Returns:
            State | None: The next state to move to. `None` if we're staying in the tavern state for now.
        """
        screenshot, window_location = capture_window()

        if self.do_daily_pvp and find(vio.daily_pvp, screenshot, threshold=0.9):
            print("Going to PVP_STATE")
            return States.PVP_STATE
        if find(vio.daily_boss_battle, screenshot, threshold=0.9):
            print("Going to BOSS_STATE")
            return States.BOSS_STATE
        if find(vio.daily_patrol, screenshot, threshold=0.9):
            print("Going to PATROL_STATE")
            return States.PATROL_STATE
        if find(vio.daily_fort_solgress, screenshot, threshold=0.9):
            print("Going to FORT_SOLGRESS_STATE")
            return States.FORT_SOLRGESS_STATE
        if find(vio.daily_vanya_ale, screenshot, threshold=0.9):
            print("Going to VANYA_ALE_STATE")
            return States.VANYA_ALE_STATE
        if find(vio.daily_friendship_coins, screenshot, threshold=0.9):
            print("Going to FRIENDSHIP_COINS_STATE")
            return States.FRIENDSHIP_COINS_STATE

        # If we're here, we can find no missions. Take all and try again
        if find_and_click(vio.take_all_rewards, screenshot, window_location, threshold=0.8):
            print("Can't find any mission, taking all rewards for now.")
            return

        # If we're here, means we're done with all dailies.
        find_and_click(vio.tavern, screenshot, window_location, threshold=0.8)
        if find(vio.battle_menu, screenshot):
            print("We're done with daily missions, hooray!")
            # Only go to the EXIT state if we're in the tavern already.
            return States.EXIT_FARMER

    def go_to_mission(self, vision_image: Vision, screenshot: np.ndarray, window_location: tuple[int, int]):
        """Click on 'Go Now' corresponding to the specific vision image"""
        # Extract the portion we want to click on
        rectangle = vision_image.find(screenshot, threshold=0.8)
        rectangle_image = crop_image(screenshot, rectangle[:2], rectangle[:2] + rectangle[2:])

        # Click on `Go Now`
        find_and_click(
            vio.go_now,
            rectangle_image,
            window_location=(window_location[0] + rectangle[0], window_location[1] + rectangle[1]),
        )

    def in_tavern_state(self):
        """We're in the tavern, go to the next task."""

        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Find the next mission and change the state accordingly
            print("Picking next daily to complete...")
            next_state = self.find_next_mission()
            self.current_state = next_state if next_state is not None else States.IN_TAVERN_STATE

        # Try to go to tasks
        elif not find_and_click(vio.tasks, screenshot, window_location):
            # Go to quests
            find_and_click(vio.quests, screenshot, window_location)

    def boss_state(self):
        """Handle the boss state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            print("Going to the mission...")
            self.go_to_mission(vio.daily_boss_battle, screenshot, window_location)

        find_and_click(vio.boss_battle, screenshot, window_location)
        find_and_click(vio.normal_diff_boss_battle, screenshot, window_location)

        # Increase the auto ticket by one and clear mission
        click_and_sleep(vio.plus_auto_ticket, screenshot, window_location, threshold=0.8, sleep_time=1)
        if find_and_click(vio.strart_auto_clear, screenshot, window_location):
            return

        # Click on 'auto clear tickets'
        find_and_click(vio.auto_clear, screenshot, window_location)

        if find(vio.daily_quest_info, screenshot):
            # Mission complete!
            self.current_state = States.MISSION_COMPLETE_STATE
            return

    def mission_complete_state(self):
        """We've complete a mission, go back to the tavern"""
        screenshot, window_location = capture_window()

        # If we can already go to the quest menu, go right away!
        if find(vio.quests, screenshot):
            print("Going back to the Quests menu")
            self.current_state = States.IN_TAVERN_STATE
            return

        find_and_click(vio.daily_quest_info, screenshot, window_location)
        # In case we need to cancel something
        find_and_click(vio.cancel, screenshot, window_location)
        # Click on the Result
        find_and_click(vio.daily_result, screenshot, window_location)
        # Go back
        find_and_click(vio.back, screenshot, window_location)

    def vanya_ale_state(self):
        """Handle the Vanya Ale state."""

    def fort_solrgess_state(self):
        """Handle the Fort Solrgess state."""

    def pvp_state(self):
        """Handle the PvP state."""

    def brawl_state(self):
        """Handle the Brawl state."""

    def patrol_state(self):
        """Handle the Patrol state."""

    def friendship_coins_state(self):
        """Handle the Friendship Coins state."""

    def run(self):

        self.logger.info("Doing dailies!")

        while True:
            if self.current_state == States.IN_TAVERN_STATE:
                self.in_tavern_state()

            elif self.current_state == States.BOSS_STATE:
                self.boss_state()

            elif self.current_state == States.VANYA_ALE_STATE:
                self.vanya_ale_state()

            elif self.current_state == States.FORT_SOLRGESS_STATE:
                self.fort_solrgess_state()

            elif self.current_state == States.PVP_STATE:
                self.pvp_state()

            elif self.current_state == States.BRAWL_STATE:
                self.brawl_state()

            elif self.current_state == States.PATROL_STATE:
                self.patrol_state()

            elif self.current_state == States.FRIENDSHIP_COINS_STATE:
                self.friendship_coins_state()

            elif self.current_state == States.MISSION_COMPLETE_STATE:
                self.mission_complete_state()

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            # Close the daily farmer
            if DailyFarmer.exit_flag:
                break

            time.sleep(0.8)
