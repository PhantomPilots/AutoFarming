import time

import numpy as np
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import (
    capture_window,
    count_empty_card_slots,
    find,
    find_and_click,
)


class BirdFighter(IFighter):

    def fighting_state(self):

        screenshot, window_location = capture_window()

        # In case we've been lazy and it's the first time we're doing Demonic Beast this week...
        find_and_click(
            vio.weekly_mission,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("lazy_weekly_bird_mission"),
        )
        # To skip quickly to the rewards when the fight is done
        find_and_click(vio.creature_destroyed, screenshot, window_location)

        if find(vio.finished_fight_ok, screenshot):
            # Fight is complete
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif (available_card_slots := count_empty_card_slots(screenshot)) > 0:
            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

        elif find(vio.defeat, screenshot):
            # I may have lost though...
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.ok_bird_defeat, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            # We're going back to the main bird menu, let's end this thread
            self.complete_callback(victory=False)
            IFighter.exit_thread = True

    def _identify_phase(self, screenshot: np.ndarray):
        """Read the screenshot and identify the phase we're currently in"""
        if find(vio.phase_4, screenshot):
            # Phase 4 first, because it can be misread as a 1
            return 4
        elif find(vio.phase_2, screenshot):
            return 2
        elif find(vio.phase_3, screenshot):
            return 3

        # Default to phase 1 in case we don't see anything
        return 1

    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked. Overrides the parent method."""
        screenshot, window_location = capture_window()

        # 'pick_cards' will take a screenshot and extract the required features specific to that fighting strategy
        if self.current_hand is None:
            current_phase = self._identify_phase(screenshot)
            self.current_hand = self.battle_strategy.pick_cards(phase=current_phase)

        # We have the cards now, click on them
        self.play_cards(self.current_hand, screenshot, window_location)

        if not find(vio.empty_card_slot, screenshot):
            print("Finished my turn, going back to FIGHTING")
            self.current_state = FightingStates.FIGHTING
            # Reset the hand
            self.current_hand = None

    def fight_complete_state(self):

        screenshot, window_location = capture_window()

        # Click on the OK button to end the fight
        find_and_click(vio.finished_fight_ok, screenshot, window_location)

        # Only consider the fight complete if we see the loading screen, in case we need to click OK multiple times
        if find(vio.db_loading_screen, screenshot):
            self.complete_callback(victory=True)
            IFighter.exit_thread = True

    @IFighter.run_wrapper
    def run(self):

        print("Fighting very hard...")

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.FIGHTING_COMPLETE:
                self.fight_complete_state()

            elif self.current_state == FightingStates.DEFEAT:
                self.defeat_state()

            if IFighter.exit_thread:
                print("Closing Fighter thread!")
                return

            time.sleep(0.7)
