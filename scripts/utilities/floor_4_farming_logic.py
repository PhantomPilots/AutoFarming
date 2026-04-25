import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.app_config import get_minutes_to_wait_before_login
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import CHECK_IN_HOUR, PACIFIC_TIMEZONE, IFarmer
from utilities.general_farmer_interface import States as GlobalStates
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    drag_im,
    find,
    find_and_click,
)

logger = LoggerWrapper("Floor4Logger", log_file="floor_4.log")
_EXTRA_MODE_MAX_ATTEMPTS = 10


class States(Enum):
    PROCEED_TO_FLOOR = 0
    FIGHTING = 1
    READY_TO_FIGHT = 2
    EXIT_FARMER = 3
    GOING_TO_DB = 4


class IFloor4Farmer(IFarmer):

    # Need to be static across instances
    success_count = 0
    total_count = 0
    reset_count = 0
    dict_of_defeats = defaultdict(int)

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state: States,
        max_runs="inf",
        demonic_beast_image: vio.Vision | None = None,
        extra_mode_source_image: vio.Vision | None = None,
        do_dailies=False,
        password: str | None = None,
        extra_clears: int = 0,
    ):

        super().__init__()

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {get_minutes_to_wait_before_login()} mins. before attempting a log in.")

        # In case we want to do dailies at the specified hour
        IFarmer.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming Floor4 at {CHECK_IN_HOUR} PT to do our dailies!")

        self.max_runs = float(max_runs)
        if self.max_runs < float("inf"):
            print(f"We're gonna clear Floor4 {int(self.max_runs)} times.")

        self.extra_clear_limit = max(0, int(extra_clears))
        if self.max_runs < float("inf") and self.extra_clear_limit > int(self.max_runs):
            print(
                f"Extra clears ({self.extra_clear_limit}) exceed total clears ({int(self.max_runs)}); "
                f"capping extra clears to {int(self.max_runs)}."
            )
            self.extra_clear_limit = int(self.max_runs)
        self.extra_clears_remaining = self.extra_clear_limit
        self.extra_mode_failure_attempts = 0
        self.extra_mode_unavailable = False
        self.pending_extra_clear_credit = False
        if self.extra_clear_limit > 0:
            print(f"We'll try to do {self.extra_clear_limit} Floor 4 clears in extra mode.")

        # Store internally the image of the DemonicBeast we want to fight (Bird/Deer/Dogs)
        self.db_image = demonic_beast_image
        self.extra_mode_source_image = extra_mode_source_image

        # For type helping
        self.current_state = starting_state
        # We will need to develop a specific battle strategy for it
        self.battle_strategy = battle_strategy

        # Placeholder for the thread that will call the fighter logic
        self.fight_thread = None
        self._swipe_attempts = 0

        # For the login/dailies
        IFarmer.daily_farmer.set_daily_pvp(True)
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

    def on_ready_to_fight_before_start(self, screenshot):
        """Called in ``ready_to_fight_state`` after stamina handling, before Start; subclasses may inspect UI."""

    def get_fighter_run_kwargs(self) -> dict:
        """Keyword arguments passed to ``self.fighter.run`` when starting the Floor 4 fight thread."""
        return {}

    def _should_try_extra_mode(self) -> bool:
        return (
            self.extra_clears_remaining > 0
            and not self.extra_mode_unavailable
            and not self.pending_extra_clear_credit
        )

    def _extra_mode_source_visible(self, screenshot) -> bool:
        return self.extra_mode_source_image is not None and find(self.extra_mode_source_image, screenshot, threshold=0.7)

    def _stop_trying_extra_mode(self) -> None:
        self.extra_mode_unavailable = True
        print(
            f"Could not open extra mode after {_EXTRA_MODE_MAX_ATTEMPTS} attempts; "
            "reverting to normal mode for the rest of the run."
        )

    def _record_extra_mode_failure(self, message: str) -> bool:
        self.extra_mode_failure_attempts += 1
        print(f"{message} (attempt {self.extra_mode_failure_attempts}/{_EXTRA_MODE_MAX_ATTEMPTS}).")
        if self.extra_mode_failure_attempts >= _EXTRA_MODE_MAX_ATTEMPTS:
            self._stop_trying_extra_mode()
            return False
        return True

    def _try_prepare_extra_mode(self, screenshot, window_location) -> bool:
        """Return True when this loop handled the screen and normal opening should wait."""
        if not self._should_try_extra_mode():
            return False
        if not (self._extra_mode_source_visible(screenshot) or find(vio.extra_mode, screenshot, threshold=0.75)):
            return False

        attempt = self.extra_mode_failure_attempts + 1
        if not find_and_click(vio.extra_mode, screenshot, window_location, threshold=0.75):
            return self._record_extra_mode_failure("Extra mode requested, but 'extra_mode' was not found")

        print(f"Trying to open Floor 4 in extra mode (attempt {attempt}/{_EXTRA_MODE_MAX_ATTEMPTS}).")
        time.sleep(0.3)
        screenshot, window_location = capture_window()
        if not find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.7):
            return self._record_extra_mode_failure("Clicked extra mode, but the confirmation button did not appear")

        time.sleep(0.3)
        screenshot, _ = capture_window()
        if find(vio.startbutton, screenshot):
            self.extra_mode_failure_attempts = 0
            self.pending_extra_clear_credit = True
            print(
                "Extra mode selected and the stage opened. This extra clear will be consumed on the next "
                "Floor 4 victory (even if this specific run loses first)."
            )
            self.current_state = States.READY_TO_FIGHT
            return True

        return self._record_extra_mode_failure("Clicked extra mode and confirmed it, but the stage did not open")
    def exit_message(self):
        super().exit_message()
        percent = (
            (IFloor4Farmer.success_count / IFloor4Farmer.total_count) * 100 if IFloor4Farmer.total_count > 0 else 0
        )
        print(f"We beat Floor4 {IFloor4Farmer.success_count}/{IFloor4Farmer.total_count} times ({percent:.2f}%).")
        # Log the defeats
        if len(IFloor4Farmer.dict_of_defeats):
            defeat_msg = self._print_defeats()
            logger.info(defeat_msg)

    def _print_defeats(self):
        """Generate a string message to log"""
        str_msg = "Defeats:\n"
        for phase, count in IFloor4Farmer.dict_of_defeats.items():
            str_msg += f"* Phase {phase} -> Lost {count} times.\n"

        return str_msg

    def _search_for_target_demonic_beast(self, screenshot, window_location) -> bool:
        if not find(vio.demonic_beast_battle, screenshot):
            self._swipe_attempts = 0
            return True

        if find(self.db_image, screenshot):
            self._swipe_attempts = 0
            return True

        self._swipe_attempts += 1
        if self._swipe_attempts <= 4:
            print(f"Wrong demonic beast, attempt {self._swipe_attempts}, swiping right...")
            drag_im(
                Coordinates.get_coordinates("right_swipe"),
                Coordinates.get_coordinates("left_swipe"),
                window_location,
            )
            time.sleep(0.5)
            return False

        if self._swipe_attempts <= 8:
            print(f"Wrong demonic beast, attempt {self._swipe_attempts}, swiping left...")
            drag_im(
                Coordinates.get_coordinates("left_swipe"),
                Coordinates.get_coordinates("right_swipe"),
                window_location,
            )
            time.sleep(0.5)
            return False

        print("Couldn't find the target demonic beast after 8 swipes. Resetting the search.")
        self._swipe_attempts = 0
        return False

    def going_to_db_state(self):
        """This should be the original state. Let's go to the DemonicBeast menu"""
        screenshot, window_location = capture_window()

        # We may see a "Cancel", if we just logged back in and we're in the middle of a fight!
        # Just consider that fight as lost...
        if find_and_click(vio.cancel, screenshot, window_location):
            print("We were in the middle of a fight, but let's start it over :(")
            return

        # If we're back in the tavern, click on the battle menu.
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # If we're in the battle menu, click on Demonic Beast
        find_and_click(vio.demonic_beast, screenshot, window_location)

        if not self._search_for_target_demonic_beast(screenshot, window_location):
            return

        # Go into the 'db' section
        find_and_click(self.db_image, screenshot, window_location)

        # Double-check that floor 3 is not cleared
        if find(vio.floor_3_cleared_db, screenshot):
            print("Going to fight the DemonicBeast!")
            self.current_state = States.PROCEED_TO_FLOOR

    def proceed_to_floor_state(self):

        screenshot, window_location = capture_window()

        # First of all, check if we have to do our dailies. If not, go straight to the original states
        if self.check_for_dailies():
            return
        self.maybe_reset_daily_checkin_flag()

        if find(vio.startbutton, screenshot):
            print("Let's GET READY to fight.")
            self.current_state = States.READY_TO_FIGHT
            return

        if self._try_prepare_extra_mode(screenshot, window_location):
            return

        # Click on floor 4 if it's available, then wait for the next loop to inspect the resulting screen.
        if find_and_click(vio.floor_3_cleared_db, screenshot, window_location, threshold=0.7):
            return

        screenshot, window_location = capture_window()

        if find(vio.startbutton, screenshot):
            print("Let's GET READY to fight.")
            self.current_state = States.READY_TO_FIGHT
            return

        if self._try_prepare_extra_mode(screenshot, window_location):
            return

        # In case we need to unlock the floor in the normal path.
        find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.7)

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # Restore stamina if we need to
        if find_and_click(vio.restore_stamina, screenshot, window_location, threshold=0.8):
            IFarmer.stamina_pots += 1
            # screenshot_testing(screenshot, vio.restore_stamina)
            return

        if self.on_ready_to_fight_before_start(screenshot) is False:
            return

        # Try to start the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot) or find(vio.tavern_loading_screen, screenshot):
            # We can move to the next state
            print("Moving to FIGHTING!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """This state contains the entire fight."""

        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location)

        # Set the fighter thread
        if (self.fight_thread is None or not self.fight_thread.is_alive()) and self.current_state == States.FIGHTING:
            print("Floor4 fight started!")
            self.fight_thread = threading.Thread(
                target=self.fighter.run,
                name="Floor4FighterThread",
                daemon=True,
                kwargs=self.get_fighter_run_kwargs(),
            )
            self.fight_thread.start()

        # We may have finished the fight already, let's check if we need to go back to the main screen
        if find(vio.floor_3_cleared_db, screenshot):
            # We finished the fight, let's go back to the main screen
            print("We finished the fight but are still fighting? Get outta here!")
            self.stop_fighter_thread()
            self.current_state = States.PROCEED_TO_FLOOR

    def fight_complete_callback(self, victory=True, **kwargs):
        """Called when the fight logic completes.

        If ``stop_farmer`` is True, the farmer exits immediately without taking the lock,
        incrementing ``total_count``, or updating success/defeat tallies â€” intentional for
        clean shutdown (e.g. a fighter requesting early exit).
        """
        if kwargs.get("stop_farmer", False):
            reason = kwargs.get("reason", "Stopping the Floor 4 farmer.")
            print(reason)
            self.current_state = States.EXIT_FARMER
            return

        with IFarmer._lock:
            IFloor4Farmer.total_count += 1
            if kwargs.get("reset", False):
                IFloor4Farmer.reset_count += 1
            if victory:
                # Transition to another state or perform clean-up actions
                IFloor4Farmer.success_count += 1
                if self.pending_extra_clear_credit and self.extra_clears_remaining > 0:
                    self.extra_clears_remaining -= 1
                    print(f"Consumed one extra clear on victory. Extra clears remaining: {self.extra_clears_remaining}.")
                self.pending_extra_clear_credit = False
                print("FLOOR 4 COMPLETE, WOOO!")
                print("[CLEAR]")
            else:
                phase = kwargs.get("phase", None)
                print(f"The fighter told me they lost{f' on phase {phase}' if phase is not None else ''}... :/")
                print("[LOSS]")
                # Increment the defeat count of the corresponding phase
                if phase is not None:
                    IFloor4Farmer.dict_of_defeats[phase] += 1

            percent = (IFloor4Farmer.success_count / IFloor4Farmer.total_count) * 100
            fight_complete_msg = f"We beat Floor4 a total of {IFloor4Farmer.success_count}/{IFloor4Farmer.total_count} times ({percent:.2f}%)."
            # logger.info(fight_complete_msg)
            if IFloor4Farmer.success_count >= self.max_runs:
                print("Reached maximum number of clears, exiting farmer.")
                self.current_state = States.EXIT_FARMER
                return

            # Don't log the defeats here, only on `exit_message()`
            self.exit_message()

            # Go straight to proceed to floor
            self.current_state = States.PROCEED_TO_FLOOR

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to regular farming"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming Floor 4.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DB

    def run(self):

        print(f"Fighting Floor 4 hard, starting in state {self.current_state}.")

        self.run_state_loop(
            {
                States.GOING_TO_DB: self.going_to_db_state,
                States.PROCEED_TO_FLOOR: self.proceed_to_floor_state,
                States.READY_TO_FIGHT: self.ready_to_fight_state,
                States.FIGHTING: self.fighting_state,
                States.EXIT_FARMER: self.exit_farmer_state,
            },
            login_return_state=States.GOING_TO_DB,
            sleep_seconds=0.6,
        )



