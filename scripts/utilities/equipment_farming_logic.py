from enum import Enum
from time import sleep

import pyautogui as pyautogui
import utilities.vision_images as vio

# Import all images
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_im,
    find,
    find_and_click,
    press_key,
)


class States(Enum):
    FARMING = 0
    TAVERN_TO_SALVAGE = 1
    TAVERN_TO_FARM = 2
    SALVAGING = 3
    SALVAGING_DONE = 4
    GOING_TO_TAVERN = 5


class EquipmentFarmer(IFarmer):
    """State machine that farms equipment even when equipment is full"""

    def __init__(self, battle_strategy=None, starting_state=States.TAVERN_TO_FARM):

        # Assume the state machine starts in a hardcoded state
        self.current_state = starting_state

        # Unused, how to make the code cleaner and still abide by the interface?
        self.battle_strategy = battle_strategy

        # Keep track of how many times we've salvaged equipment
        self.num_salvages = 0

    def exit_message(self):
        """Final message!"""
        print(f"We salvaged equipment {self.num_salvages} times.")

    def farming_state(self):
        """Polling checking to see if farming has ended"""
        screenshot, window_location = capture_window()

        if find_and_click(vio.auto_repeat_ended, screenshot, window_location):
            # Farming ended!
            press_key("esc")
            self.current_state = States.GOING_TO_TAVERN
            return

        sleep(2)  # In the FARMING state we can have a much lower frequency polling

    def going_to_tavern(self):
        screenshot, window_location = capture_window()

        if find(vio.auto_repeat_ended, screenshot):
            # In case it didn't go away, press ESC again
            press_key("esc")

        find_and_click(vio.ok_button, screenshot, window_location)

        if find_and_click(vio.tavern, screenshot, window_location):
            # TODO: We should not have to capture the window twice in one state, make an additional state
            screenshot, _ = capture_window()
            if find(vio.main_menu, screenshot, threshold=0.7):
                self.current_state = States.TAVERN_TO_SALVAGE
                print("Moving to TAVERN_TO_SALVAGE")

    def tavern_to_salvage_state(self):
        """I'm in the tavern. Go salvage all the equipment!"""
        screenshot, window_location = capture_window()

        # Go to the salvage menu. TODO: NOT using `find_and_click` in this case since we're using hardcoded coordinates
        rectangle = vio.main_menu.find(screenshot, 0.7)
        if rectangle.size:
            # Click on the main menu
            click_im(rectangle, window_location)
            print("Clicked on 'main_menu'")
            sleep(1.5)
            # Click on the "salvage equipment" button
            click_im(Coordinates.get_coordinates("salvage_equipment"), window_location)
            print("Clicked on 'salvage equipment'")
            sleep(3)

        # Register all equipment
        if find_and_click(vio.register_all, screenshot, window_location):
            self.current_state = States.SALVAGING
            print("Moving to SALVAGING")

    def salvaging_state(self):  # sourcery skip: extract-duplicate-method
        """TODO: Bad quality code, we shouldn't need to get more than one screenshot for each state"""

        screenshot, window_location = capture_window()

        # Apply the registered equipment
        if find_and_click(vio.apply, screenshot, window_location):
            screenshot, window_location = capture_window()
            # TODO: We DON'T WANT 0.99 thresholds, find a better way
            if find(vio.empty_salvage, screenshot, threshold=0.99):
                # Nothing to salvage! Back to the tavern and move to the TAVERN_TO_FARM state
                self.current_state = States.SALVAGING_DONE
                print("Nothing to salvage! Moving to SALVAGING DONE")
                return

        # Salvage the equipment -- TODO: This block is not ideal, divide it into two states?
        if find_and_click(vio.salvage, screenshot, window_location):
            sleep(1.5)

            screenshot, window_location = capture_window()
            # If the high-grade equipment pop-up appears...
            find_and_click(
                vio.high_grade_equipment,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("high_grade_equipment"),
            )

        elif find(vio.salvaging_results, screenshot):
            # The salvaging is done!
            self.current_state = States.SALVAGING_DONE
            print("Moving to SALVAGING DONE")

    def salvaging_done_state(self):
        """In this state, simply keep clicking on where the OK button should be until we find the 'back' button on screen"""
        screenshot, window_location = capture_window()

        find_and_click(vio.back, screenshot, window_location)

        # Click on the OK button
        find_and_click(vio.ok_button, screenshot, window_location)

        if find(vio.main_menu, screenshot, threshold=0.7):
            # We're back in the tavern
            self.current_state = States.TAVERN_TO_FARM
            # Increment the number of salvaging done
            self.num_salvages += 1
            print("Moving to TAVERN_TO_FARM")

    def tavern_to_farm_state(self):
        """I'm back in the tavern, but after salvaging the equipment. Let's go back to farming"""

        screenshot, window_location = capture_window()

        # If we're back in the tavern, click on the battle menu
        find_and_click(
            vio.main_menu,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("battle_menu"),
            threshold=0.7,
        )

        # If we're in the battle menu, click on the equipment menu
        find_and_click(
            vio.equipment,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("equipment_menu"),
        )

        # Let's farm the attack bracelet stage (arbitrary)
        find_and_click(vio.onslaught, screenshot, window_location)

        # If we're in the free stage menu, click on the 'hard' stage
        find_and_click(
            vio.free_stage,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("free_stage_hard"),
        )

        # Ensure auto repeat is ON (it'll always be OFF by default)
        find_and_click(vio.auto_repeat_off, screenshot, window_location)

        # If auto-repeat is finally ON, start farming
        if find_and_click(
            vio.auto_repeat_on,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("start_fight"),
        ):
            self.current_state = States.FARMING
            print("FARMING hard...")

    def run(self):
        """Main state machine. Assumes it starts in the `TAVER_TO_FARM` state"""

        print(f"Farming... starting from {self.current_state}")

        while True:
            # Try to reconnect first
            check_for_reconnect()

            if self.current_state == States.TAVERN_TO_FARM:
                self.tavern_to_farm_state()

            elif self.current_state == States.FARMING:
                self.farming_state()

            elif self.current_state == States.GOING_TO_TAVERN:
                self.going_to_tavern()

            elif self.current_state == States.TAVERN_TO_SALVAGE:
                self.tavern_to_salvage_state()

            elif self.current_state == States.SALVAGING:
                self.salvaging_state()

            elif self.current_state == States.SALVAGING_DONE:
                self.salvaging_done_state()

            # Run loop at 1 Hz, except when in the farming state
            sleep(1)
