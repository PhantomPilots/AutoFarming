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
    press_key,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DailyLogger", log_file="daily_farmer_logger.log")


class States(Enum):
    IN_TAVERN_STATE = auto()
    BOSS_STATE = auto()
    VANYA_ALE_STATE = auto()
    FORT_SOLGRESS_STATE = auto()
    SPECIAL_EVENT_FS_STATE = auto()
    FINISHED_SPECIAL_EVENT_FS = auto()
    PVP_STATE = auto()
    PATROL_STATE = auto()
    FRIENDSHIP_COINS_STATE = auto()
    EXIT_FARMER = auto()
    MISSION_COMPLETE_STATE = auto()
    GOING_TO_BRAWL = auto()
    BRAWL_STATE = auto()
    PLAYING_BRAWL = auto()
    FINISHED_BRAWL = auto()
    AD_WHEEL = auto()


class DailyFarmer:

    # Current state should be a class variable, since this class runs in a separate thread
    current_state = None

    # How many dungeons keys we'll try to use
    num_dungeon_keys = 3

    pvp_auto = False

    # For event-special dungeon
    event_special_dungeon_complete = False

    _lock = Lock()

    # To check if we should kill the farmer
    farmer_killed = False
    manual_kill = False

    def __init__(
        self,
        starting_state=States.IN_TAVERN_STATE,
        battle_strategy=None,  # TODO Find a way to remove this, not all farmers need a battle strategy
        do_daily_pvp=False,
        logger=logger,
        complete_callback: Callable = None,
        **kwargs,
    ):

        if DailyFarmer.current_state is None:
            DailyFarmer.current_state = starting_state

        self.logger = logger

        # Do we do daily PVP?
        self.set_daily_pvp(do_daily_pvp)

        # In case we're given a callback, call it upon exit
        self.add_complete_callback(complete_callback)

    def add_complete_callback(self, complete_callback):
        """Callback to call after Dailies are done"""
        self.complete_callback = complete_callback

    def set_daily_pvp(self, do_daily_pvp: bool):
        """Set the daily PVP"""
        if do_daily_pvp:
            print("If dailies is enabled, we will do daily PVP!")
        self.do_daily_pvp = do_daily_pvp

    def kill_farmer(self):
        """Kill the daily farmer from a different thread"""
        with DailyFarmer._lock:
            self.logger.info("Manually trying to kill the dailies thread...")
            DailyFarmer.farmer_killed = True
            DailyFarmer.manual_kill = True

    def check_if_farmer_killed(self):
        """Check if the farmer was killed"""
        with DailyFarmer._lock:
            if DailyFarmer.farmer_killed:
                DailyFarmer.current_state = States.EXIT_FARMER
                self.logger.info("Successfully killing the farmer thread!")
                DailyFarmer.farmer_killed = False

    def exit_farmer_state(self) -> bool:  # sourcery skip: extract-duplicate-method, extract-method, split-or-ifs
        screenshot, window_location = capture_window()

        print("In EXIT FARMER state, trying to exit...")

        # First, ensure we're back on the tavern
        find_and_click(vio.back, screenshot, window_location)

        if find(vio.tavern, screenshot) or DailyFarmer.manual_kill:
            if self.complete_callback is not None:
                # Call the complete callback if needed
                self.complete_callback()
            # Let's reset the number of dungeon keys for tomorrow
            DailyFarmer.num_dungeon_keys = 3
            # Reset the PVP auto
            DailyFarmer.pvp_auto = False
            # Reset the event-special dungeon complete
            DailyFarmer.event_special_dungeon_complete = False
            # Reset the current state!
            DailyFarmer.current_state = States.IN_TAVERN_STATE
            # Reset the manual kill
            DailyFarmer.manual_kill = False
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

        if self.do_daily_pvp and find(vio.daily_pvp, screenshot, threshold=0.89):
            print("Going to PVP_STATE")
            return States.PVP_STATE
        if find(vio.daily_boss_battle, screenshot, threshold=0.89):
            print("Going to BOSS_STATE")
            return States.BOSS_STATE
        if find(vio.daily_patrol, screenshot, threshold=0.85):
            print("Going to PATROL_STATE")
            return States.PATROL_STATE
        if find(vio.daily_vanya_ale, screenshot, threshold=0.89):
            print("Going to VANYA_ALE_STATE")
            return States.VANYA_ALE_STATE
        if find(vio.daily_friendship_coins, screenshot, threshold=0.89):
            print("Going to FRIENDSHIP_COINS_STATE")
            return States.FRIENDSHIP_COINS_STATE
        if find(vio.daily_fort_solgress, screenshot, threshold=0.89):
            # Here, we may have wrongly clicked on death match
            mission_rectangle = self.extract_mission_rectangle(vio.daily_fort_solgress, screenshot)
            if not find(vio.blue_stone, mission_rectangle, threshold=0.8):
                print("Going to FORT_SOLGRESS_STATE")
                return States.FORT_SOLGRESS_STATE
            else:
                print("We WRONGLY want to click on death match thinking it's FORT SOLGRESS!")

        # If there's no 'go now', means we're done with the missions
        if not find(vio.go_now, screenshot):
            print("No more missions, going to collect Brawl reward now (1).")
            find_and_click(vio.back, screenshot, window_location)
            return States.GOING_TO_BRAWL

        # If we're here, means we're done with all dailies.
        click_and_sleep(vio.tavern, screenshot, window_location, threshold=0.8, sleep_time=1)
        screenshot, _ = capture_window()
        find_and_click(vio.ok_main_button, screenshot, window_location)
        if find(vio.battle_menu, screenshot, threshold=0.6):
            print("No more missions, going to collect Brawl reward now (2).")
            # Only go to the EXIT state if we're in the tavern already.
            return States.GOING_TO_BRAWL

    def extract_mission_rectangle(self, vision_image: Vision, screenshot: np.ndarray):
        """Extarct the part of the image that contains the mission information"""
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

        # First, check if we have a wheel ad roulette from FS, and spin it if so
        if in_ad_wheel := self.check_ad_wheel(screenshot, window_location):
            # We don't want to do anything else until the ad wheel is complete
            print("We've finished the mission but there's an ad wheel to spin!")
            DailyFarmer.current_state = States.AD_WHEEL
            return

        # If we can already go to the quest menu, go right away!
        if find(vio.quests, screenshot):
            print("Going back to the Quests menu")
            DailyFarmer.current_state = States.IN_TAVERN_STATE
            return

        # In case we need to cancel something
        find_and_click(vio.cancel, screenshot, window_location)
        # If there's any OK button
        find_and_click(vio.ok_main_button, screenshot, window_location)
        # In case we see a cross, exit
        find_and_click(vio.exit_cross, screenshot, window_location)
        # Patrol dispatched successfully
        find_and_click(vio.patrol_dispatched, screenshot, window_location)
        # Daily quest for when a battle happened
        find_and_click(vio.daily_quest_info, screenshot, window_location)
        # Click on the Result
        find_and_click(vio.daily_result, screenshot, window_location)
        # Go back
        find_and_click(vio.back, screenshot, window_location)

    def ad_wheel_state(self):
        """We have to play the ad wheel, until there's no more"""
        screenshot, window_location = capture_window()
        if not self.check_ad_wheel(screenshot, window_location):
            print("In the AD_WHEEL state, but no more ad wheel to play!")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def in_tavern_state(self):
        """We're in the tavern, go to the next task."""

        screenshot, window_location = capture_window()

        if find_and_click(vio.daily_tasks, screenshot, window_location):
            # Find the next mission and change the state accordingly
            print("Picking next daily to complete...")
            next_state = self.find_next_mission()
            if next_state is not None:
                print(f"Next state will be {next_state}")
            else:
                print("Finished all dailies!")
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

        if find(vio.meli_affection, screenshot) or find(vio.perci_affection, screenshot):
            # Consider the mission done already, since it's all automatic!
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def special_event_fs_state(self):
        """We have a special event dungeon, let's clear it"""

        screenshot, window_location = capture_window()

        # If we have a monthly...
        if in_ad_wheel := self.check_ad_wheel(screenshot, window_location):
            # We don't want to do anything else until the ad wheel is complete
            return

        # Click on the battle
        find_and_click(vio.event_special_fs_battle, screenshot, window_location)
        find_and_click(vio.event_special_fs_dungeon, screenshot, window_location)

        # Fight...
        find_and_click(
            vio.auto_repeat_on,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("start_fight"),
        )
        find_and_click(vio.auto_repeat_off, screenshot, window_location)

        # Fight is done, let's go back
        find_and_click(vio.daily_quest_info, screenshot, window_location)

        if find(vio.auto_repeat_ended, screenshot):
            press_key("esc")

        # Exit this state
        if find(vio.ok_main_button, screenshot) and not find(vio.ad_wheel_play, screenshot, threshold=0.6):
            print("Finished special FS event...")
            DailyFarmer.event_special_dungeon_complete = True
            DailyFarmer.current_state = States.FINISHED_SPECIAL_EVENT_FS

    def finished_special_event_fs_state(self):
        """We've finished the special event, go back to FS state"""
        screenshot, window_location = capture_window()

        # If we have a monthly...
        if in_ad_wheel := self.check_ad_wheel(screenshot, window_location):
            # We don't want to do anything else until the ad wheel is complete
            return

        if find(vio.fort_solgress_special, screenshot):
            print("Going back to FS state!")
            DailyFarmer.current_state = States.FORT_SOLGRESS_STATE
            return

        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.daily_result, screenshot, window_location)
        find_and_click(vio.back, screenshot, window_location)

    def check_ad_wheel(self, screenshot, window_location, threshold=0.7) -> bool:
        """For when we have a monthly"""
        # To spin the wheel
        if find_and_click(vio.ad_wheel_free, screenshot, window_location, threshold=threshold):
            print("Spinning the wheel...")
            return True

        # To skip the reward
        if find_and_click(vio.ad_wheel_play, screenshot, window_location, threshold=0.6):
            print("We're seeing ad_wheel_play, going to AD_WHEEL state...")
            return True

        return False

    def fort_solgress_state(self):
        """Handle the Fort Solrgess state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_fort_solgress, screenshot, window_location, threshold=0.89)

        if (
            find(vio.daily_quest_info, screenshot)
            or find(vio.daily_result, screenshot)
            or DailyFarmer.num_dungeon_keys == 0
        ):
            print("Mission complete!")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        if find(vio.not_enough_dungeon_keys, screenshot):
            print(f"We don't have enough dungeon keys, trying with {DailyFarmer.num_dungeon_keys}.")
            DailyFarmer.num_dungeon_keys -= 1
            press_key("esc")
            return

        # If we find an event-special dungeon, go there first instead!
        # TODO: Fix to add multiple dungeons? Otherwise, keep it for one dungeon only
        if not DailyFarmer.event_special_dungeon_complete and find(vio.event_special_fs_dungeon, screenshot):
            print("Found an event-special dungeon! We should go there")
            DailyFarmer.current_state = States.SPECIAL_EVENT_FS_STATE
            return

        if in_ad_wheel := self.check_ad_wheel(screenshot, window_location):
            # We don't want to do anything else until the ad wheel is complete
            return

        # Click on the Special FS dungeon
        find_and_click(vio.fort_solgress_special, screenshot, window_location)

        # Click on the 6th floor
        find_and_click(vio.fs_special_6th_floor, screenshot, window_location)

        # Click on the event dungeon
        find_and_click(vio.fs_event_dungeon, screenshot, window_location)

        ## Below, we're inside the team setting

        # Increase the auto ticket by two and clear mission
        for _ in range(DailyFarmer.num_dungeon_keys - 1):
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

        # If we've failed tier up...
        find_and_click(vio.tier_up_failed, screenshot, window_location)

        # For when Monday
        find_and_click(vio.view_pvp_results, screenshot, window_location)
        find_and_click(vio.join_all, screenshot, window_location)
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # Find a match...
        find_and_click(vio.search_pvp_match, screenshot, window_location)

        # Set PVP to auto
        if not DailyFarmer.pvp_auto and find_and_click(vio.demons_auto, screenshot, window_location):
            DailyFarmer.pvp_auto = True

        # After the match...
        find_and_click(vio.daily_quest_info, screenshot, window_location)

        # If we win, or lose:
        if find(vio.ok_main_button, screenshot) and DailyFarmer.pvp_auto:
            print("PVP fight finished! Ending mission")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def patrol_state(self):
        """Handle the Patrol state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_patrol, screenshot, window_location, threshold=0.85)

        if find(vio.patrol_dispatched, screenshot):
            print("Finished Patrol mission")
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        find_and_click(vio.patrol_all, screenshot, window_location)
        # First click on complete all
        find_and_click(vio.complete_all, screenshot, window_location)
        # Then click on set all
        find_and_click(vio.set_all_patrol, screenshot, window_location)
        find_and_click(vio.reward, screenshot, window_location)

    def friendship_coins_state(self):
        """Handle the Friendship Coins state."""
        screenshot, window_location = capture_window()

        if find(vio.daily_tasks, screenshot):
            # Go to the mission
            self.go_to_mission(vio.daily_friendship_coins, screenshot, window_location)

        if find_and_click(vio.send_friendship_coins, screenshot, window_location, threshold=0.8):
            DailyFarmer.current_state = States.MISSION_COMPLETE_STATE
            return

        # if find_and_click(vio.mail, screenshot, window_location):
        #     return

        # if find_and_click(vio.claim_all, screenshot, window_location):
        #     print("Mission complete!")
        #     DailyFarmer.current_state = States.MISSION_COMPLETE_STATE

    def going_to_brawl_state(self):
        """Go get Brawl."""
        screenshot, window_location = capture_window()

        if find(vio.brawl, screenshot):
            print("Going to BRAWL")
            DailyFarmer.current_state = States.BRAWL_STATE
            return

        if find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6):
            return

        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.tavern, screenshot, window_location, threshold=0.8)

    def brawl_state(self):
        """Once we collect the reward, exit the farmer"""
        screenshot, window_location = capture_window()

        find_and_click(vio.brawl, screenshot, window_location)
        find_and_click(vio.view_pvp_results, screenshot, window_location)
        find_and_click(vio.join_all, screenshot, window_location)
        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.participate, screenshot, window_location)

        # TODO Improve the logic in this function
        self.collect_brawl_reward(screenshot, window_location)

    def collect_brawl_reward(self, screenshot, window_location):
        """Collect the Brawl reward"""

        if find(vio.receive_brawl, screenshot):
            # Only try it once. If it fails, tough luck
            time.sleep(4)
            find_and_click(
                vio.receive_brawl_extended,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("receive_brawl"),
            )
            time.sleep(1)

            screenshot, window_location = capture_window()
            find_and_click(vio.reward, screenshot, window_location)
            time.sleep(1)

            # ... And let's play a Brawl match too!
            screenshot, window_location = capture_window()
            if find(vio.back, screenshot):
                print("Going to PLAYING_BRAWL state")
                DailyFarmer.current_state = States.PLAYING_BRAWL

    def playing_brawl_state(self):
        """Play a Brawl match such that Brawl doesn't reset"""

        screenshot, window_location = capture_window()

        # In case we didn't click it in the previous state
        find_and_click(vio.reward, screenshot, window_location)

        # For after the match
        if find(vio.ok_main_button, screenshot):
            print("Brawl match finished. Hopefully we won!")
            DailyFarmer.current_state = States.FINISHED_BRAWL
            return

        # To fight the match
        find_and_click(vio.battle_brawl, screenshot, window_location)
        if find_and_click(vio.ready_up_brawl, screenshot, window_location):
            time.sleep(0.5)  # Necessary to wait a tiny bit, empirically found

    def finished_brawl_state(self):
        """After the Brawl match, we go back to the tavern"""
        screenshot, window_location = capture_window()

        if find(vio.back, screenshot):
            print("Finished all farming!")
            DailyFarmer.current_state = States.EXIT_FARMER
            return

        find_and_click(vio.ok_main_button, screenshot, window_location)

    def check_for_annoying_popups(self):
        """Check if we have the Essette shop, and click on it if so to remove the popup"""
        screenshot, window_location = capture_window()
        find_and_click(vio.essette_shop, screenshot, window_location)

        if (
            DailyFarmer.current_state == States.IN_TAVERN_STATE
            and find(vio.battle_menu, screenshot)
            and find_and_click(vio.annoying_chat_popup, screenshot, window_location, threshold=0.8)
        ):
            print("Closing the annoying chat popup...")

    def run(self):

        self.logger.info("Doing dailies!")

        while True:

            self.check_for_annoying_popups()

            # In case we manually press the "kill switch"
            self.check_if_farmer_killed()

            if DailyFarmer.current_state == States.IN_TAVERN_STATE:
                self.in_tavern_state()

            elif DailyFarmer.current_state == States.BOSS_STATE:
                self.boss_state()

            elif DailyFarmer.current_state == States.VANYA_ALE_STATE:
                self.vanya_ale_state()

            elif DailyFarmer.current_state == States.FORT_SOLGRESS_STATE:
                self.fort_solgress_state()

            elif DailyFarmer.current_state == States.SPECIAL_EVENT_FS_STATE:
                self.special_event_fs_state()
            elif DailyFarmer.current_state == States.FINISHED_SPECIAL_EVENT_FS:
                self.finished_special_event_fs_state()

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
            elif DailyFarmer.current_state == States.PLAYING_BRAWL:
                self.playing_brawl_state()
            elif DailyFarmer.current_state == States.FINISHED_BRAWL:
                self.finished_brawl_state()

            elif DailyFarmer.current_state == States.AD_WHEEL:
                self.ad_wheel_state()

            elif DailyFarmer.current_state == States.EXIT_FARMER:
                if self.exit_farmer_state():
                    return

            time.sleep(1)
