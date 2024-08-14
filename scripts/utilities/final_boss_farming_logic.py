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


class FinalBossFarmer(IFarmer):

    def __init__(self, battle_strategy: IBattleStrategy = None, starting_state=States.GOING_TO_FB, **kwargs):

        # Initialize the current state
        self.current_state = starting_state

        # TODO: Unused, bad coding
        self.bird_fighter = battle_strategy

        # Keep track of how many fights have been done
        self.num_fights = 0

        # Decide whether hell or challenge difficulty
        self.difficulty = kwargs["difficulty"]

    def exit_message(self):
        print(f"We beat the Final Boss {self.num_fights} times.")

    def going_to_fb_state(self):
        """This should be the original state. Let's go to the bird menu"""
        screenshot, window_location = capture_window()

        # If we're back in the tavern, click on the battle menu.
        # TODO: Remove the hardcoded coordinates, or at least make them dynamic with respect to the window size
        find_and_click(
            vio.main_menu,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("battle_menu"),
            threshold=0.7,
        )

        # If we're in the battle menu, click on Final Boss
        find_and_click(vio.final_boss_menu, screenshot, window_location, threshold=0.8)

        if find(vio.hell_difficulty, screenshot):
            # We're in the final boss menu, move to the next state
            self.current_state = States.IN_FINAL_BOSS_MENU

    def in_final_boss_menu_state(self):
        """Click on challenge or hell based on difficulty option"""
        screenshot, window_location = capture_window()

        # We may see an OK button, if we come from a defeat screen
        find_and_click(vio.ok_bird_defeat, screenshot, window_location)

        # After clicking, if we're on start, move to the battle!
        if find(vio.startbutton, screenshot):
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
        if find_and_click(vio.fb_ok_button, screenshot, window_location):
            return

        # We may need to restore stamina
        find_and_click(vio.restore_stamina, screenshot, window_location)

        # Click on START to begin the fight
        find_and_click(vio.startbutton, screenshot, window_location)

        # If we see a SKIP button
        if find(vio.skip_bird, screenshot, threshold=0.7):
            # Go to fight!
            self.current_state = States.FIGHTING
            return

    def fighting_state(self):

        screenshot, window_location = capture_window()

        # If we've ended the fight...
        find_and_click(vio.boss_destroyed, screenshot, window_location, threshold=0.6)
        find_and_click(vio.episode_clear, screenshot, window_location)
        find_and_click(vio.boss_results, screenshot, window_location)
        find_and_click(
            vio.showdown, screenshot, window_location, point_coordinates=Coordinates.get_coordinates("showdown")
        )
        if find_and_click(vio.boss_mission, screenshot, window_location):
            self.num_fights += 1
            print(f"FB cleared! {self.num_fights} times so far.")

        # We may need to restore stamina
        find_and_click(vio.restore_stamina, screenshot, window_location)

        # Click 'again'
        find_and_click(vio.again, screenshot, window_location)

        # Skip to the fight
        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.7)

        # Ensure AUTO is on
        find_and_click(vio.auto_off, screenshot, window_location, threshold=0.9)

        if find(vio.ok_bird_defeat, screenshot):
            print("Oh no, we have lost :( Retrying")
            self.current_state = States.IN_FINAL_BOSS_MENU

    def run(self):

        print(f"Farming {self.difficulty} Final Boss.")

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

            time.sleep(0.8)
