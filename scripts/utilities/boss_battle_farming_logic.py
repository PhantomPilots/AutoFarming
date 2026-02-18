import time
from enum import Enum, auto

import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper, logging
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    move_to_location,
    find,
    find_and_click,
    press_key,
    click_and_sleep
)

logger = LoggerWrapper("boss_battle_logger", level=logging.INFO, log_to_file=False)


class States(Enum):
    GOING_TO_DUNGEON = auto()
    OPENING_DUNGEON = auto()
    GOING_TO_FLOOR_STATE = auto()
    GET_READY = auto()
    FIGHTING = auto()
    RESTART_FIGHT = auto()
    RUN_ENDED = auto()


class BossBattleFarmer(IFarmer):
    """Boss battle farmer"""

    # How many runs we've done?
    num_runs_complete = 0

    # To avoid counting multiple finished runs if the "finished_auto_repeat_fight" image is detected for multiple consecutive frames
    finished_run_lockout_until: float = 0.0

    def __init__(
        self,
        *,
        starting_state=States.GOING_TO_DUNGEON,
        battle_strategy=None,
        **kwargs,
    ):
        self.current_state = starting_state
        print(f"Starting Boss Battles farmer")

    def going_to_dungeon_state(self):
        """Let's go to the dungeon"""
        screenshot, window_location = capture_window()

        # Click on battle menu
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)
        # Click on boss battle menu
        if find_and_click(vio.boss_menu, screenshot, window_location):
            # Move the mouse out of the way... coincidentally, clicking on boss_menu will leave the mouse over the stage so image recognition fails
            move_to_location(Coordinates.get_coordinates("center_screen"), window_location)
            time.sleep(0.5)
        # Turn off simulatanous clear
        find_and_click(vio.sim_clear_on, screenshot, window_location, threshold=0.9)
        # Turn off activate all
        find_and_click(vio.activate_all_on, screenshot, window_location, threshold=0.9)
        # Click on one star difficulty
        find_and_click(vio.boss_one_star, screenshot, window_location, threshold=0.9)
        # Find the actual stage
        if find(vio.stage_melee_of_phantasms, screenshot):
            self.current_state = States.OPENING_DUNGEON
            print(f"Going to {self.current_state}")

    def opening_dungeon_state(self):
        screenshot, window_location = capture_window()

        if click_and_sleep(vio.stage_melee_of_phantasms, screenshot, window_location, sleep_time=0.5):
            # We're re-opening the floor!
            self.current_state = States.GOING_TO_FLOOR_STATE
            print(f"Going to {self.current_state}")

    def going_to_floor_state(self):
        """Dungeon is open, let's go to the floor"""
        screenshot, window_location = capture_window()

        if find(vio.death_match_vanya, screenshot):
            if find_and_click(vio.cancel, screenshot, window_location):
                print("We popped a death match, cancelling it and continuing to the floor")
            return

        if find(vio.startbutton, screenshot):
            # Let's go to proceed to battle!
            self.current_state = States.GET_READY
            print(f"Going to {self.current_state}")
            return

        find_and_click(vio.boss_floor_extreme, screenshot, window_location)

    def get_ready_state(self):
        """Prepare the fight and go!"""
        screenshot, window_location = capture_window()

        if find_and_click(vio.auto_repeat_off, screenshot, window_location, threshold=0.8):
            return

        # Let's fight!
        if find(vio.startbutton, screenshot):
            print("LET'S FIGHT!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """Fighting!"""
        screenshot, window_location = capture_window()

        if find(vio.auto_repeat_ended, screenshot, threshold=0.7):
            print("Finished this run! Gotta re-open the dungeon")
            time.sleep(1.0)
            press_key("esc")
            time.sleep(1.0)
            self.current_state = States.RUN_ENDED
            return
        
         # If we've finished a fight in the auto-repeat, count it
        now = time.monotonic()
        if now >= BossBattleFarmer.finished_run_lockout_until and find(vio.finished_auto_repeat_fight, screenshot):
            BossBattleFarmer.num_runs_complete += 1
            BossBattleFarmer.finished_run_lockout_until = now + 5.0
            print(f"We've completed {BossBattleFarmer.num_runs_complete} runs so far and used {IFarmer.stamina_pots} stamina pots")

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location, threshold=0.8):
            IFarmer.stamina_pots += 1
            return

        find_and_click(vio.startbutton, screenshot, window_location)

    def run_ended_state(self):
        """We finished a run! Gotta re-open the dungeon, by ESC-ing until we're back into the dungeon"""
        screenshot, window_location = capture_window()

        if find(vio.boss_battle_loading_screen, screenshot):
            self.current_state = States.GOING_TO_FLOOR_STATE
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return
        else:
            press_key("esc")

    def check_for_esette_popup(self):
        """Check if we have the Essette shop, and click on it if so to remove the popup"""
        screenshot, window_location = capture_window()
        find_and_click(vio.essette_shop, screenshot, window_location)

    def run(self):

        print("Farming Boss Battles!")

        while True:

            check_for_reconnect()
            self.check_for_esette_popup()

            if self.current_state == States.GOING_TO_DUNGEON:
                self.going_to_dungeon_state()

            elif self.current_state == States.OPENING_DUNGEON:
                self.opening_dungeon_state()

            elif self.current_state == States.GOING_TO_FLOOR_STATE:
                self.going_to_floor_state()

            elif self.current_state == States.GET_READY:
                self.get_ready_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == States.RUN_ENDED:
                self.run_ended_state()

            time.sleep(0.5)
