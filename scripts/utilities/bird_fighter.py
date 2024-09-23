import time

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
from utilities.coordinates import Coordinates
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import capture_window, find, find_and_click, get_hand_cards


class BirdFighter(IFighter):

    phase = 1

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

        if find(vio.defeat, screenshot):
            # I may have lost though...
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT

        elif find(vio.finished_fight_ok, screenshot):
            # Fight is complete
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif (available_card_slots := BirdFighter.count_empty_card_slots(screenshot)) > 0:
            # First, identify if we are fully disabled... If so, restart the fight
            if available_card_slots >= 3 and self._check_disabled_hand():
                # We're fully disabled, we need to exit and restart the fight...
                print("Our hand is fully disabled, let's restart the fight!")
                self.current_state = FightingStates.EXIT_FIGHT
                return

            # We see empty card slots, it means its our turn
            self.available_card_slots = available_card_slots
            # Update the current phase
            if (new_phase := self._identify_phase(screenshot)) != BirdFighter.phase:
                print(f"MOVING TO PHASE {new_phase}!")
                BirdFighter.phase = new_phase

            # Finally, move to the next state
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

    def _identify_phase(self, screenshot: np.ndarray):
        """Read the screenshot and identify the phase we're currently in"""
        if find(vio.phase_4, screenshot, threshold=0.8):
            # Phase 4 first, because it can be misread as a 1
            return 4
        elif find(vio.phase_2, screenshot, threshold=0.8):
            return 2
        elif find(vio.phase_3, screenshot, threshold=0.8):
            return 3

        # Default to phase 1 in case we don't see anything
        return 1

    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked. Overrides the parent method."""
        screenshot, _ = capture_window()

        # Ensure we have the current hand
        if self.current_hand is None:
            self._update_current_hand(screenshot)

        # Attempt to play the cards
        if not self._attempt_to_play_cards():
            print("We're trying to play a GROUND card, we need to re-capture the hand...")
            self._update_current_hand(screenshot)
            return

        if not find(vio.empty_card_slot, screenshot):
            print("Finished my turn, going back to FIGHTING")
            self.current_state = FightingStates.FIGHTING
            # Reset the hand
            self.current_hand = None

    def _check_disabled_hand(self):
        """If we have a disabled hand"""
        house_of_cards = get_hand_cards()
        return np.all([card.card_type in [CardTypes.DISABLED, CardTypes.GROUND] for card in house_of_cards])

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.7):
        """Ideally used within a fight, count how many empty card slots we have available"""
        rectangles, _ = vio.empty_card_slot.find_all_rectangles(screenshot, threshold=threshold)
        # The second one is in case we cannot play ANY card. Then, the empty card slots look different
        rectangles_2, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.6)
        return rectangles.shape[0] + rectangles_2.shape[0]

    def _update_current_hand(self, screenshot):
        """Update the current hand of cards based on the phase."""
        current_phase = self._identify_phase(screenshot)
        cards_to_play = BirdFighter.count_empty_card_slots(screenshot)
        self.current_hand = self.battle_strategy.pick_cards(cards_to_play=cards_to_play, phase=current_phase)

    def _attempt_to_play_cards(self) -> bool:
        """Attempt to play the cards, returning True if successful, False otherwise."""
        try:
            self.play_cards(self.current_hand)
            return True
        except ValueError:
            return False

    def exit_fight_state(self):
        """We have to manually finish the fight because we've been fully disabled..."""
        screenshot, window_location = capture_window()

        if find(vio.forfeit_fight_ok, screenshot):
            # Move to the fight complete state
            self.current_state = FightingStates.DEFEAT
            return

        # Click on FORFEIT BATTLE
        if find_and_click(vio.forfeit, screenshot, window_location):
            return

        # Click in the 'pause' icon
        find_and_click(vio.pause, screenshot, window_location)

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.ok_bird_defeat, screenshot, window_location)
        find_and_click(vio.forfeit_fight_ok, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot) or find(vio.tavern_loading_screen, screenshot):
            # We're going back to the main bird menu, let's end this thread
            self.complete_callback(victory=False, phase=BirdFighter.phase)
            with self._lock:
                self.exit_thread = True

    def fight_complete_state(self):

        screenshot, window_location = capture_window()

        # Click on the OK button to end the fight
        find_and_click(vio.finished_fight_ok, screenshot, window_location)

        # Only consider the fight complete if we see the loading screen, in case we need to click OK multiple times
        if find(vio.db_loading_screen, screenshot):
            self.complete_callback(victory=True)
            with self._lock:
                self.exit_thread = True

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

            elif self.current_state == FightingStates.EXIT_FIGHT:
                self.exit_fight_state()

            if self.exit_thread:
                print("Closing Fighter thread!")
                return

            time.sleep(0.7)
