import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_im,
    find,
    find_and_click,
    find_rect,
)


class States(Enum):
    GOING_TO_LB = 0
    IN_LEGENDARY_BOSS_MENU = 1
    READY_TO_FIGHT = 2
    FIGHTING = 3
    EXIT_FARMER = 4


class LegendaryBossFarmer(IFarmer):

    # Keep track of how many fights have been done
    num_fights = 0

    def __init__(self, battle_strategy: IBattleStrategy = None, starting_state=States.GOING_TO_LB, **kwargs):
        super().__init__()

        # Initialize the current state
        self.current_state = starting_state

        # TODO: Unused, bad coding
        self.fighter = battle_strategy

        # Decide whether hell or challenge difficulty
        self.difficulty = kwargs["difficulty"]

        # In case we have a limited amount of runs we want to make
        self.max_num_runs = float(kwargs.get("num_runs", "inf"))
        if self.max_num_runs < float("inf"):
            print(f"We're gonna farm the Legendary Boss {int(self.max_num_runs)} times.")

    def exit_message(self):
        super().exit_message()
        print(f"We beat the Legendary Boss {LegendaryBossFarmer.num_fights} times.")

    def going_to_lb_state(self):
        """This should be the original state. Let's go to the bird menu"""
        screenshot, window_location = capture_window()

        # Click on the battle menu if we see it
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # If we're in the battle menu, click on Legendary Boss
        find_and_click(vio.legendary_boss_menu, screenshot, window_location, threshold=0.8)

        if find(vio.legendary_boss_roxy, screenshot):
            # We're in the legendary boss menu, move to the next state
            print("Moving to IN_LEGENDARY_BOSS_MENU")
            self.current_state = States.IN_LEGENDARY_BOSS_MENU

    def in_legendary_boss_menu_state(self):
        """Click on challenge or hell based on difficulty option"""
        screenshot, window_location = capture_window()

        # We may see an OK button, if we come from a defeat screen
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # After clicking, if we're on start, move to the battle!
        if find(vio.startbutton, screenshot):
            print("Moving to READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT
            return

        difficulty_rect = None
        difficulty_on_screen = None
        if (difficulty_rect := find_rect(vio.legendary_boss_extreme, screenshot)) is not None:
            difficulty_on_screen = "extreme"
        elif (difficulty_rect := find_rect(vio.legendary_boss_hell, screenshot)) is not None:
            difficulty_on_screen = "hell"
        elif (difficulty_rect := find_rect(vio.legendary_boss_challenge, screenshot)) is not None:
            difficulty_on_screen = "challenge"

        if difficulty_rect is None or difficulty_on_screen is None:
            print("Couldn't find the current difficulty on screen, retry...")
            return

        selected_difficulty = str(self.difficulty).strip().lower()
        order = ["extreme", "hell", "challenge"]
        if selected_difficulty not in order:
            print(f"Unknown difficulty '{self.difficulty}'. Default to hell.")
            selected_difficulty = "hell"

        center_x_local = screenshot.shape[1] // 2
        click_y_local = int(difficulty_rect[1]) + 50

        # Already on target: click middle
        if difficulty_on_screen == selected_difficulty:
            click_im((center_x_local, click_y_local), window_location)
            self.current_state = States.READY_TO_FIGHT
            return

        # Otherwise scroll left/right in steps of 80px
        current_idx = order.index(difficulty_on_screen)
        target_idx = order.index(selected_difficulty)
        arrow = vio.legendary_boss_right_arrow if target_idx > current_idx else vio.legendary_boss_left_arrow
        find_and_click(arrow, screenshot, window_location)

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # If we see an OK button bc of oath of combat not selected...
        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            print(f"We've used {IFarmer.stamina_pots} stamina pots so far")
            return

        # Click on the "Min." button to remove extra challenges, we don't need for farming
        find_and_click(vio.legendary_boss_min_button, screenshot, window_location, threshold=0.8)

        # Click on START to begin the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        # If we see a SKIP button
        if find(vio.skip, screenshot, threshold=0.7) or find(vio.fb_aut_off, screenshot):
            # Go to fight!
            print("Moving to FIGHTING")
            self.current_state = States.FIGHTING
            return

    def fighting_state(self):
        screenshot, window_location = capture_window()

        # If we've ended the fight...
        find_and_click(vio.legendary_boss_final_score, screenshot, window_location, threshold=0.7)
        find_and_click(vio.episode_clear, screenshot, window_location)
        find_and_click(vio.boss_mission, screenshot, window_location)

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Click 'again'
        if find(vio.again, screenshot):
            LegendaryBossFarmer.num_fights += 1
            print(f"LB cleared! {LegendaryBossFarmer.num_fights} times so far.")
            print("[CLEAR]")

            # Now, exit the fight if we've reached the desired number of runs
            if LegendaryBossFarmer.num_fights >= self.max_num_runs:
                print("Reached the desired number of runs, exiting the farmer...")
                find_and_click(vio.ok_main_button, screenshot, window_location)
                self.current_state = States.EXIT_FARMER
                return

            find_and_click(vio.again, screenshot, window_location)

        elif find(vio.failed, screenshot):
            print("Oh no, we have lost :( Retrying...")
            print("[LOSS]")
            self.current_state = States.IN_LEGENDARY_BOSS_MENU

        else:
            # Skip to the fight
            find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.6)

            # Ensure AUTO is on
            find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.8)

    def run(self):

        print(f"Farming {self.difficulty} Final Boss, starting from state {self.current_state}.")

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_LB:
                self.going_to_lb_state()

            elif self.current_state == States.IN_LEGENDARY_BOSS_MENU:
                self.in_legendary_boss_menu_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.8)
