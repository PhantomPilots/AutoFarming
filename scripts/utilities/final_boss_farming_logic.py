import sys
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
    drag_im,
    find,
    find_and_click,
)


class States(Enum):
    GOING_TO_FB = 0
    IN_FINAL_BOSS_MENU = 1
    READY_TO_FIGHT = 2
    FIGHTING = 3
    EXIT_FARMER = 4


class FinalBossFarmer(IFarmer):

    # Keep track of how many fights have been done
    num_fights = 0

    def __init__(self, battle_strategy: IBattleStrategy = None, starting_state=States.GOING_TO_FB, **kwargs):

        # Initialize the current state
        self.current_state = starting_state

        # TODO: Unused, bad coding
        self.fighter = battle_strategy

        # Decide whether hell or challenge difficulty
        self.difficulty = kwargs["difficulty"]

        # In case we have a limited amount of runs we want to make
        self.max_num_runs = float(kwargs.get("num_runs", "inf"))
        if self.max_num_runs < float("inf"):
            print(f"We're gonna farm the Final Boss {int(self.max_num_runs)} times.")

    def exit_message(self):
        super().exit_message()
        print(f"We beat the Final Boss {FinalBossFarmer.num_fights} times.")

    def going_to_fb_state(self):
        """This should be the original state. Let's go to the bird menu"""
        screenshot, window_location = capture_window()

        # Click on the battle menu if we see it
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)

        # If we're in the battle menu, click on Final Boss
        find_and_click(vio.final_boss_menu, screenshot, window_location, threshold=0.8)

        if find(vio.hell_difficulty, screenshot):
            # We're in the final boss menu, move to the next state
            print("Moving to IN_FINAL_BOSS_MENU")
            self.current_state = States.IN_FINAL_BOSS_MENU

    def in_final_boss_menu_state(self):
        """Click on challenge or hell based on difficulty option"""
        screenshot, window_location = capture_window()

        # We may see an OK button, if we come from a defeat screen
        find_and_click(vio.ok_main_button, screenshot, window_location)

        # After clicking, if we're on start, move to the battle!
        if find(vio.startbutton, screenshot):
            print("Moving to READY_TO_FIGHT")
            self.current_state = States.READY_TO_FIGHT
            return

        # We're in final boss, based on the chosen difficulty, drag (or not)
        if self.difficulty.lower() == "hard":
            # Click on Hell
            find_and_click(vio.hard_difficulty, screenshot, window_location)
        elif self.difficulty.lower() == "extreme":
            # Click on Hell
            find_and_click(vio.extreme_difficulty, screenshot, window_location)
        elif self.difficulty.lower() == "hell":
            # Click on Hell
            find_and_click(vio.hell_difficulty, screenshot, window_location)
        elif self.difficulty.lower() == "challenge":
            # Drag!
            if not find(vio.challenge_difficulty, screenshot):
                drag_im(
                    Coordinates.get_coordinates("start_drag"),
                    Coordinates.get_coordinates("end_drag"),
                    window_location,
                    drag_duration=0.2,
                )
                # And try to find 'challenge' now
                time.sleep(0.3)
            find_and_click(vio.challenge_difficulty, screenshot, window_location, threshold=0.7)
        else:
            print("You have chosen a wrong difficulty, defaulting to 'Hell'")
            self.difficulty = "hell"

    def ready_to_fight_state(self):
        screenshot, window_location = capture_window()

        # If we see an OK button bc of oath of combat not selected...
        if not find(vio.diamond, screenshot) and find_and_click(vio.ok_main_button, screenshot, window_location):
            return

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Click on START to begin the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        # If we see a SKIP button
        if find(vio.skip_bird, screenshot, threshold=0.7) or find(vio.fb_aut_off, screenshot):
            # Go to fight!
            print("Moving to FIGHTING")
            self.current_state = States.FIGHTING
            return

    def fighting_state(self):

        screenshot, window_location = capture_window()

        # If we've ended the fight...
        find_and_click(vio.boss_destroyed, screenshot, window_location, threshold=0.6)
        find_and_click(vio.episode_clear, screenshot, window_location)
        find_and_click(vio.boss_results, screenshot, window_location)
        find_and_click(vio.boss_mission, screenshot, window_location)
        if find_and_click(
            vio.showdown, screenshot, window_location, point_coordinates=Coordinates.get_coordinates("showdown")
        ):
            FinalBossFarmer.num_fights += 1
            print(f"FB cleared! {FinalBossFarmer.num_fights} times so far.")

            # Now, exit the fight if we've reached the desired number of runs
            if FinalBossFarmer.num_fights >= self.max_num_runs:
                print("Reached the desired number of runs, exiting the farmer...")
                self.current_state = States.EXIT_FARMER
                return

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            return

        # Click 'again'
        if find_and_click(vio.again, screenshot, window_location):
            return

        # Skip to the fight
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.6)

        # Ensure AUTO is on
        find_and_click(vio.fb_aut_off, screenshot, window_location, threshold=0.9)

        if find(vio.failed, screenshot):
            print("Oh no, we have lost :( Retrying...")
            self.current_state = States.IN_FINAL_BOSS_MENU

    def run(self):

        print(f"Farming {self.difficulty} Final Boss, starting from state {self.current_state}.")

        while True:

            check_for_reconnect()

            if self.current_state == States.GOING_TO_FB:
                self.going_to_fb_state()

            elif self.current_state == States.IN_FINAL_BOSS_MENU:
                self.in_final_boss_menu_state()

            elif self.current_state == States.READY_TO_FIGHT:
                self.ready_to_fight_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == States.EXIT_FARMER:
                self.exit_farmer_state()

            time.sleep(0.8)
