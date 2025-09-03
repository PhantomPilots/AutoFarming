import abc
import threading
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum

import utilities.vision_images as vio
from utilities.capture_window import capture_window
from utilities.constants import *
from utilities.coordinates import Coordinates
from utilities.daily_farming_logic import DailyFarmer
from utilities.daily_farming_logic import States as DailyFarmerStates
from utilities.general_fighter_interface import IFighter
from utilities.utilities import (
    click_and_sleep,
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


class IFarmer:
    """Generic farmer interface."""

    # For thread-safe variables
    _lock = threading.Lock()

    # For type helping
    current_state: int
    fighter: IFighter
    stamina_pots: int = 0

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
    daily_farmer = DailyFarmer(
        starting_state=DailyFarmerStates.IN_TAVERN_STATE,
        do_daily_pvp=False,
        complete_callback=None,
    )

    # Whether we want to do dailies
    do_dailies: bool = False

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

    def check_for_dailies(self) -> bool:
        """Return whether we have to do our dailies"""
        now = datetime.now(PACIFIC_TIMEZONE)
        if self.do_dailies and (not IFarmer.daily_checkin and now.hour == CHECK_IN_HOUR):
            print("Going to CHECK IN!")
            self.current_state = States.DAILY_RESET
            return True
        return False

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
            self.current_state = initial_state
            login_attempted = True
        elif find(vio.connection_confrm_expired, screenshot):
            print("Connection confirmation expired!")
            close_game()
            return

        # Only try to log in if enough time has passed since the last logout
        if (
            not login_attempted
            and not IFarmer.first_login
            and time.time() - IFarmer.logged_out_time < MINUTES_TO_WAIT_BEFORE_LOGIN * 60
        ):
            time.sleep(1)
            return

        # In case we have an update
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.skip, screenshot, threshold=0.6) or find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a daily reset!")
            self.current_state = States.DAILY_RESET
            login_attempted = True

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
            print(f"We've been logged out! Waiting {MINUTES_TO_WAIT_BEFORE_LOGIN} mins to log back in...")

            # And close the fighter thread if open
            self.stop_fighter_thread()

            # Kill the dailies thread if it's running!
            if IFarmer.dailies_thread is not None and IFarmer.dailies_thread.is_alive():
                IFarmer.daily_farmer.kill_farmer()

    def fortune_card_state(self):
        """Open the fortune card"""
        screenshot, window_location = capture_window()

        if find(vio.ok_main_button, screenshot, threshold=0.6):
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
        screenshot, window_location = capture_window()

        if find(vio.fortune_card, screenshot, threshold=0.8):
            print("We're seeing a fortune card!")
            self.current_state = States.FORTUNE_CARD
            return

        # If we see a "cross", click it before clicking the OK button
        if find_and_click(vio.cross, screenshot, window_location):
            screenshot, window_location = capture_window()

        # Cancel the demon search
        click_and_sleep(vio.cancel_realtime, screenshot, window_location)

        # We may be receiving the daily rewards now
        click_and_sleep(vio.skip, screenshot, window_location, threshold=0.6)

        # Go to CHECK IN state
        if find(vio.knighthood, screenshot) or find(vio.search_for_a_kh, screenshot):
            print("Going to CHECK IN state")
            self.current_state = States.CHECK_IN
            return

        # Click on "Knighthood"
        if click_and_sleep(
            vio.battle_menu,
            screenshot,
            window_location,
            threshold=0.6,
            point_coordinates=Coordinates.get_coordinates("knighthood"),
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

        if find(vio.search_for_a_kh, screenshot):
            print("We're not in any KH, we cannot check in...")
            press_key("esc")
            self.current_state = States.DAILIES_STATE
            # And reset daily checking
            IFarmer.daily_checkin = True
            return

        # Check in
        if click_and_sleep(vio.check_in, screenshot, window_location, sleep_time=2):
            print("Checked in successfully!")

        # Click on the reward
        click_and_sleep(vio.check_in_reward, screenshot, window_location)

        # Exit the knighthood after checking in...
        if find(vio.check_in_complete, screenshot):
            press_key("esc")

        if find(vio.battle_menu, screenshot, threshold=0.6):
            IFarmer.daily_checkin = True
            print("Going to do all dailies!")
            self.current_state = States.DAILIES_STATE

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
