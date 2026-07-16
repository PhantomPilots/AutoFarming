import time

import utilities.vision_images as vio
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import capture_window, find, get_card_slot_region_image


class GuildBossFighter(IFighter):
    """Shared manual card-playing state machine for two-phase Guild Boss battles."""

    def fighting_state(self):
        screenshot, _ = capture_window()

        if find(vio.ok_main_button, screenshot):
            self.current_state = FightingStates.EXIT_FIGHT
        elif (available_card_slots := self.count_empty_card_slots(screenshot)) > 0:
            self.available_card_slots = available_card_slots
            self._apply_detected_phase(self._identify_phase(screenshot))
            self.current_state = FightingStates.MY_TURN

    def my_turn_state(self):
        self.play_cards()

    def _identify_phase(self, screenshot):
        return 2 if find(vio.phase_2, screenshot, threshold=0.8) else None

    @staticmethod
    def count_empty_card_slots(screenshot, threshold=0.6):
        card_slots_image = get_card_slot_region_image(screenshot)
        rectangles, _ = vio.empty_card_slot.find_all_rectangles(card_slots_image, threshold=threshold)
        alternate_rectangles, _ = vio.empty_card_slot_2.find_all_rectangles(screenshot, threshold=0.7)
        rectangles = alternate_rectangles if alternate_rectangles.size else rectangles
        return 4 if find(vio.skill_locked, screenshot, threshold=0.6) else len(rectangles)

    def exit_fight_state(self):
        with self._lock:
            self.exit_thread = True

    @IFighter.run_wrapper
    def run(self):
        print("Fighting Guild Boss...")

        while True:
            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()
            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()
            elif self.current_state == FightingStates.EXIT_FIGHT:
                self.exit_fight_state()

            if self.exit_thread:
                print("Closing Guild Boss fighter thread!")
                return

            time.sleep(0.5)
