import time

import numpy as np
import utilities.vision_images as vio
from utilities.card_color_mapper import CardColorMapper
from utilities.card_data import Card, CardColors, CardTypes
from utilities.coordinates import Coordinates
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import (
    capture_window,
    find,
    find_and_click,
    get_card_slot_region_image,
    get_hand_cards,
)


class DemonKingFighter(IFighter):
    """The Indura fighter!"""

    current_team = 0

    def __init__(self, battle_strategy, callback=None):
        super().__init__(battle_strategy=battle_strategy, callback=callback)
        self.color_mapper = CardColorMapper()
        self._unit_colors: list[CardColors] = []
        self._first_turn = True

    def fighting_state(self):
        screenshot, _ = capture_window()

        if find(vio.ok_main_button, screenshot):
            self.current_state = FightingStates.EXIT_FIGHT

        elif (available_card_slots := DemonKingFighter.count_empty_card_slots(screenshot)) > 0:
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

            if (new_phase := self._identify_phase(screenshot)) != IFighter.current_phase:
                print(f"MOVING TO PHASE {new_phase}!")
                IFighter.current_phase = new_phase

            if self._first_turn and self._unit_colors:
                hand = get_hand_cards()
                self.color_mapper.calibrate(hand, self._unit_colors)
                self._first_turn = False

    @staticmethod
    def _identify_phase(screenshot: np.ndarray):
        if find(vio.phase_2, screenshot, threshold=0.8):
            return 2
        elif find(vio.phase_3, screenshot, threshold=0.8):
            return 3
        return 1

    def my_turn_state(self):
        self.play_cards(dk_team=DemonKingFighter.current_team, color_mapper=self.color_mapper)

    def exit_fight_state(self):
        screenshot, _ = capture_window()

        with self._lock:
            self.exit_thread = True
            self.battle_strategy.reset_fight_turn()

        self.complete_callback(find(vio.victory, screenshot))

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6, plot=False):
        """Count how many empty card slots are there for DEER"""

        card_slots_image = get_card_slot_region_image(screenshot)

        rectangles, _ = vio.empty_card_slot.find_all_rectangles(card_slots_image, threshold=threshold)
        rectangles_2, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.7)
        rectangles_3, _ = vio.dk_empty_slot.find_all_rectangles(screenshot, threshold=0.7)

        rectangles = rectangles_3 if rectangles_3.size else rectangles_2 if rectangles_2.size else rectangles

        return 3 if find(vio.skill_locked, screenshot, threshold=0.6) else min(3, len(rectangles))

    @IFighter.run_wrapper
    def run(self, unit_colors: list[CardColors]):

        print("[Fighter] Successfully received these unit colors: ", [utype.name for utype in unit_colors])
        self._unit_colors = unit_colors
        self._first_turn = True
        self.color_mapper.reset()

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.EXIT_FIGHT:
                self.exit_fight_state()

            if self.exit_thread:
                print("Closing DK fighter thread!")
                self.color_mapper.reset()
                return

            time.sleep(0.7)
