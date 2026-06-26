import time
from enum import Enum, auto

import utilities.vision_images as vio
from utilities.general_farmer_interface import CHECK_IN_HOUR, IFarmer
from utilities.general_farmer_interface import States as GlobalStates
from utilities.utilities import capture_window, find, find_and_click, press_key


class States(Enum):
    GOING_TO_DUNGEON = auto()
    FIGHTING = auto()
    SETTING_UP_CHECKIN = auto()
    SKIP_FIGHT = auto()


class GoldFarmer(IFarmer):
    """Minimal gold farmer skeleton.

    This first step only establishes the farmer contract, the shared dailies/login flow,
    and the initial local state machine entrypoint.
    """

    used_skip_tickets = 0

    def __init__(
        self,
        *,
        starting_state=States.GOING_TO_DUNGEON,
        battle_strategy=None,
        password: str | None = None,
        use_skip_tickets=False,
        max_skip_tickets_to_use=float("inf"),
        do_dailies=False,
        do_daily_pvp=True,
        **kwargs,
    ):
        del battle_strategy, kwargs
        super().__init__(do_daily_pvp=do_daily_pvp)

        self.current_state = starting_state
        self.use_skip_tickets = use_skip_tickets
        if self.use_skip_tickets:
            print("We'll use skip tickets to farm Gold!")
        self.max_skip_tickets_to_use = max_skip_tickets_to_use

        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")

        IFarmer.do_dailies = do_dailies
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

        print("Starting Gold farmer skeleton.")
        if do_dailies:
            print(f"We'll stop farming Gold at {CHECK_IN_HOUR}h PST to do dailies.")

    def going_to_dungeon_state(self):
        """Placeholder entry state for future gold navigation logic."""

        screenshot, window_location = capture_window()

        if find(vio.auto_clear, screenshot) or find(vio.startbutton, screenshot):
            print("Let's fight!")
            self.current_state = States.FIGHTING
            return

        find_and_click(vio.sixth_floor, screenshot, window_location)
        find_and_click(vio.gold_dungeon, screenshot, window_location)
        find_and_click(vio.fs_dungeon, screenshot, window_location)
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

    def fighting_state(self):
        """Fighting!"""
        screenshot, window_location = capture_window()

        if self.check_for_dailies():
            self.current_state = States.SETTING_UP_CHECKIN
            return
        self.maybe_reset_daily_checkin_flag()

        # In case we come from fighting with skip tickets...
        if find_and_click(vio.daily_result, screenshot, window_location):
            return

        # We may need to restore stamina to keep the run going.
        if find(vio.stamina_pot, screenshot) and find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Now, below we can choose to either start the fight, OR use skip tickets!
        if not self.use_skip_tickets:
            if find_and_click(vio.auto_repeat_off, screenshot, window_location):
                return

            find_and_click(vio.startbutton, screenshot, window_location)

        elif GoldFarmer.used_skip_tickets < self.max_skip_tickets_to_use:
            print("Let's use skip tickets!")
            self.current_state = States.SKIP_FIGHT

        else:
            print("[WARN] We've used all our skip tickets, let's farm Gold normally now!")
            self.use_skip_tickets = False

    def skipping_fight_state(self):
        """For when using skip tickets..."""
        screenshot, window_location = capture_window()

        if find(vio.daily_result, screenshot):
            self.current_state = States.FIGHTING
            return

        # We're using skip tickets :)
        if find(vio.max_skip_tickets, screenshot):
            # Click on MAX twice, then click on START auto-clear!
            find_and_click(vio.max_skip_tickets, screenshot, window_location, sleep_time=0.5)
            find_and_click(vio.max_skip_tickets, screenshot, window_location, sleep_time=0.5)
            if find_and_click(vio.strart_auto_clear, screenshot, window_location):
                GoldFarmer.used_skip_tickets += 30
                print(f"We've used {GoldFarmer.used_skip_tickets} skip tickets so far.")

        # If not, try to click on auto-clear
        find_and_click(vio.auto_clear, screenshot, window_location)

    def setting_up_checkin_state(self):
        """Setting up checkin!"""
        screenshot, window_location = capture_window()

        if find(vio.pause_fight, screenshot):
            press_key("esc")
            return

        if find(vio.tavern, screenshot):
            self.current_state = GlobalStates.DAILY_RESET
            return

        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.forfeit, screenshot, window_location)

    def dailies_complete_callback(self):
        """Resume gold farming after the shared DailyFarmer finishes."""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming Gold.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DUNGEON

    def run(self):
        print("Farming Gold!")

        self.run_state_loop(
            {
                States.GOING_TO_DUNGEON: self.going_to_dungeon_state,
                States.FIGHTING: self.fighting_state,
                States.SETTING_UP_CHECKIN: self.setting_up_checkin_state,
                States.SKIP_FIGHT: self.skipping_fight_state,
            },
            login_return_state=States.GOING_TO_DUNGEON,
            sleep_seconds=0.5,
        )
