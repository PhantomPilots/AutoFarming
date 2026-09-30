import time
from typing import Callable

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.supreme_deity_fighting_strategies import SupremeDeityBattleStrategy
from utilities.utilities import (
    capture_window,
    click_im,
    find,
    find_and_click,
)

# Turns (phase, turn) on which we use the Odin talent (Omnipotence). Its cooldown is 3 turns, and these turns are far
# enough apart as long as the Judgments don't die faster than in the video
TALENT_TURNS = {(1, 1), (4, 1), (5, 1), (6, 2)}
# The Stigmata of Weakening finishes the Third Judgment. Against the final boss, we try again on every turn from the
# 2nd one, in case the gauge filled up
STIGMATA_TURNS = {(3, 2)}
STIGMATA_FINAL_BOSS_FIRST_TURN = 2
# The icon of an available Stigmata scores ~0.8, a locked one ~0.6
STIGMATA_THRESHOLD = 0.7

# Banners shown when a phase starts. "X Judgment" only stays ~0.6s, "New Supreme Deity's Messengers have been sent."
# ~2.5s after it, and the VS screen before the Forces of Protection and the final boss ~4s
JUDGMENT_BANNERS = (
    (vio.sd_banner_first, 1),
    (vio.sd_banner_second, 2),
    (vio.sd_banner_third, 3),
    (vio.sd_banner_fourth, 4),
)
BANNER_THRESHOLD = 0.85
# "ENEMY TURN" fades in and out, it scores 0.62 to 1.0 during the enemy turns and never above 0.6 elsewhere
ENEMY_TURN_THRESHOLD = 0.75
# A turn only starts once a banner was seen since our last turn (a phase banner at the start of the fight, then
# "ENEMY TURN" or a phase banner), and this long after it left the screen. While our cards are being played, the slots
# empty one by one and look like a new turn
BANNER_SETTLE_SECONDS = 3
# If no banner was seen (e.g. the bot was started in the middle of a fight), we stop waiting after this long
NO_BANNER_TIMEOUT_SECONDS = 60
# During the cutscenes and the card animations the hand is hidden: a real turn shows the cards of the hand
MIN_KNOWN_CARDS_FOR_TURN = 5

# The 4 card slots. An empty slot is dark and see-through, a filled one shows a card or the move icon.
# The 4th slot is tinted blue, that's why the generic empty slot templates miss it.
CARD_SLOT_CENTERS = ((175, 745), (240, 745), (305, 745), (370, 745))
CARD_SLOT_HALF_SIZE = (20, 35)  # half width, half height
EMPTY_SLOT_MAX_BRIGHTNESS = 100
EMPTY_SLOT_MAX_BRIGHT_PIXELS = 0.02


class SupremeDeityFighter(IFighter):
    """Supreme Deity Battle fighter, for the 6 phases: the 4 Judgments (waves of messengers), the Heavenly Punishment
    Forces of Protection, then the final boss. The phases are read on the banners shown between them, and the final
    boss on the frame of its portrait.
    """

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None, stigmata_mode="auto"):
        # "auto": Stigmata of Weakening on the Third Judgment and the final boss. "never": no Stigmata at all
        self.stigmata_mode = stigmata_mode
        self._fight_start_time = time.time()
        # Last time a banner was on screen, None until the first one
        self._last_banner_time: float | None = None
        self._last_turn_end_time: float | None = None
        super().__init__(battle_strategy=battle_strategy, callback=callback)

    def prepare_for_new_fight(self):
        super().prepare_for_new_fight()
        self._fight_start_time = time.time()
        self._last_banner_time = None
        self._last_turn_end_time = None

    def finish_turn(self):
        self._last_turn_end_time = time.time()
        return super().finish_turn()

    def _reset_instance_variables(self):
        super()._reset_instance_variables()
        # The talent and the Stigmata are handled once, at the start of each turn
        self.turn_start_done = False

    def _before_pick_cards(self, *, screenshot, window_location, empty_card_slots: int) -> None:
        # The strategy reads the cards of the hand on this screenshot
        if isinstance(self.battle_strategy, SupremeDeityBattleStrategy):
            self.battle_strategy.screenshot = screenshot

    def fighting_state(self):
        screenshot, window_location = capture_window()

        # Cutscenes between phases
        find_and_click(vio.skip, screenshot, window_location, threshold=0.7)

        self._watch_phase_banners(screenshot)

        if find(vio.defeat, screenshot) or find(vio.failed, screenshot):
            print("We lost the Supreme Deity fight :(")
            self.current_state = FightingStates.DEFEAT

        elif find(vio.ok_main_button, screenshot):
            print("Supreme Deity fight complete!")
            self.current_state = FightingStates.FIGHTING_COMPLETE

        elif (
            available_card_slots := SupremeDeityFighter.count_empty_card_slots(screenshot)
        ) > 0 and self._is_real_turn(screenshot):
            # We see empty card slots and the hand, it means its our turn
            self.available_card_slots = available_card_slots
            print(f"MY TURN, selecting {available_card_slots} cards...")
            self.current_state = FightingStates.MY_TURN

            if find(vio.sd_final_boss, screenshot, threshold=0.8):
                self._apply_detected_phase(6)

    def _is_real_turn(self, screenshot: np.ndarray) -> bool:
        """Wait for a banner since our last turn and the end of its animation, and for the cards of the hand"""
        now = time.time()
        waiting_since = self._last_turn_end_time or self._fight_start_time
        if self._last_banner_time is None or self._last_banner_time < waiting_since:
            if now - waiting_since < NO_BANNER_TIMEOUT_SECONDS:
                return False
        elif now - self._last_banner_time < BANNER_SETTLE_SECONDS:
            return False

        return SupremeDeityBattleStrategy.count_known_cards(screenshot) >= MIN_KNOWN_CARDS_FOR_TURN

    def _watch_phase_banners(self, screenshot: np.ndarray):
        """Read the phase on the banners shown between the phases"""
        if find(vio.sd_enemy_turn, screenshot, threshold=ENEMY_TURN_THRESHOLD):
            self._last_banner_time = time.time()

        for banner, phase in JUDGMENT_BANNERS:
            if find(banner, screenshot, threshold=BANNER_THRESHOLD):
                print(f"Banner of phase {phase}!")
                self._last_banner_time = time.time()
                self._apply_detected_phase(phase)
                return

        new_messengers = find(vio.sd_new_messengers, screenshot, threshold=BANNER_THRESHOLD)
        vs_screen = not new_messengers and find(vio.sd_vs, screenshot, threshold=BANNER_THRESHOLD)
        if not new_messengers and not vs_screen:
            return
        self._last_banner_time = time.time()

        # These banners stay on screen for several seconds, and the ordinal banner may have been missed. They only
        # count once per phase: after a phase change, no turn has started yet in the new phase
        if IBattleStrategy.phase_turn == 0:
            return

        if new_messengers and IFighter.current_phase < 4:
            print("New messengers: next phase!")
            self._apply_detected_phase(IFighter.current_phase + 1)

        elif vs_screen:
            # The first VS screen comes before the Forces of Protection, the second one before the final boss
            print("VS screen: next phase!")
            self._apply_detected_phase(max(5, IFighter.current_phase + 1) if IFighter.current_phase < 6 else 6)

    def my_turn_state(self):
        """Use the talent and the Stigmata first, then play the cards"""
        # A phase banner means the turn is over (e.g. our cards killed the wave)
        screenshot, _ = capture_window()
        self._watch_phase_banners(screenshot)

        if not self.turn_start_done:
            self._start_phase_turn_if_needed()
            self._turn_start_actions(IFighter.current_phase, IBattleStrategy.phase_turn)
            self.turn_start_done = True

        self.play_cards()

    def _turn_start_actions(self, phase: int, turn: int):
        print(f"Supreme Deity: phase {phase}, turn {turn}")

        if (phase, turn) in TALENT_TURNS:
            self._use_odin_talent()

        if self.stigmata_mode != "never" and (
            (phase, turn) in STIGMATA_TURNS or (phase == 6 and turn >= STIGMATA_FINAL_BOSS_FIRST_TURN)
        ):
            self._use_stigmata(vio.sd_stigmata_menu_weakening, "Weakening")

    def _use_odin_talent(self):
        screenshot, window_location = capture_window()
        if find_and_click(vio.sd_talent_odin, screenshot, window_location, threshold=0.7, sleep_time=2.5):
            print("Used the Odin talent!")
        else:
            print("[WARN] Couldn't find the Odin talent.")

    def _use_stigmata(self, stigmata_vision, name: str) -> bool:
        """Open the Stigmata menu, and use the given Stigmata if it's available. The menu closes by itself"""
        screenshot, window_location = capture_window()
        click_im(Coordinates.get_coordinates("sd_stigmata_button"), window_location)
        time.sleep(1)

        screenshot, window_location = capture_window()
        if not find(vio.sd_stigmata_menu_close, screenshot, threshold=0.8):
            print(f"[WARN] The Stigmata menu didn't open, can't use the Stigmata of {name}.")
            return False

        # The icon only matches when the Stigmata is available (it's greyed out with a lock otherwise)
        if find_and_click(stigmata_vision, screenshot, window_location, threshold=STIGMATA_THRESHOLD, sleep_time=2):
            screenshot, window_location = capture_window()
            if not find(vio.sd_stigmata_menu_close, screenshot, threshold=0.8):
                print(f"Used the Stigmata of {name}!")
                return True
            # "Cannot use Stigmata skill.": the menu stays open
            print(f"The game refused the Stigmata of {name}.")
        else:
            print(f"The Stigmata of {name} isn't available.")

        find_and_click(vio.sd_stigmata_menu_close, screenshot, window_location, threshold=0.8, sleep_time=1)
        return False

    def fight_complete_state(self):
        screenshot, window_location = capture_window()

        # Click on OK until we leave the rewards screen
        if find_and_click(vio.ok_main_button, screenshot, window_location, sleep_time=1):
            return

        self.complete_callback(victory=True)
        self.exit_thread = True

    def defeat_state(self):
        screenshot, window_location = capture_window()

        if find_and_click(vio.ok_main_button, screenshot, window_location, sleep_time=1):
            return

        if find(vio.defeat, screenshot) or find(vio.failed, screenshot):
            # Still on the defeat screen, tap to continue
            find_and_click(vio.defeat, screenshot, window_location)
            find_and_click(vio.failed, screenshot, window_location)
            return

        self.complete_callback(victory=False)
        self.exit_thread = True

    @staticmethod
    def count_empty_card_slots(screenshot, **kwargs):
        """Count how many of the 4 card slots are empty. Outside of our turn, there are no slots at all"""
        half_width, half_height = CARD_SLOT_HALF_SIZE
        empty_slots = 0
        for x, y in CARD_SLOT_CENTERS:
            slot = screenshot[y - half_height : y + half_height, x - half_width : x + half_width]
            brightness = cv2.cvtColor(slot, cv2.COLOR_BGR2HSV)[..., 2]
            if brightness.mean() < EMPTY_SLOT_MAX_BRIGHTNESS and (brightness > 200).mean() < EMPTY_SLOT_MAX_BRIGHT_PIXELS:
                empty_slots += 1
        return empty_slots

    @IFighter.run_wrapper
    def run(self):

        print("Fighting the Supreme Deity...")

        while True:

            if self.current_state == FightingStates.FIGHTING:
                self.fighting_state()

            elif self.current_state == FightingStates.MY_TURN:
                self.my_turn_state()

            elif self.current_state == FightingStates.FIGHTING_COMPLETE:
                self.fight_complete_state()

            elif self.current_state == FightingStates.DEFEAT:
                self.defeat_state()

            if self.exit_thread:
                print("Closing the Supreme Deity fighting thread!")
                return

            time.sleep(0.5)
