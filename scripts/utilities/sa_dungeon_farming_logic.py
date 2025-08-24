import time
from enum import Enum, auto

import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    drag_im,
    find,
    find_and_click,
    press_key,
)


class States(Enum):
    GOING_TO_DUNGEON = auto()
    OPENING_DUNGEON = auto()
    GOING_TO_FLOOR_STATE = auto()
    GET_READY = auto()
    FIGHTING = auto()
    RESTART_FIGHT = auto()
    RUN_ENDED = auto()


class SADungeonFarmer(IFarmer):
    """SA dungeon farmer"""

    MAX_RESETS = 3

    num_resets = 0

    def __init__(self, starting_state=States.GOING_TO_DUNGEON, battle_strategy=None, max_resets=10, **kwargs):
        self.current_state = starting_state

        SADungeonFarmer.MAX_RESETS = max_resets

        print(f"We'll restart the fight at most {SADungeonFarmer.MAX_RESETS} times.")

    def going_to_dungeon_state(self):
        """Let's go to the dungeon"""
        screenshot, window_location = capture_window()

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            time.sleep(1)
            screenshot, window_location = capture_window()
            # Tower opened, let's click on it
            find_and_click(vio.clock_tower, screenshot, window_location)
            self.current_state = States.GOING_TO_FLOOR_STATE
            return

        # Click on battle menu
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)
        # Click on FS dungeon
        find_and_click(vio.fs_dungeon, screenshot, window_location)
        # Click on FS Special
        find_and_click(vio.fort_solgress_special, screenshot, window_location)
        # Clock Tower
        if find(vio.clock_tower, screenshot):
            print("Let's go to the floor...")
            self.current_state = States.OPENING_DUNGEON

    def opening_dungeon_state(self):
        screenshot, window_location = capture_window()

        if find(vio.clock_tower_floor, screenshot):
            self.current_state = States.GOING_TO_FLOOR_STATE
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            # We're re-opening the floor!
            print("Opening the floor, let's reset the 'reset count'")
            SADungeonFarmer.num_resets = 0
            return

        if not find(vio.sa_coin, screenshot) and find(vio.back, screenshot):
            # Let's drag up
            drag_im(
                Coordinates.get_coordinates("start_drag_sa"),
                Coordinates.get_coordinates("end_drag_sa"),
                window_location,
                drag_duration=0.2,
            )
            return

        find_and_click(vio.clock_tower, screenshot, window_location)

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

        find_and_click(vio.startbutton, screenshot, window_location)

        if (
            find(vio.sa_boss, screenshot, threshold=0.6)
            and SADungeonFarmer.num_resets < SADungeonFarmer.MAX_RESETS
            and not find(vio.chest, screenshot)
        ):
            self.current_state = States.RESTART_FIGHT
            SADungeonFarmer.num_resets += 1
            print(
                f"We don't see a chest, restarting the fight...\n"
                f"We'll restart at most {SADungeonFarmer.MAX_RESETS-SADungeonFarmer.num_resets} more times"
            )
            time.sleep(1)
            return

    def restart_fight_state(self):
        """We gotta restart, because of no chest..."""
        screenshot, window_location = capture_window()

        if find(vio.tavern_loading_screen, screenshot):
            self.current_state = States.OPENING_DUNGEON
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return
        if find_and_click(vio.forfeit, screenshot, window_location):
            return

        press_key("esc")

    def run_ended_state(self):
        """We finished a run! Gotta re-open the dungeon, by ESC-ing until we're back into the dungeon"""
        screenshot, _ = capture_window()

        if find(vio.back, screenshot) or find(vio.clock_tower, screenshot):
            self.current_state = States.GOING_TO_DUNGEON
            print(f"Going to {self.current_state}")
            return

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
