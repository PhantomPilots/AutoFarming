import time
import threading
from enum import Enum, auto

import utilities.vision_images as vio
from utilities.app_config import get_minutes_to_wait_before_login
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import CHECK_IN_HOUR, IFarmer
from utilities.general_fighter_interface import IBattleStrategy, IFighter
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    click_im,
    find,
    find_and_click,
    press_key,
)
from utilities.vision_images import Vision

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
        battle_strategy: type[IBattleStrategy] | None = None,
        do_dailies=False,  # Do we halt demon farming to do dailies?
        do_daily_pvp=True,  # If we do dailies, do we do PVP?
        password: str = None,
        push_week: bool = False,
        guild_boss: Vision = vio.belgius_hel,
        fighter_cls: type[IFighter] | None = None,
    ):
        if push_week and (fighter_cls is None or battle_strategy is None):
            raise ValueError("Push-week Guild Boss farming requires a fighter class and battle strategy.")

        self.push_week = push_week
        self.guild_boss = guild_boss if push_week else vio.belgius_hel
        self.battle_strategy = battle_strategy
        self.fighter_cls = fighter_cls
        self.fighter: IFighter | None = None
        self.fighter_thread: threading.Thread | None = None

        # To initialize the Daily Farmer thread
        super().__init__(do_daily_pvp=do_daily_pvp)

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {get_minutes_to_wait_before_login()} mins. before attempting a log in.")

        self.current_state = starting_state
        # Set specific properties of our DailyFarmer
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)
        IFarmer.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming to do daily missions at {CHECK_IN_HOUR}h PST.")

    def _start_push_week_fighter_if_needed(self, *, fight_ended: bool) -> None:
        """Lazily start the manual fighter once for an active push-week battle."""
        if not self.push_week or fight_ended:
            return

        if self.fighter_thread is not None and self.fighter_thread.is_alive():
            return

        if self.fighter is None:
            self.fighter = self.fighter_cls(battle_strategy=self.battle_strategy, callback=None)

        self.fighter.prepare_for_new_fight()
        self.fighter_thread = threading.Thread(target=self.fighter.run, daemon=True)
        self.fighter_thread.start()
        print("Guild Boss fighter started!")

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
        find_and_click(self.guild_boss, screenshot, window_location)

        # Search until we find the selected Guild Boss
        if not find(self.guild_boss, screenshot):
            click_im(Coordinates.get_coordinates("change_gb"), window_location)
            time.sleep(1)

    def fighting_state(self):
        screenshot, window_location = capture_window()

        # First, check if we should go back to the initial state
        if find(self.guild_boss, screenshot, threshold=0.8):
            print("We're somehow not fighting anymore, let's go back to fighting...")
            self.stop_fighter_thread()
            self.current_state = States.FINDING_BOSS
            return

        # If we've ended the fight...
        fight_ended = find_and_click(vio.boss_destroyed, screenshot, window_location, threshold=0.6)
        fight_ended = find_and_click(vio.episode_clear, screenshot, window_location) or fight_ended
        fight_ended = find_and_click(vio.daily_quest_info, screenshot, window_location) or fight_ended
        if find_and_click(vio.boss_mission, screenshot, window_location):
            self.stop_fighter_thread()
            GuildBossFarmer.num_fights += 1
            logger.info(f"Did {GuildBossFarmer.num_fights} runs. Re-starting the fight!")
            print("[CLEAR]")
            return
        fight_ended = find_and_click(vio.boss_results, screenshot, window_location) or fight_ended
        if fight_ended:
            self.stop_fighter_thread()

        # We may need to restore stamina
        if find(vio.stamina_pot, screenshot) and find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            logger.info(f"We've used {IFarmer.stamina_pots} stamina pots")
            return

        self._start_push_week_fighter_if_needed(fight_ended=fight_ended)

        find_and_click(vio.skip, screenshot, window_location)
        if not self.push_week:
            # Weird that here, we need a threshold of 0.7 for the AUTO button... But seems to work?
            find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.8)

        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.again, screenshot):
            # First, if it's time to check in, do it
            if self.check_for_dailies():
                self.stop_fighter_thread()
                press_key("esc")  # To make sure we'll be in the right screen for DAILIES
                return
            # Reset the daily checkin flag for tomorrow after we're done
            self.maybe_reset_daily_checkin_flag()

            # If we're not checking in, let's keep fighting
            find_and_click(vio.again, screenshot, window_location)

        elif find(vio.failed, screenshot):
            print("Oh no, we have lost :( Retrying...")
            self.stop_fighter_thread()
            self.current_state = States.FINDING_BOSS
            # TODO: The line below may cause a bot lock, may have to fix it
            find_and_click(vio.ok_main_button, screenshot, window_location)

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
