import threading
import time
from datetime import datetime
from enum import Enum, auto
from typing import Callable

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
    PATROL_STATE = auto()
    FRIENDSHIP_COINS_STATE = auto()
    EXIT_FARMER = auto()
    MISSION_COMPLETE_STATE = auto()
    GOING_TO_BRAWL = auto()
    BRAWL_STATE = auto()


class DailyFarmer(IFarmer):

    current_state = None

    def __init__(
        self,
        starting_state=States.IN_TAVERN_STATE,
        battle_strategy=None,  # Find a way to remove this, not all farmers need a battle strategy
        do_daily_pvp=False,
        logger=logger,
        complete_callback: Callable = None,
    ):

        if DailyFarmer.current_state is None:
            DailyFarmer.current_state = starting_state

        self.logger = logger

        # Do we do daily PVP?
        self.do_daily_pvp = do_daily_pvp

        # In case we're given a callback, call it upon exit
        self.complete_callback = complete_callback

    def exit_farmer_state(self):
        screenshot, window_location = capture_window()

        # First, ensure we're back on the tavern
        click_and_sleep(vio.tavern, screenshot, window_location, sleep_time=1)
        screenshot, window_location = capture_window()
        find_and_click(vio.fb_ok_button, screenshot, window_location)

        # Call the complete callback!
        if self.complete_callback is not None:
            self.complete_callback()

        # Cleanup before exiting
        super().exit_farmer_state()

    def find_next_mission(self) -> States | None:
        """Identify the next mission to do, by scrolling if we can't find any match.
        If we don't find a match by "Take all" is available, click on it.
        Else, we're done with all the dailies.

        Returns:
            State | None: The next state to move to. `None` if we're staying in the tavern state for now.
        """
        screenshot, window_location = capture_window()

        if self.do_daily_pvp and find(vio.daily_pvp, screenshot, threshold=0.85):
            print("Going to PVP_STATE")
            return States.PVP_STATE
        if find(vio.daily_boss_battle, screenshot, threshold=0.85):
            print("Going to BOSS_STATE")
            return States.BOSS_STATE
        if find(vio.daily_patrol, screenshot, threshold=0.85):
            print("Going to PATROL_STATE")
            return States.PATROL_STATE
        if find(vio.daily_fort_solgress, screenshot, threshold=0.85):
            print("Going to FORT_SOLGRESS_STATE")
            return States.FORT_SOLRGESS_STATE
        if find(vio.daily_vanya_ale, screenshot, threshold=0.85):
            print("Going to VANYA_ALE_STATE")
            return States.VANYA_ALE_STATE
        if find(vio.daily_friendship_coins, screenshot, threshold=0.85):
            print("Going to FRIENDSHIP_COINS_STATE")
            return States.FRIENDSHIP_COINS_STATE

        # If we're here, we can find no missions. Take all and try again
        if find(vio.daily_complete, screenshot):
            find_and_click(vio.take_all_rewards, screenshot, window_location, threshold=0.85)
            # TODO: Re-take the 'take all rewards' image
            print("Can't find any mission, taking all rewards for now.")
            return

        # If there's no 'go now', means we're done with the missions
        if not find(vio.go_now, screenshot):
            print("No more missions, going to collect Brawl reward now.")
            # return States.EXIT_FARMER
            find_and_click(vio.back, screenshot, window_location)
            return States.GOING_TO_BRAWL

        # # If we're here, means we're done with all dailies.
        # find_and_click(vio.tavern, screenshot, window_location, threshold=0.8)
        # if find(vio.battle_menu, screenshot):
        #     print("We're done with daily missions, hooray!")
        #     # Only go to the EXIT state if we're in the tavern already.
        #     return States.EXIT_FARMER

    def go_to_mission(self, vision_image: Vision, screenshot: np.ndarray, window_location: tuple[int, int]):
        """Click on 'Go Now' corresponding to the specific vision image"""
        # Extract the portion we want to click on
        rectangle = vision_image.find(screenshot, threshold=0.8)

        if len(rectangle):
            rectangle_image = crop_image(screenshot, rectangle[:2], rectangle[:2] + rectangle[2:])

            print("Going to the mission...")
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
            DailyFarmer.current_state = States.IN_TAVERN_STATE
            return

        # If there's any OK button
        find_and_click(vio.ok_button, screenshot, window_location)
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

        # TODO: Re-take 'daily_tasks' with the "green" background
        if find_and_click(vio.daily_tasks, screenshot, window_location):
            # Find the next mission and change the state accordingly
            print("Picking next daily to complete...")
            next_state = self.find_next_mission()
            DailyFarmer.current_state = next_state if next_state is not None else States.IN_TAVERN_STATE

        # Try to go to tasks
        elif not find_and_click(vio.tasks, screenshot, window_location):
            # Go to quests
            find_and_click(vio.quests, screenshot, window_location)

    def boss_state(self):
        """Handle the boss state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_boss_battle, screenshot, window_location)

        if find(vio.daily_quest_info, screenshot):
            print("Mission complete!")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        find_and_click(vio.boss_battle, screenshot, window_location)
        find_and_click(vio.normal_diff_boss_battle, screenshot, window_location)

        # Increase the auto ticket by one and clear mission
        click_and_sleep(vio.plus_auto_ticket, screenshot, window_location, threshold=0.8, sleep_time=1)
        if find_and_click(vio.strart_auto_clear, screenshot, window_location):
            return

        # Click on 'auto clear tickets'
        find_and_click(vio.auto_clear, screenshot, window_location)

    def vanya_ale_state(self):
        """Handle the Vanya Ale state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_vanya_ale, screenshot, window_location)

        if find(vio.meli_affection, screenshot):
            # Consider the mission done already, since it's all automatic!
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def fort_solrgess_state(self):
        """Handle the Fort Solrgess state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_fort_solgress, screenshot, window_location)

        if find(vio.daily_quest_info, screenshot):
            print("Mission complete!")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        # Click on the Special FS dungeon
        find_and_click(vio.fort_solgress_special, screenshot, window_location)

        # Click on the 6th floor
        find_and_click(vio.fs_special_6th_floor, screenshot, window_location)

        # Click on the event dungeon
        find_and_click(vio.fs_event_dungeon, screenshot, window_location)

        ## Below, we're inside the team setting

        # Increase the auto ticket by two and clear mission
        click_and_sleep(vio.plus_auto_ticket, screenshot, window_location, threshold=0.8, sleep_time=0.5)
        click_and_sleep(vio.plus_auto_ticket, screenshot, window_location, threshold=0.8, sleep_time=0.5)
        if find_and_click(vio.strart_auto_clear, screenshot, window_location):
            return

        # Click on 'auto clear tickets'
        find_and_click(vio.auto_clear, screenshot, window_location)

    def pvp_state(self):
        """Handle the PvP state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_pvp, screenshot, window_location)

    def patrol_state(self):
        """Handle the Patrol state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_patrol, screenshot, window_location)

        if find(vio.patrol_dispatched, screenshot):
            print("Finished Patrol mission")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        find_and_click(vio.patrol_all, screenshot, window_location)
        find_and_click(vio.set_all_patrol, screenshot, window_location)
        find_and_click(vio.reward, screenshot, window_location)
        find_and_click(vio.complete_all, screenshot, window_location)

    def friendship_coins_state(self):
        """Handle the Friendship Coins state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_friendship_coins, screenshot, window_location)

        if find_and_click(vio.send_friendship_coins, screenshot, window_location, threshold=0.8):
            return

        if find_and_click(vio.mail, screenshot, window_location):
            return

        if find_and_click(vio.claim_all, screenshot, window_location):
            print("Mission complete!")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def going_to_brawl_state(self):
        """Go get Brawl."""
        screenshot, window_location = capture_window()

        find_and_click(vio.battle_menu, screenshot, window_location)

        if find(vio.brawl, screenshot):
            print("Going to BRAWL")
            DailyFarmer.current_state = States.BRAWL_STATE

    def brawl_state(self):
        """Once we collect the reward, exit the farmer"""
        screenshot, window_location = capture_window()

        find_and_click(vio.brawl, screenshot, window_location)

        if find(vio.receive_brawl, screenshot):
            # Only try it once. If it fails, tough luck
            time.sleep(4)
            find_and_click(vio.receive_brawl, screenshot, window_location)
            time.sleep(1)
            press_key("esc")
            time.sleep(1)
            find_and_click(vio.back, screenshot, window_location)
            print("Assuming Brawl reward collected, exiting daily farmer.")
            DailyFarmer.current_state = States.EXIT_FARMER
            return

    def run(self):

        self.logger.info("Doing dailies!")

        while True:
            if DailyFarmer.current_state == States.IN_TAVERN_STATE:
                self.in_tavern_state()

            elif DailyFarmer.current_state == States.BOSS_STATE:
                self.boss_state()

            elif DailyFarmer.current_state == States.VANYA_ALE_STATE:
                self.vanya_ale_state()

            elif DailyFarmer.current_state == States.FORT_SOLRGESS_STATE:
                self.fort_solrgess_state()

            elif DailyFarmer.current_state == States.PVP_STATE:
                self.pvp_state()

            elif DailyFarmer.current_state == States.BRAWL_STATE:
                self.brawl_state()

            elif DailyFarmer.current_state == States.PATROL_STATE:
                self.patrol_state()

            elif DailyFarmer.current_state == States.FRIENDSHIP_COINS_STATE:
                self.friendship_coins_state()

            elif DailyFarmer.current_state == States.MISSION_COMPLETE_STATE:
                self.mission_complete_state()

            elif DailyFarmer.current_state == States.GOING_TO_BRAWL:
                self.going_to_brawl_state()
            elif DailyFarmer.current_state == States.BRAWL_STATE:
                self.brawl_state()

            elif DailyFarmer.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(1)
