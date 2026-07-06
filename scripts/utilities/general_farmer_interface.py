import abc
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import utilities.vision_images as vio
from utilities.capture_window import capture_window
from utilities.constants import *
from utilities.coordinates import Coordinates
from utilities.daily_farming_logic import DailyFarmer
from utilities.daily_farming_logic import States as DailyFarmerStates
from utilities.general_fighter_interface import IFighter
from utilities.app_config import get_minutes_to_wait_before_login
from utilities.utilities import (
    check_for_reconnect,
    close_game,
    drag_im,
    find,
    find_and_click,
    press_key,
    type_word,
)


class States(Enum):
    LOGIN_SCREEN = 0
    DAILY_RESET = 1
    CHECK_IN = 2
    DAILIES_STATE = 6
    FORTUNE_CARD = 7


@dataclass
class ResetFlowIntent:
    resume_state: object | None
    run_check_in: bool
    run_daily_missions: bool


class IFarmerMeta(abc.ABCMeta):
    """Metaclass that auto-prints [POT] whenever stamina_pots is incremented."""

    @property
    def stamina_pots(cls):
        return cls._stamina_pots

    @stamina_pots.setter
    def stamina_pots(cls, value):
        old = getattr(cls, "_stamina_pots", 0)
        cls._stamina_pots = value
        if value > old:
            print("[POT]")


class IFarmer(metaclass=IFarmerMeta):
    """Generic farmer interface."""

    # For thread-safe variables
    _lock = threading.Lock()

    # For type helping
    current_state: int
    fighter: IFighter
    _stamina_pots: int = 0  # managed by IFarmerMeta — use IFarmer.stamina_pots

    # Keep track of the defeats in an organized manner
    dict_of_defeats = defaultdict(int)

    # Store the account password in this instance
    password: str | None = None

    # The thread for doing dailies
    dailies_thread: threading.Thread | None = None
    # Keep track if we've done the daily check in
    daily_checkin = False
    # More dailies stuff
    logged_out_time: float = time.time()
    first_login: bool = False

    # To allow every farmer instance to do dailies
    daily_farmer = None

    # Whether we want to do dailies
    do_dailies: bool = False

    # To keep track of whether we're doing dailies
    doing_dailies = False

    # Manual keepalive support for long-running operations with no state/click changes
    _keepalive_until: float = 0.0
    _keepalive_reason: str | None = None

    def __init__(self, *, do_daily_pvp: bool = False):
        """Just to initialize the Daily Farmer"""
        self._keepalive_until = 0.0
        self._keepalive_reason = None
        self._reset_flow_intent: ResetFlowIntent | None = None
        IFarmer.daily_farmer = DailyFarmer(
            starting_state=DailyFarmerStates.IN_TAVERN_STATE,
            do_daily_pvp=do_daily_pvp,
            complete_callback=None,
        )

    def keep_alive(self, duration_seconds: float = 120, reason: str | None = None):
        """Emit a manual keepalive to temporarily suppress runtime stuck alerts.

        Use this in farmer logic for known long-running phases where state and click activity
        are legitimately quiet (for example, long animation, loading, or battle waits).
        """
        keepalive_seconds = max(0.0, float(duration_seconds))
        keepalive_until = time.time() + keepalive_seconds

        with IFarmer._lock:
            self._keepalive_until = max(self._keepalive_until, keepalive_until)
            if reason is not None:
                self._keepalive_reason = reason

    def get_keepalive_deadline(self) -> float:
        """Return the keepalive deadline timestamp (epoch seconds)."""
        with IFarmer._lock:
            return self._keepalive_until

    def before_state_loop_iteration(self) -> None:
        """Hook called at the beginning of each shared state-loop iteration."""

    def on_unknown_state(self) -> None:
        """Raise a clear error when a farmer reaches a state it cannot dispatch."""
        raise RuntimeError(f"Unknown farmer state: {self.current_state}")

    def handle_global_state(self, login_return_state: States) -> bool:
        """Handle global farmer states shared by multiple farming loops."""
        if self.current_state == States.DAILY_RESET:
            self.daily_reset_state()
            return True

        if self.current_state == States.CHECK_IN:
            self.check_in_state()
            return True

        if self.current_state == States.DAILIES_STATE:
            self.dailies_state()
            return True

        if self.current_state == States.FORTUNE_CARD:
            self.fortune_card_state()
            return True

        if self.current_state == States.LOGIN_SCREEN:
            self.login_screen_state(initial_state=login_return_state)
            return True

        return False

    def run_state_loop(
        self,
        state_handlers: dict,
        *,
        login_return_state,
        sleep_seconds=0.6,
        check_reconnect=True,
        login_check=True,
    ):
        """Run a farmer's local state machine with shared reconnect/login/global-state handling."""
        while True:
            if check_reconnect and not check_for_reconnect():
                print("Let's try to log back in immediately...")
                IFarmer.first_login = True

            self.before_state_loop_iteration()

            if login_check:
                self.check_for_login_state()

            if self.handle_global_state(login_return_state):
                time.sleep(sleep_seconds)
                continue

            state_handler = state_handlers.get(self.current_state)
            if state_handler is None:
                self.on_unknown_state()

            state_handler()
            time.sleep(sleep_seconds)

    def stop_fighter_thread(self):
        """Send a STOP signal to the IFighter thread"""
        if hasattr(self, "fighter") and isinstance(self.fighter, IFighter):
            print("STOPPING FIGHTER!")
            self.fighter.stop_fighter()

    def exit_message(self):
        """Final message to display on the screen when CTRL+C happens"""
        print(f"We used {IFarmer.stamina_pots} stamina pots.")

    def print_defeats(self):
        """Print on-screen the defeats"""
        if len(IFarmer.dict_of_defeats):
            print("Defeats:")
            for key, val in IFarmer.dict_of_defeats.items():
                print(f"* {key} -> Lost {val} times")

    def fight_complete_callback(self, **kwargs):
        """Callback used for the fighter to notify the farmer when the fight has ended.
        Not abstract since not all farmers use a fighter, and therefore a 'fight complete callback'.
        """

    def exit_farmer_state(self, msg: str | None = None):
        """Exit the farming!"""
        if msg is None:
            msg = "Terminating process: farming cycle completed."
        raise KeyboardInterrupt(msg)

    def _start_reset_flow(
        self,
        *,
        resume_state=None,
        run_check_in: bool = True,
        run_daily_missions: bool = False,
    ) -> None:
        """Enter the shared post-reset flow with an explicit completion target."""
        if resume_state is None:
            resume_state = self.current_state

        self._reset_flow_intent = ResetFlowIntent(
            resume_state=resume_state,
            run_check_in=run_check_in,
            run_daily_missions=run_daily_missions,
        )
        self.current_state = States.DAILY_RESET

    def _get_reset_flow_intent(self) -> ResetFlowIntent:
        """Return the active reset intent, creating the default scheduled-dailies intent if needed."""
        if self._reset_flow_intent is None:
            self._reset_flow_intent = ResetFlowIntent(
                resume_state=None,
                run_check_in=True,
                run_daily_missions=IFarmer.do_dailies or IFarmer.doing_dailies,
            )
        return self._reset_flow_intent

    def _complete_check_in_flow(self) -> None:
        """Finish check-in by either starting daily missions or resuming the interrupted farmer."""
        intent = self._get_reset_flow_intent()
        IFarmer.daily_checkin = True

        if intent.run_daily_missions:
            print("Going to do all dailies!")
            self.current_state = States.DAILIES_STATE
            self._reset_flow_intent = None
            return

        print("Daily check-in complete. Resuming farming.")
        self.current_state = intent.resume_state
        self._reset_flow_intent = None

    def _handle_daily_reset_entrypoint(self, screenshot, window_location) -> bool:
        """Handle daily reset popups from safe navigation states."""
        if (
            find_and_click(vio.skip, screenshot, window_location, threshold=0.6)
            or find(vio.fortune_card, screenshot, threshold=0.8)
            or find_and_click(vio.cross, screenshot, window_location)
            or find(vio.membership_perk, screenshot)
        ):
            self._start_reset_flow(run_daily_missions=IFarmer.do_dailies)
            return True

        return False

    def check_for_dailies(self) -> bool:
        """Return whether we have to do our dailies"""
        now = datetime.now(PACIFIC_TIMEZONE)
        if self.do_dailies and (not IFarmer.daily_checkin and now.hour == CHECK_IN_HOUR):
            print("Let's do all the dailies!")
            self._start_reset_flow(run_daily_missions=True)
            return True
        return False

    def maybe_reset_daily_checkin_flag(self):
        """Reset the flag for the next day"""
        now = datetime.now(PACIFIC_TIMEZONE)
        if now.hour > CHECK_IN_HOUR and IFarmer.daily_checkin:
            print("Resetting daily checkin")
            IFarmer.daily_checkin = False

    def login_screen_state(self, initial_state: States):
        """We're at the login screen, need to login!"""
        screenshot, window_location = capture_window()

        # First of all, if we have a 'cancel', click that first!
        if find_and_click(vio.cancel, screenshot, window_location):
            return

        # Flag to indicate if a successful login branch was detected
        login_attempted = False

        if find(vio.tavern, screenshot):
            print("Logged in successfully! Going back to the previous state...")
            if IFarmer.doing_dailies:
                self._start_reset_flow(resume_state=initial_state, run_daily_missions=True)
            else:
                self.current_state = initial_state
            login_attempted = True
            # Reset the 'doing_dailies' flag
            IFarmer.doing_dailies = False
        elif find(vio.connection_confrm_expired, screenshot):
            print("Connection confirmation expired!")
            close_game()
            return

        # Only try to log in if enough time has passed since the last logout
        if (
            not login_attempted
            and not IFarmer.first_login
            and time.time() - IFarmer.logged_out_time < get_minutes_to_wait_before_login() * 60
        ):
            time.sleep(1)
            return

        # In case we have an update
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if (
            find_and_click(vio.skip, screenshot, window_location, threshold=0.6)
            or find(vio.fortune_card, screenshot, threshold=0.8)
            or find_and_click(vio.cross, screenshot, window_location)
            or find(vio.membership_perk, screenshot)
        ):
            print("We're seeing a daily reset!")
            self._start_reset_flow(
                resume_state=initial_state,
                run_daily_missions=IFarmer.do_dailies or IFarmer.doing_dailies,
            )
            login_attempted = True
            IFarmer.doing_dailies = False

        # In case the game needs to update
        elif find_and_click(vio.yes, screenshot, window_location):
            print("Downloading update...")

        elif find_and_click(
            vio.global_server,
            screenshot,
            window_location,
            threshold=0.6,
            point_coordinates=Coordinates.get_coordinates("center_screen"),
        ):
            print("Trying to log back in...")

        # Click on the password field
        elif find_and_click(vio.password, screenshot, window_location):
            # Type the password and press enter
            type_word(IFarmer.password)
            press_key("enter")

        # Update first_login flag only once if a successful login/reset was detected
        if login_attempted and IFarmer.first_login:
            print("First login attempt was successful!")
            IFarmer.first_login = False

    def check_for_login_state(self):
        """Check whether we need to switch to the login state"""
        if IFarmer.password is None:
            # Skip the checks if we don't have a password
            return

        screenshot, window_location = capture_window()

        # Check if duplicate connection, if so click on 'ok_main_button'
        if find(vio.duplicate_connection, screenshot):
            find_and_click(vio.ok_main_button, screenshot, window_location)

            # And close the fighter thread if open
            self.stop_fighter_thread()

        elif find(vio.password, screenshot) and self.current_state != States.LOGIN_SCREEN:
            self.current_state = States.LOGIN_SCREEN
            IFarmer.logged_out_time = time.time()
            print(f"We've been logged out! Waiting {get_minutes_to_wait_before_login()} mins to log back in...")

            # And close the fighter thread if open
            self.stop_fighter_thread()

            # Kill the dailies thread if it's running!
            if IFarmer.dailies_thread is not None and IFarmer.dailies_thread.is_alive():
                print("We were doing dailies! Let's continue when we log back in...")
                IFarmer.doing_dailies = True
                IFarmer.daily_farmer.kill_farmer()

    def fortune_card_state(self):
        """Open the fortune card"""
        screenshot, window_location = capture_window()

        if find(vio.ok_main_button, screenshot, threshold=0.8):
            print("Got a good fortune? Going back to daily reset state")
            self.current_state = States.DAILY_RESET
            return

        drag_im(
            Coordinates.get_coordinates("daily_fortune_bottom"),
            Coordinates.get_coordinates("daily_fortune_top"),
            window_location,
        )

    def daily_reset_state(self):
        """Click on skip as much as needed, check in, then go back to doing whatever we were doing"""
        intent = self._get_reset_flow_intent()
        screenshot, window_location = capture_window()

        if find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a fortune card!")
            self.current_state = States.FORTUNE_CARD
            return

        # If we see a "cross", click it before clicking the OK button
        if find_and_click(vio.cross, screenshot, window_location, sleep_time=1):
            screenshot, window_location = capture_window()

        # Cancel the demon search
        find_and_click(vio.cancel_realtime, screenshot, window_location, sleep_time=1)

        # We may be receiving the daily rewards now
        find_and_click(vio.skip, screenshot, window_location, threshold=0.6, sleep_time=1)

        # We may be receiving the monthly subscription too
        if find(vio.membership_perk, screenshot):
            press_key("esc")

        # In case we're in the knighthood or something!
        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return

        # Go to CHECK IN state
        if find(vio.knighthood, screenshot) or find(vio.search_for_a_kh, screenshot):
            if intent.run_check_in:
                print("Going to CHECK IN state")
                self.current_state = States.CHECK_IN
            else:
                self.current_state = intent.resume_state
                self._reset_flow_intent = None
            return

        # Click on "Knighthood"
        if find_and_click(
            vio.battle_menu,
            screenshot,
            window_location,
            threshold=0.6,
            point_coordinates=Coordinates.get_coordinates("knighthood"),
            sleep_time=1,
        ):
            return

        # In case we have a "Start" mission
        find_and_click(vio.start_quest, screenshot, window_location)

        # In case an OK pop-up shows up
        find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.6)

        # Go to tavern
        if not find_and_click(vio.tavern, screenshot, window_location):
            # If we don't see the tavern button, just click on "back" till we get there
            find_and_click(vio.back, screenshot, window_location)

    def check_in_state(self):
        """Check in, and go back to"""
        screenshot, window_location = capture_window()

        # In case some random GW popup appears
        find_and_click(vio.cross, screenshot, window_location)

        if find(vio.search_for_a_kh, screenshot):
            print("We're not in any KH, we cannot check in...")
            press_key("esc")
            self._complete_check_in_flow()
            return

        # Check in
        if find_and_click(vio.check_in, screenshot, window_location, sleep_time=2):
            print("Checked in successfully!")

        # Click on the reward
        find_and_click(vio.check_in_reward, screenshot, window_location, sleep_time=1)

        # Exit the knighthood after checking in...
        if find(vio.check_in_complete, screenshot):
            press_key("esc")

        if find(vio.battle_menu, screenshot, threshold=0.6):
            self._complete_check_in_flow()

    def dailies_state(self):
        """Run the thread to do all dailies"""
        with IFarmer._lock:
            if (
                IFarmer.dailies_thread is None or not IFarmer.dailies_thread.is_alive()
            ) and self.current_state == States.DAILIES_STATE:
                IFarmer.dailies_thread = threading.Thread(target=self.daily_farmer.run, daemon=True)
                IFarmer.dailies_thread.start()
                print("Dailies farmer started!")

    @abc.abstractmethod
    def run(self):
        """Needs to be implemented by a subclass"""
