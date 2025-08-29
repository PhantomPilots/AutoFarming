import time
from enum import Enum, auto

import numpy as np
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper, logging
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    drag_im,
    find,
    find_and_click,
    press_key,
)

logger = LoggerWrapper("sa_dungeon_logger", level=logging.INFO, log_to_file=False)


class States(Enum):
    GOING_TO_DUNGEON = auto()
    OPENING_DUNGEON = auto()
    GOING_TO_FLOOR_STATE = auto()
    GET_READY = auto()
    FIGHTING = auto()
    RESTART_FIGHT = auto()
    RUN_ENDED = auto()


class Scrolling(Enum):
    DOWN = auto()
    UP = auto()


class SADungeonFarmer(IFarmer):
    """SA dungeon farmer"""

    # How many max resets in total
    MAX_RESETS = 3

    # How many resets so far
    num_resets = 0

    # start time since opening the dungeon
    start_dungeon_time = None

    # To count how much time between runs
    start_reset_time = None

    # Longest time for a reset
    max_time_for_reset = 0

    def __init__(self, starting_state=States.GOING_TO_DUNGEON, battle_strategy=None, max_resets=10, **kwargs):
        self.current_state = starting_state

        SADungeonFarmer.MAX_RESETS = max_resets

        print(f"We'll restart the fight at most {SADungeonFarmer.MAX_RESETS} times.")

    def going_to_dungeon_state(self):
        """Let's go to the dungeon"""
        screenshot, window_location = capture_window()

        # Click on battle menu
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)
        # Click on FS dungeon
        find_and_click(vio.fs_dungeon, screenshot, window_location)
        # Click on FS Special
        find_and_click(vio.fort_solgress_special, screenshot, window_location)
        # Clock Tower
        if find(vio.sa_coin, screenshot) or find(vio.clock_tower, screenshot) or find(vio.fs_dungeon_lock, screenshot):
            self.current_state = States.OPENING_DUNGEON
            print(f"Going to {self.current_state}")

    def opening_dungeon_state(self):
        screenshot, window_location = capture_window()

        if find(vio.clock_tower_floor, screenshot):
            self.current_state = States.GOING_TO_FLOOR_STATE
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            # We're re-opening the floor!
            print("Opening the floor, let's reset the 'reset count' and start a timer")
            SADungeonFarmer.num_resets = 0
            SADungeonFarmer.start_dungeon_time = time.time()  # We'll have 30 mins!
            return

        if not find(vio.sa_coin, screenshot) and find(vio.back, screenshot):
            # Let's drag, up or down?
            direction = Scrolling.DOWN if find(vio.fs_event_dungeon, screenshot) else Scrolling.UP

            # If we find a "lock", let's scroll from that position
            rectangle = vio.fs_dungeon_lock.find(screenshot)
            if direction == Scrolling.DOWN:
                drag_im(
                    rectangle[:2] if len(rectangle) else Coordinates.get_coordinates("start_drag_sa"),
                    (
                        (rectangle[0], rectangle[1] - 150)
                        if len(rectangle)
                        else Coordinates.get_coordinates("end_drag_sa")
                    ),
                    window_location,
                )
            elif direction == Scrolling.UP:
                drag_im(
                    rectangle[:2] if len(rectangle) else Coordinates.get_coordinates("end_drag_sa"),
                    (
                        (rectangle[0], rectangle[1] + 150)
                        if len(rectangle)
                        else Coordinates.get_coordinates("start_drag_sa")
                    ),
                    window_location,
                )

            return

        if find(vio.sa_coin, screenshot):
            # Let's try to access/open the tower
            rectangle = vio.sa_coin.find(screenshot)
            find_and_click(
                vio.sa_coin,
                screenshot,
                window_location,
                point_coordinates=(Coordinates.get_coordinates("center_screen")[0], rectangle[1] + rectangle[-1] / 2),
            )

    def going_to_floor_state(self):
        """Dungeon is open, let's go to the floor"""
        screenshot, window_location = capture_window()

        if find(vio.startbutton, screenshot):
            # Let's go to proceed to battle!
            self.current_state = States.GET_READY
            print(f"Going to {self.current_state}")
            return

        if find(vio.clock_tower_floor, screenshot):
            rectangle = vio.clock_tower_floor.find(screenshot)
            find_and_click(
                vio.clock_tower_floor,
                screenshot,
                window_location,
                point_coordinates=(Coordinates.get_coordinates("center_screen")[0], rectangle[1] + rectangle[-1] / 2),
            )

    def get_ready_state(self):
        """Prepare the fight and go!"""
        screenshot, window_location = capture_window()

        find_and_click(vio.auto_repeat_off, screenshot, window_location)

        # Let's fight!
        if find(vio.startbutton, screenshot):
            print("LET'S FIGHT!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """Fighting!"""
        screenshot, window_location = capture_window()

        if find(vio.auto_repeat_ended, screenshot):
            print("Finished this run! Gotta re-open the dungeon")
            self.current_state = States.RUN_ENDED
            return

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location, threshold=0.8):
            IFarmer.stamina_pots += 1
            return

        if find_and_click(vio.startbutton, screenshot, window_location):
            # If we come from a reset, let's log how much time has passed
            if (
                SADungeonFarmer.start_reset_time is not None
                and time.time() - SADungeonFarmer.start_reset_time > SADungeonFarmer.max_time_for_reset
            ):
                SADungeonFarmer.max_time_for_reset = time.time() - SADungeonFarmer.start_reset_time
            print(f"Current max reset time found: {SADungeonFarmer.max_time_for_reset:.2f}")
            SADungeonFarmer.start_reset_time = None

            # TODO: REMOVE
            if SADungeonFarmer.start_dungeon_time is None:
                SADungeonFarmer.start_dungeon_time = time.time()

        if find(vio.sa_boss, screenshot, threshold=0.6) and not find(vio.chest, screenshot, threshold=0.6):
            # Let's decide if we use a timer or if we use max resets
            print("We don't see a chest, can we restart the fight?")

            if SADungeonFarmer.max_time_for_reset > 0 and SADungeonFarmer.start_dungeon_time is not None:
                # Let's compute if we can reset...
                remaining_time = (30 * 60 + SADungeonFarmer.start_dungeon_time) - (
                    time.time() + SADungeonFarmer.max_time_for_reset + 5  # Adding 5 seconds of buffer
                )
                if remaining_time > 0:
                    # We can restart!
                    print(f"We have {remaining_time/60:.2f} mins left. Enough time to restart the fight once more!")
                    self.lets_restart_fight(screenshot)

            # If we cannot use a timer
            elif (
                SADungeonFarmer.max_time_for_reset == 0 or SADungeonFarmer.start_dungeon_time is None
            ) and SADungeonFarmer.num_resets < SADungeonFarmer.MAX_RESETS:
                self.lets_restart_fight(screenshot)

    def lets_restart_fight(self, screenshot: np.ndarray):
        """Common logic to restart the fight"""
        self.current_state = States.RESTART_FIGHT
        # Let's log the image for later inspection
        logger.save_image(screenshot, subdir="sa_images")

        # Increase the reset count regardless
        SADungeonFarmer.num_resets += 1
        print(f"We've restarted the fight {SADungeonFarmer.num_resets} times")

    def restart_fight_state(self):
        """We gotta restart, because of no chest..."""
        screenshot, window_location = capture_window()

        if find(vio.tavern_loading_screen, screenshot):
            self.current_state = States.OPENING_DUNGEON
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return
        if find_and_click(vio.forfeit, screenshot, window_location):
            return

        press_key("esc")
        # Let's start the smaller timer that will count how long a reset takes
        SADungeonFarmer.start_reset_time = time.time()

    def run_ended_state(self):
        """We finished a run! Gotta re-open the dungeon, by ESC-ing until we're back into the dungeon"""
        screenshot, _ = capture_window()

        if find(vio.back, screenshot) or find(vio.sa_coin, screenshot):
            self.current_state = States.GOING_TO_DUNGEON
            print(f"Going to {self.current_state}")
            return

        if not find(vio.fs_loading_screen, screenshot):
            press_key("esc")

    def check_for_esette_popup(self):
        """Check if we have the Essette shop, and click on it if so to remove the popup"""
        screenshot, window_location = capture_window()
        find_and_click(vio.essette_shop, screenshot, window_location)

    def run(self):

        print("Farming SA coin dungeon!")

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

            elif self.current_state == States.RESTART_FIGHT:
                self.restart_fight_state()

            elif self.current_state == States.RUN_ENDED:
                self.run_ended_state()

            time.sleep(0.5)
