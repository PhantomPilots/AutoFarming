import sys
import threading
import time
from datetime import datetime
from enum import Enum, auto

import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import (
    CHECK_IN_HOUR,
    MINUTES_TO_WAIT_BEFORE_LOGIN,
    PACIFIC_TIMEZONE,
    IFarmer,
)
from utilities.general_farmer_interface import States as GlobalStates
from utilities.general_fighter_interface import IBattleStrategy, IFighter
from utilities.indura_fighter import InduraFighter
from utilities.indura_fighting_strategies import InduraBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    click_im,
    crop_image,
    display_image,
    find,
    find_and_click,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="GuildBossLogger", log_to_file=False)


class States(Enum):
    GOING_TO_GB = auto()
    FINDING_BOSS = auto()
    FIGHTING = auto()


class GuildBossFarmer(IFarmer):

    num_fights = 0

    def __init__(
        self,
        starting_state=States.GOING_TO_GB,
        battle_strategy: IBattleStrategy = None,  # No need
        do_dailies=False,  # Do we halt demon farming to do dailies?
        do_daily_pvp=False,  # If we do dailies, do we do PVP?
        password: str = None,
    ):
        # To initialize the Daily Farmer thread
        super().__init__()

        self.current_state = starting_state

        # Set specific properties of our DailyFarmer
        IFarmer.daily_farmer.set_daily_pvp(do_daily_pvp)
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)
        self.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming to do daily missions at {CHECK_IN_HOUR}h PST.")

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to farming demons"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming Guild Boss.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_GB

    def going_to_gb_state(self):
        screenshot, window_location = capture_window()

        if find(vio.kh_rank, screenshot):
            self.current_state = States.FINDING_BOSS
            print(f"Moving to state {self.current_state}")
            return

        find_and_click(vio.knighthood_boss, screenshot, window_location)

        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

    def finding_boss_state(self):
        screenshot, window_location = capture_window()

        if find(vio.startbutton, screenshot):
            self.current_state = States.FIGHTING
            print(f"Moving to state {self.current_state}")
            return

        # If we find it, go into the fight!
        find_and_click(vio.belgius_hel, screenshot, window_location)

        # Search until we find the Belgius hel
        if not find(vio.belgius_hel, screenshot):
            click_im(Coordinates.get_coordinates("change_gb"), window_location)
            time.sleep(1)

    def fighting(self):
        screenshot, window_location = capture_window()

        # If we've ended the fight...
        find_and_click(vio.boss_destroyed, screenshot, window_location, threshold=0.6)
        find_and_click(vio.episode_clear, screenshot, window_location)
        find_and_click(vio.boss_results, screenshot, window_location)
        find_and_click(vio.boss_mission, screenshot, window_location)
        find_and_click(vio.daily_quest_info, screenshot, window_location)
        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            logger.info(f"We've used {IFarmer.stamina_pots} stamina pots")
            return

        find_and_click(vio.skip, screenshot, window_location)
        # Weird that here, we need a threshold of 0.7 for the AUTO button... But seems to work?
        find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.8)

        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.again, screenshot):

            # First, if it's time to check in, do it
            if self.check_for_dailies():
                return
            # Reset the daily checkin flag for tomorrow after we're done
            self.maybe_reset_daily_checkin_flag()

            # If we're not checking in, let's keep fighting
            find_and_click(vio.again, screenshot, window_location)
            GuildBossFarmer.num_fights += 1
            logger.info(f"Did {GuildBossFarmer.num_fights} runs. Re-starting the fight!")

        elif find(vio.failed, screenshot):
            print("Oh no, we have lost :( Retrying...")
            self.current_state = States.FINDING_BOSS
            # TODO: The line below may cause a bot lock, may have to fix it
            find_and_click(vio.ok_main_button, screenshot, window_location)

    def run(self):

        while True:
            # Try to reconnect first
            if not (success := check_for_reconnect()):
                # We had to restart the game! Let's log back in immediately
                print("Let's try to log back in immediately...")
                IFarmer.first_login = True

            # Check if we need to log in again!
            self.check_for_login_state()

            if self.current_state == States.GOING_TO_GB:
                self.going_to_gb_state()

            elif self.current_state == States.FINDING_BOSS:
                self.finding_boss_state()

            elif self.current_state == States.FIGHTING:
                self.fighting()

            elif self.current_state == GlobalStates.DAILY_RESET:
                self.daily_reset_state()

            elif self.current_state == GlobalStates.CHECK_IN:
                self.check_in_state()

            elif self.current_state == GlobalStates.DAILIES_STATE:
                self.dailies_state()

            elif self.current_state == GlobalStates.FORTUNE_CARD:
                self.fortune_card_state()

            elif self.current_state == GlobalStates.LOGIN_SCREEN:
                self.login_screen_state(initial_state=States.GOING_TO_GB)

            # We need the loop to run very fast
            time.sleep(0.7)
