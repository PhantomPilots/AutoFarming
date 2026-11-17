import time
from enum import Enum, auto

import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.app_config import get_minutes_to_wait_before_login
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import CHECK_IN_HOUR, IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.reward_sets import GUILD_BOSS_REWARDS
from utilities.reward_tracker import RewardTracker
from utilities.utilities import (
    capture_window,
    click_im,
    find,
    find_and_click,
    is_game_window_focused,
    press_key,
)

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
        do_daily_pvp=True,  # If we do dailies, do we do PVP?
        password: str = None,
        max_stamina_pots: int | float = float("inf"),  # Stop farming once we've used this many stamina pots
    ):
        # To initialize the Daily Farmer thread
        super().__init__(do_daily_pvp=do_daily_pvp)

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {get_minutes_to_wait_before_login()} mins. before attempting a log in.")

        self.current_state = starting_state
        self.max_stamina_pots = max_stamina_pots
        if max_stamina_pots < float("inf"):
            print(f"We'll use up to {max_stamina_pots} stamina pots.")

        # Reads the reward tiles of the result screens, the GUI sums the '[REWARDS]' lines
        self.rewards = RewardTracker(GUILD_BOSS_REWARDS, logger)
        self._reset_result_tracking()

        # Set specific properties of our DailyFarmer
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)
        IFarmer.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming to do daily missions at {CHECK_IN_HOUR}h PST.")

    def _reset_result_tracking(self):
        self._victory_seen = False
        self._clear_counted = False
        self.rewards.give_up()

    def handle_global_state(self, login_return_state):
        if not isinstance(self.current_state, States):
            self._reset_result_tracking()
        return super().handle_global_state(login_return_state)

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to farming demons"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming Guild Boss.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_GB

    def going_to_gb_state(self):
        self._reset_result_tracking()
        screenshot, window_location = capture_window()

        if find(vio.kh_rank, screenshot):
            self.current_state = States.FINDING_BOSS
            print("Looking for the Guild Boss.")
            return

        find_and_click(vio.knighthood_boss, screenshot, window_location)

        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

    def finding_boss_state(self):
        self._reset_result_tracking()
        screenshot, window_location = capture_window()

        if find(vio.startbutton, screenshot):
            self.current_state = States.FIGHTING
            print("Starting the Guild Boss fight.")
            return

        # If we find it, go into the fight!
        find_and_click(vio.belgius_hel, screenshot, window_location)

        # Search until we find the Belgius hel
        if not find(vio.belgius_hel, screenshot):
            click_im(Coordinates.get_coordinates("change_gb"), window_location)
            time.sleep(1)

    def fighting_state(self):
        screenshot, window_location = capture_window()

        # First, check if we should go back to the initial state
        if find(vio.belgius_hel, screenshot, threshold=0.8):
            self._reset_result_tracking()
            print("We're somehow not fighting anymore, let's go back to fighting...")
            self.current_state = States.FINDING_BOSS
            return

        if find(vio.failed, screenshot):
            self._reset_result_tracking()
            print("Oh no, we have lost :( Retrying...")
            self.current_state = States.FINDING_BOSS
            find_and_click(vio.ok_main_button, screenshot, window_location)
            return

        self._victory_seen = self._victory_seen or find(vio.victory, screenshot, threshold=0.6)
        ok_visible = find(vio.ok_main_button, screenshot)
        if self._victory_seen and ok_visible:
            if not self.rewards.read_before_continue(screenshot):
                return
        else:
            # Advance intermediate screens using a fresh screenshot after each click.
            for image, threshold in (
                (vio.boss_destroyed, 0.6),
                (vio.episode_clear, 0.7),
                (vio.daily_quest_info, 0.7),
                (vio.skip, 0.7),
            ):
                if find_and_click(image, screenshot, window_location, threshold=threshold):
                    return
            if find_and_click(vio.boss_mission, screenshot, window_location):
                if not self._clear_counted:
                    self._clear_counted = True
                    GuildBossFarmer.num_fights += 1
                    logger.info(f"Did {GuildBossFarmer.num_fights} runs. Re-starting the fight!")
                    print("[CLEAR]")
                    self.rewards.run_finished()
                return
            if find_and_click(vio.boss_results, screenshot, window_location):
                return
            if self._victory_seen:
                return

        # We may need to restore stamina
        if find(vio.stamina_pot, screenshot) and find(vio.restore_stamina, screenshot):
            if IFarmer.stamina_pots >= self.max_stamina_pots:
                self.exit_farmer_state("Potion limit reached. Farming stopped.")
            if find_and_click(vio.restore_stamina, screenshot, window_location):
                IFarmer.stamina_pots += 1
                logger.info(f"We've used {IFarmer.stamina_pots} stamina pots")
                return

        # Weird that here, we need a threshold of 0.7 for the AUTO button... But seems to work?
        clicked_image = find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.8)

        if find_and_click(vio.startbutton, screenshot, window_location):
            self._reset_result_tracking()
            return

        if find(vio.again, screenshot):
            # First, if it's time to check in, do it
            if self.check_for_dailies():
                press_key("esc")  # To make sure we'll be in the right screen for DAILIES
                self._reset_result_tracking()
                return
            # Reset the daily checkin flag for tomorrow after we're done
            self.maybe_reset_daily_checkin_flag()

            # If we're not checking in, let's keep fighting
            if find_and_click(vio.again, screenshot, window_location):
                self._reset_result_tracking()
            return

        if self._victory_seen and ok_visible:
            find_and_click(vio.ok_main_button, screenshot, window_location)
            return

        if not clicked_image and is_game_window_focused():
            click_im((279, 197), window_location)

    def run(self):

        self.run_state_loop(
            {
                States.GOING_TO_GB: self.going_to_gb_state,
                States.FINDING_BOSS: self.finding_boss_state,
                States.FIGHTING: self.fighting_state,
            },
            login_return_state=States.GOING_TO_GB,
            sleep_seconds=0.7,
        )
