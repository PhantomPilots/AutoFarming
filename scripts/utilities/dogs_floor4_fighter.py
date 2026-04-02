import time
from numbers import Integral
from typing import Callable

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import capture_window, click_im, crop_image, find, find_and_click, get_hand_cards

from utilities.dogs_fighter import DogsFighter


class DogsFloor4Fighter(DogsFighter):
    """Dogs fighter variant for Floor 4.

    Keeps Dogs Floor 4 targeting explicit and local to this class.
    Phase 1 must select the RIGHT dog first and stop cleanly when phase 2 begins.
    """

    PHASE3_5PCT_LEFT_TOP_LEFT = (100, 290)
    PHASE3_5PCT_LEFT_BOTTOM_RIGHT = (190, 320)
    PHASE3_5PCT_RIGHT_TOP_LEFT = (310, 290)
    PHASE3_5PCT_RIGHT_BOTTOM_RIGHT = (380, 320)
    PHASE2_TURN2_DOGDED_TOP_LEFT = (95, 730)
    PHASE2_TURN2_DOGDED_BOTTOM_RIGHT = (460, 760)

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None):
        super().__init__(battle_strategy=battle_strategy, callback=callback)
        self.target_selected_phase = None
        self.phase1_buff_sacred_check_done = False
        self.phase1_turn2_backup_check_done = False
        self.phase1_turn1_confirmed = False
        self.phase1_turn1_wait_logged = False
        self.reset_pending = False
        self.reset_phase = None
        self.max_allowed_turns_per_phase = 6
        self.phase3_confirmed_target_side = None
        self.last_phase_start_validation = None
        self.sacred_gauges_locked_in = False
        self.last_known_thonar_gauge_count = 0
        self.turn_actions_taken = 0
        self.turn_completion_wait_logged = False
        self.awaiting_full_turn_open = False
        self.awaiting_full_turn_open_since = 0.0
        self.phase2_post_talent_mode = False
        self.phase2_post_talent_steps = []
        self.phase2_post_talent_template_names = ()
        self.phase2_post_talent_snapshot_index = None

    def fighting_state(self):

        screenshot, window_location = capture_window()

        find_and_click(
            vio.weekly_mission,
            screenshot,
            window_location,
            point_coordinates=Coordinates.get_coordinates("lazy_weekly_bird_mission"),
        )
        find_and_click(vio.daily_quest_info, screenshot, window_location)
        find_and_click(vio.creature_destroyed, screenshot, window_location)

        if find(vio.defeat, screenshot):
            print("I lost! :(")
            self.current_state = FightingStates.DEFEAT
            return

        elif find(vio.db_victory, screenshot, threshold=0.7):
            print("Fighting complete! Is it true? Double check...")
            self.current_state = FightingStates.FIGHTING_COMPLETE
            return

        phase = self._identify_current_phase(screenshot, window_location)
        if self._should_stop_before_phase(phase):
            return
        if self._should_wait_for_phase1_turn1_confirmation(phase, screenshot):
            return

        if (available_card_slots := self.count_empty_card_slots(screenshot, threshold=0.8)) > 0:
            if self.awaiting_full_turn_open and available_card_slots < 4:
                if time.time() - self.awaiting_full_turn_open_since < 2.5:
                    return
                print(
                    "Dogs Floor 4 turn-open guard timed out while waiting for 4 visible empty slots. "
                    "Proceeding with the currently visible slot count."
                )
                self.awaiting_full_turn_open = False
            self.awaiting_full_turn_open = False
            self.available_card_slots = available_card_slots
            self.current_state = FightingStates.MY_TURN

    def my_turn_state(self):
        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot, threshold=0.8)
        slot_index = max(0, self.available_card_slots - empty_card_slots)
        if slot_index == 0:
            self.turn_actions_taken = 0
            self.turn_completion_wait_logged = False
        phase = self._identify_current_phase(screenshot, window_location)
        self._handle_phase_entry(phase, window_location)
        if self._should_stop_before_phase(phase):
            return
        if self.turn_actions_taken >= 4:
            print("Dogs Floor 4 turn guard: 4 actions were already sent this turn. Finishing turn immediately.")
            self.finish_turn()
            return
        if self._should_reset_for_phase_turn_limit(phase):
            self._trigger_phase_reset(
                f"Dogs Floor 4 phase {phase} exceeded {self.max_allowed_turns_per_phase} turns. Resetting fight."
            )
            return
        hand_of_cards = None
        if slot_index == 0 and self._should_run_floor4_start_turn_validation(phase):
            hand_of_cards = get_hand_cards()
            if phase == 1:
                self._log_phase1_sacred_card_status(hand_of_cards)
            elif phase == 2:
                hand_of_cards, should_reset = self._validate_phase2_turn1_requirements(hand_of_cards)
                if should_reset:
                    self._trigger_phase_reset()
                    return

        if phase == 2 and self.phase2_post_talent_mode:
            hand_of_cards = hand_of_cards or get_hand_cards()
            post_talent_action = self._phase2_post_talent_action(hand_of_cards)
            if post_talent_action is None:
                self.finish_turn()
                return
            played_card = self._play_card(
                hand_of_cards,
                post_talent_action,
                window_location=window_location,
                screenshot=screenshot,
            )
            self.picked_cards[min(slot_index, len(self.picked_cards) - 1)] = played_card
            return

        if phase == 3 and slot_index == 0 and hasattr(self.battle_strategy, "observe_phase3_turn_start"):
            hand_of_cards = hand_of_cards or get_hand_cards()
            if self._should_reset_for_phase3_turn1_gold_gauge_setup(hand_of_cards):
                self._trigger_phase_reset(
                    "Phase 3 turn 1 setup failed: fewer than 2 gold thonar_gauge cards were found. Resetting fight."
                )
                return
            self.battle_strategy.observe_phase3_turn_start(screenshot, hand_of_cards)
            if getattr(type(self.battle_strategy), "phase3_missing_thonar_reset_pending", False):
                self._trigger_phase_reset(
                    "Phase 3 turn 3 was confirmed via escalin_talent, but no Thonar card was found. Resetting fight."
                )
                return
            if self._should_reset_for_phase3_persistent_5percent_limit(screenshot):
                self._trigger_phase_reset(
                    "Phase 3 gimmick 1 was completed, but the 5% damage limit is still visible. Resetting fight."
                )
                return

        self.play_cards(hand_of_cards=hand_of_cards)

    def _identify_current_phase(self, screenshot=None, window_location=None):
        if screenshot is None or window_location is None:
            screenshot, window_location = capture_window()

        if not self.phase1_turn1_confirmed:
            phase = 1
        elif find(vio.phase_2, screenshot, threshold=0.8):
            phase = 2
        elif find(vio.phase_3_dogs, screenshot, threshold=0.8):
            phase = 3
        else:
            phase = 1

        IFighter.current_phase = phase
        return phase

    def _should_check_phase1_post_turn1_buff_sacred_cards(self, phase: int, screenshot) -> bool:
        return False

    def _should_wait_for_phase1_turn1_confirmation(self, phase: int, screenshot) -> bool:
        if phase != 1 or self.phase1_turn1_confirmed:
            return False

        if find(vio.dogs_escalin_talent, screenshot, threshold=0.75):
            self.phase1_turn1_confirmed = True
            self.phase1_turn1_wait_logged = False
            print("Confirmed official Phase 1 Turn 1 start via escalin_talent. Card play is now unlocked.")
            return False

        if not self.phase1_turn1_wait_logged:
            print("Waiting for escalin_talent before allowing Phase 1 Turn 1 card play.")
            self.phase1_turn1_wait_logged = True
        return True

    def _should_check_phase1_turn2_backup_sacred_cards(self, phase: int, empty_card_slots: int) -> bool:
        return False

    def _should_run_floor4_start_turn_validation(self, phase: int) -> bool:
        scripted_turn = getattr(self.battle_strategy, "turn", 0)
        phase_initialized = getattr(self.battle_strategy, "_phase_initialized", set())
        phase2_not_initialized_yet = phase == 2 and "phase_2" not in phase_initialized
        validation_key = (phase, scripted_turn, phase2_not_initialized_yet)

        if validation_key == self.last_phase_start_validation:
            return False

        if phase == 1 and scripted_turn >= 1:
            print(
                "Dogs Floor 4 start-of-turn validation -> "
                f"phase=1, scripted_turn={scripted_turn + 1}, reason=ongoing phase 1 sacred-card tracking."
            )
            self.last_phase_start_validation = validation_key
            return True

        if phase == 2 and (scripted_turn == 0 or phase2_not_initialized_yet):
            reason = "first observed phase 2 entry before strategy reset" if phase2_not_initialized_yet else "phase 2 turn 1"
            print(
                "Dogs Floor 4 start-of-turn validation -> "
                f"phase=2, scripted_turn={scripted_turn + 1}, reason={reason}."
            )
            self.last_phase_start_validation = validation_key
            return True

        return False

    def _handle_phase_entry(self, phase: int, window_location):
        if self.target_selected_phase == phase:
            return

        if phase == 1:
            self._select_phase_target(phase, "light_dog", window_location)
        elif phase == 2:
            self._select_phase_target(phase, "dark_dog", window_location)
        else:
            self.target_selected_phase = phase

    def _select_phase_target(self, phase: int, coordinate_key: str, window_location):
        click_im(Coordinates.get_coordinates(coordinate_key), window_location)
        self.target_selected_phase = phase

    def _should_reset_for_missing_sacred_cards(self, hand_of_cards=None, reason: str = "phase 1 sacred-card check") -> bool:
        if hand_of_cards is None:
            hand_of_cards = get_hand_cards()

        thonar_gauge_count = self._count_thonar_gauge_cards(hand_of_cards)
        print(f"Sacred-card check for {reason} found {thonar_gauge_count} thonar_gauge card(s).")

        if thonar_gauge_count < 2:
            print(f"Sacred-card check failed for {reason}: fewer than 2 thonar_gauge cards. Resetting fight.")
            return True

        return False

    def _log_phase1_sacred_card_status(self, hand_of_cards):
        scripted_turn = getattr(self.battle_strategy, "turn", 0)
        thonar_gauge_count = self._count_thonar_gauge_cards(hand_of_cards)
        self.last_known_thonar_gauge_count = max(self.last_known_thonar_gauge_count, thonar_gauge_count)
        if thonar_gauge_count >= 2:
            self._lock_in_sacred_gauges(
                f"Phase 1 sacred-card tracking confirmed {thonar_gauge_count} thonar_gauge cards on turn {scripted_turn + 1}."
            )
        print(
            "Phase 1 sacred-card check -> "
            f"turn={scripted_turn + 1}, thonar_gauge_count={thonar_gauge_count}. "
            "Continuing to stall until Phase 2 Turn 1 unless the hand naturally reaches the desired setup."
        )

    def _validate_phase2_turn1_requirements(self, hand_of_cards):
        (
            best_hand,
            thonar_gauge_count,
            thonar_gauge_unv_count,
            has_nasi_stun,
            has_thonar_stance,
        ) = self._sample_best_phase2_turn1_hand(hand_of_cards)
        max_matching_gauges = max(thonar_gauge_count, thonar_gauge_unv_count)
        self.last_known_thonar_gauge_count = max(self.last_known_thonar_gauge_count, max_matching_gauges)
        if not self.sacred_gauges_locked_in and (
            thonar_gauge_count >= 2 or thonar_gauge_unv_count >= 2
        ):
            gauge_mode = "normal" if thonar_gauge_count >= 2 else "unavailable"
            matched_count = thonar_gauge_count if gauge_mode == "normal" else thonar_gauge_unv_count
            self._lock_in_sacred_gauges(
                f"Phase 2 setup check confirmed {matched_count} {gauge_mode} thonar_gauge card(s)."
            )

        print(
            "Phase 2 turn 1 setup check -> "
            f"thonar_gauge_count={thonar_gauge_count}, "
            f"thonar_gauge_unv_count={thonar_gauge_unv_count}, "
            f"has_nasi_stun={has_nasi_stun}, has_thonar_stance={has_thonar_stance}."
        )

        if not self.sacred_gauges_locked_in and thonar_gauge_count < 2 and thonar_gauge_unv_count < 2:
            print(
                "Phase 2 turn 1 setup check failed: neither 2 normal `thonar_gauge` cards nor "
                "2 `thonar_gauge_unv` cards were found. Resetting fight."
            )
            return best_hand, True

        if not (has_nasi_stun or has_thonar_stance):
            print("Phase 2 turn 1 setup check failed: neither nasi_stun nor thonar_stance is available. Resetting fight.")
            return best_hand, True

        return best_hand, False

    def _lock_in_sacred_gauges(self, reason: str):
        if self.sacred_gauges_locked_in:
            return
        self.sacred_gauges_locked_in = True
        print(f"Sacred thonar_gauge requirement locked in for this run. {reason}")

    def _sample_best_phase2_turn1_hand(self, initial_hand):
        best_hand = initial_hand
        best_gauge_count = self._count_thonar_gauge_cards(initial_hand)
        best_gauge_unv_count = self._count_thonar_gauge_cards(initial_hand, unavailable_only=True)
        best_has_nasi_stun = bool(self._matching_hand_cards(initial_hand, ("dogs_nasi_stun",)))
        best_has_thonar_stance = bool(self._matching_hand_cards(initial_hand, ("thonar_stance",)))
        best_score = (
            max(best_gauge_count, best_gauge_unv_count),
            best_gauge_count,
            best_gauge_unv_count,
            int(best_has_nasi_stun or best_has_thonar_stance),
            int(best_has_nasi_stun),
            int(best_has_thonar_stance),
        )

        for sample_idx in range(2):
            time.sleep(0.12)
            sampled_hand = get_hand_cards()
            gauge_count = self._count_thonar_gauge_cards(sampled_hand)
            gauge_unv_count = self._count_thonar_gauge_cards(sampled_hand, unavailable_only=True)
            has_nasi_stun = bool(self._matching_hand_cards(sampled_hand, ("dogs_nasi_stun",)))
            has_thonar_stance = bool(self._matching_hand_cards(sampled_hand, ("thonar_stance",)))
            score = (
                max(gauge_count, gauge_unv_count),
                gauge_count,
                gauge_unv_count,
                int(has_nasi_stun or has_thonar_stance),
                int(has_nasi_stun),
                int(has_thonar_stance),
            )

            print(
                "Phase 2 turn 1 setup sample -> "
                f"sample={sample_idx + 2}, thonar_gauge_count={gauge_count}, "
                f"thonar_gauge_unv_count={gauge_unv_count}, "
                f"has_nasi_stun={has_nasi_stun}, has_thonar_stance={has_thonar_stance}."
            )

            if score > best_score:
                best_hand = sampled_hand
                best_gauge_count = gauge_count
                best_gauge_unv_count = gauge_unv_count
                best_has_nasi_stun = has_nasi_stun
                best_has_thonar_stance = has_thonar_stance
                best_score = score

        return best_hand, best_gauge_count, best_gauge_unv_count, best_has_nasi_stun, best_has_thonar_stance

    def _matching_hand_cards(self, hand_of_cards, template_names: tuple[str, ...]):
        return [
            card
            for card in hand_of_cards
            if card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
            and card.card_image is not None
            and any(find(getattr(vio, template_name), card.card_image) for template_name in template_names)
        ]

    def _count_thonar_gauge_cards(self, hand_of_cards, unavailable_only=False) -> int:
        unavailable_vision = getattr(vio, "thonar_gauge_unv", None)
        return sum(
            card.card_image is not None
            and (
                (unavailable_vision is not None and find(unavailable_vision, card.card_image))
                if unavailable_only
                else find(vio.thonar_gauge, card.card_image)
            )
            for card in hand_of_cards
        )

    def _should_stop_before_phase(self, phase: int) -> bool:
        if phase >= 3 and getattr(self.battle_strategy, "stop_after_phase_2", False):
            self.complete_callback(
                stop_farmer=True,
                reason="Reached Dogs Floor 4 phase 3; stopping cleanly after the scripted phase 2.",
            )
            self.exit_thread = True
            return True
        return False

    def _should_reset_for_phase_turn_limit(self, phase: int) -> bool:
        if phase not in {1, 2}:
            return False

        phase_turn = getattr(self.battle_strategy, "turn", 0)
        if phase_turn >= self.max_allowed_turns_per_phase:
            print(
                f"Phase {phase} safety check triggered: current scripted turn is {phase_turn + 1}, "
                f"which is beyond the allowed {self.max_allowed_turns_per_phase} turns."
            )
            return True

        return False

    def _count_phase3_gold_thonar_gauges(self, hand_of_cards) -> int:
        return sum(
            card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
            and card.card_rank == CardRanks.GOLD
            and card.card_image is not None
            and find(vio.thonar_gauge, card.card_image)
            for card in hand_of_cards
        )

    def _should_reset_for_phase3_turn1_gold_gauge_setup(self, hand_of_cards) -> bool:
        strategy_turn = getattr(self.battle_strategy, "turn", 0)
        if strategy_turn != 0:
            return False

        best_gold_count = self._count_phase3_gold_thonar_gauges(hand_of_cards)
        for _ in range(2):
            if best_gold_count >= 2:
                break
            time.sleep(0.12)
            best_gold_count = max(best_gold_count, self._count_phase3_gold_thonar_gauges(get_hand_cards()))

        print(f"Phase 3 turn 1 gold thonar_gauge check -> count={best_gold_count}.")
        if hasattr(type(self.battle_strategy), "phase3_gold_gauges_locked_in"):
            type(self.battle_strategy).phase3_gold_gauges_locked_in = best_gold_count >= 2
        return best_gold_count < 2

    def _should_reset_for_phase3_persistent_5percent_limit(self, screenshot) -> bool:
        if IFighter.current_phase != 3:
            return False
        if not getattr(self.battle_strategy, "phase3_gimmick1_completed", False):
            return False
        left_region = crop_image(screenshot, self.PHASE3_5PCT_LEFT_TOP_LEFT, self.PHASE3_5PCT_LEFT_BOTTOM_RIGHT)
        right_region = crop_image(screenshot, self.PHASE3_5PCT_RIGHT_TOP_LEFT, self.PHASE3_5PCT_RIGHT_BOTTOM_RIGHT)
        if not (
            find(vio.dogs_5perc_dmg_limit, left_region, threshold=0.8)
            or find(vio.dogs_5perc_dmg_limit, right_region, threshold=0.8)
        ):
            return False

        print("Phase 3 safety check triggered: 5% damage limit is still visible after Stage 2 completed.")
        return True

    def exit_fight_state(self):
        """Forfeit the fight to reset a bad Phase 2 hand."""
        screenshot, window_location = capture_window()

        if find(vio.ok_main_button, screenshot):
            self.current_state = FightingStates.DEFEAT
            return

        if find_and_click(vio.forfeit, screenshot, window_location):
            return

        find_and_click(vio.pause, screenshot, window_location)

    def _trigger_phase_reset(self, message: str | None = None):
        if message:
            print(message)
        print("Triggering Dogs Floor 4 fight reset.")
        self.reset_phase = IFighter.current_phase
        self._reset_dogs_floor4_state("Dogs Floor 4 local state cleared for reset.")
        self.reset_pending = True
        self.current_state = FightingStates.EXIT_FIGHT

    def _reset_dogs_floor4_state(self, log_message: str | None = None):
        IFighter.current_phase = -1
        self.target_selected_phase = None
        self.phase1_buff_sacred_check_done = False
        self.phase1_turn2_backup_check_done = False
        self.phase1_turn1_confirmed = False
        self.phase1_turn1_wait_logged = False
        self.phase3_confirmed_target_side = None
        self.last_phase_start_validation = None
        self.sacred_gauges_locked_in = False
        self.last_known_thonar_gauge_count = 0
        self.turn_actions_taken = 0
        self.turn_completion_wait_logged = False
        self.awaiting_full_turn_open = False
        self.awaiting_full_turn_open_since = 0.0
        self._clear_phase2_post_talent_plan()
        if hasattr(self.battle_strategy, "reset_run_state"):
            self.battle_strategy.reset_run_state()
        elif hasattr(self.battle_strategy, "_initialize_static_variables"):
            self.battle_strategy.reset_fight_turn()
            self.battle_strategy._initialize_static_variables()
        if log_message:
            print(log_message)

    def defeat_state(self):
        """We've lost the battle..."""
        screenshot, window_location = capture_window()

        find_and_click(vio.daily_quest_info, screenshot, window_location)
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.db_loading_screen, screenshot):
            phase = self.reset_phase if self.reset_phase is not None else IFighter.current_phase
            if not self.reset_pending:
                self._reset_dogs_floor4_state("Dogs Floor 4 local state cleared for a fresh run.")
            self.complete_callback(victory=False, phase=phase, reset=self.reset_pending)
            self.exit_thread = True
            self.reset_pending = False
            self.reset_phase = None

    def _phase3_target_coordinate_key(self, target_side: str) -> str:
        return "dark_dog" if target_side == "left" else "light_dog"

    def _detect_phase3_target_marker_hits(self, screenshot, vision_image, side: str, threshold=0.8):
        template = vision_image.needle_img
        if template is None or screenshot is None:
            return []

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        match_locations = np.where(result >= threshold)
        template_height, template_width = template.shape[:2]

        rectangles = []
        for x, y in zip(match_locations[1], match_locations[0]):
            rectangles.append([int(x), int(y), int(template_width), int(template_height)])
            rectangles.append([int(x), int(y), int(template_width), int(template_height)])

        if not rectangles:
            return []

        grouped_rectangles, grouped_weights = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)
        if len(grouped_rectangles) == 0:
            return []

        hits = []
        for rect, weight in zip(grouped_rectangles, grouped_weights):
            x, y, width, height = rect
            hits.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "w": int(width),
                    "h": int(height),
                    "side": side,
                    "weight": int(weight),
                }
            )

        hits.sort(key=lambda hit: (hit["x"], hit["y"]))
        return hits

    def _get_phase3_selected_target_sides(self, screenshot) -> set[str]:
        selected_sides = set()
        if self._detect_phase3_target_marker_hits(screenshot, vio.dogs_left_target_sel, "left", threshold=0.8):
            selected_sides.add("left")
        if self._detect_phase3_target_marker_hits(screenshot, vio.dogs_right_target_sel, "right", threshold=0.8) or (
            self._detect_phase3_target_marker_hits(screenshot, vio.dogs_right_target_sel2, "right", threshold=0.8)
        ):
            selected_sides.add("right")
        return selected_sides

    def _wait_for_phase3_target_selection(self, target_side: str, timeout_seconds=0.75, poll_interval=0.05) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            screenshot, _ = capture_window()
            selected_sides = self._get_phase3_selected_target_sides(screenshot)
            if target_side in selected_sides:
                self.phase3_confirmed_target_side = target_side
                return True
            time.sleep(poll_interval)
        return False

    def _ensure_phase3_target_selected(self, target_side: str, window_location) -> bool:
        screenshot, _ = capture_window()
        selected_sides = self._get_phase3_selected_target_sides(screenshot)

        if target_side in selected_sides:
            self.phase3_confirmed_target_side = target_side
            print(f"Phase 3 target verification: {target_side} dog is already selected.")
            return True

        print(f"Phase 3 targeting {target_side} dog.")
        click_im(Coordinates.get_coordinates(self._phase3_target_coordinate_key(target_side)), window_location)
        if self._wait_for_phase3_target_selection(target_side):
            print(f"Phase 3 target verification: confirmed {target_side} dog selection.")
            return True

        screenshot, _ = capture_window()
        if hasattr(self.battle_strategy, "handle_phase3_target_selection_failure") and self.battle_strategy.handle_phase3_target_selection_failure(
            screenshot,
            target_side,
        ):
            print(
                "Phase 3 target verification fallback: could not confirm "
                f"{target_side} selection, and the strategy inferred that dog is already dead. Replanning next action."
            )
            self.phase3_confirmed_target_side = None
            return False

        print(
            "Phase 3 target verification failed: could not confirm "
            f"{target_side} dog selection after click. Deferring this card so we do not fire at random."
        )
        self.phase3_confirmed_target_side = None
        return False

    def _activate_phase3_talent(self, window_location):
        print("Activating Dogs Floor 4 phase 3 talent.")
        click_im(Coordinates.get_coordinates("talent"), window_location)
        time.sleep(2.5)

    def _should_block_phase1_turn1_card(self, list_of_cards, index: int) -> bool:
        if IFighter.current_phase != 1:
            return False
        if getattr(self.battle_strategy, "turn", 0) != 0:
            return False
        if not (0 <= index < len(list_of_cards)):
            return False

        card = list_of_cards[index]
        is_thonar_gauge = (
            card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
            and card.card_image is not None
            and find(vio.thonar_gauge, card.card_image)
        )
        if is_thonar_gauge:
            print("Blocking accidental thonar_gauge usage during phase 1 turn 1 while the fight-start UI settles.")
        return is_thonar_gauge

    def _phase2_all_cards_unavailable(self, hand_of_cards) -> bool:
        return all(card.card_type in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND) for card in hand_of_cards)

    def _phase2_turn2_dogded_visible(self, screenshot) -> bool:
        if getattr(vio, "dogs_p2t2_dogded", None) is None:
            return False
        region = crop_image(
            screenshot,
            self.PHASE2_TURN2_DOGDED_TOP_LEFT,
            self.PHASE2_TURN2_DOGDED_BOTTOM_RIGHT,
        )
        return find(vio.dogs_p2t2_dogded, region, threshold=0.8)

    def _matching_phase2_hand_indices(self, hand_of_cards, template_names, include_disabled=False):
        matching_ids = []
        for idx, card in enumerate(hand_of_cards):
            if card.card_type in (CardTypes.NONE, CardTypes.GROUND):
                continue
            if not include_disabled and card.card_type == CardTypes.DISABLED:
                continue
            if card.card_image is None:
                continue
            if any(getattr(vio, template_name, None) is not None and find(getattr(vio, template_name), card.card_image) for template_name in template_names):
                matching_ids.append(idx)
        return matching_ids

    def _clear_phase2_post_talent_plan(self):
        self.phase2_post_talent_mode = False
        self.phase2_post_talent_steps = []
        self.phase2_post_talent_template_names = ()
        self.phase2_post_talent_snapshot_index = None

    def _prepare_phase2_post_talent_plan(self, live_hand_of_cards, snapshot_hand_of_cards):
        remaining_actions = max(0, 4 - self.turn_actions_taken)
        visible_nasi_ult_ids = self._matching_phase2_hand_indices(live_hand_of_cards, ("dogs_nasi_ult",))
        visible_nasi_heal_ids = self._matching_phase2_hand_indices(
            live_hand_of_cards,
            ("dogs_nasi_heal",),
        )

        self.phase2_post_talent_mode = True
        if visible_nasi_ult_ids:
            self.phase2_post_talent_steps = ["move"] * remaining_actions
            self.phase2_post_talent_template_names = ("dogs_nasi_ult",)
            self.phase2_post_talent_snapshot_index = visible_nasi_ult_ids[-1]
            print("Phase 2 post-talent plan: dog is dead and nasi_ult is visible, so moving it for the rest of the turn.")
            return

        if visible_nasi_heal_ids:
            visible_count = min(len(visible_nasi_heal_ids), remaining_actions)
            move_count = max(0, remaining_actions - visible_count)
            self.phase2_post_talent_steps = ["move"] * move_count + ["play"] * visible_count
            self.phase2_post_talent_template_names = ("dogs_nasi_heal",)
            self.phase2_post_talent_snapshot_index = visible_nasi_heal_ids[-1]
            print(
                "Phase 2 post-talent plan: dog is dead and nasi_heal is visible, "
                f"so doing {move_count} move(s) and {visible_count} play(s)."
            )
            return

        snapshot_nasi_ids = self._matching_phase2_hand_indices(
            snapshot_hand_of_cards,
            ("dogs_nasi_ult", "dogs_nasi_heal", "dogs_nasi_stun"),
            include_disabled=True,
        )
        self.phase2_post_talent_steps = ["move"] * max(0, remaining_actions - 1) + (["play"] if remaining_actions > 0 else [])
        self.phase2_post_talent_template_names = ("dogs_nasi_ult", "dogs_nasi_heal", "dogs_nasi_stun")
        self.phase2_post_talent_snapshot_index = snapshot_nasi_ids[-1] if snapshot_nasi_ids else None
        print("Phase 2 post-talent plan: dog is dead, so falling back to the last seen nasi card from the snapshot.")

    def _phase2_random_transition_move_action(self, hand_of_cards):
        movable_ids = [
            idx for idx, card in enumerate(hand_of_cards) if card.card_type not in (CardTypes.NONE, CardTypes.GROUND)
        ]
        if len(movable_ids) >= 2:
            return [movable_ids[-1], movable_ids[-2]]
        if len(movable_ids) == 1:
            origin_idx = movable_ids[0]
            if origin_idx > 0:
                return [origin_idx, origin_idx - 1]
            if origin_idx < len(hand_of_cards) - 1:
                return [origin_idx, origin_idx + 1]
        return None

    def _phase2_post_talent_action(self, hand_of_cards):
        if not self.phase2_post_talent_steps:
            self._clear_phase2_post_talent_plan()
            return None

        step = self.phase2_post_talent_steps.pop(0)
        visible_ids = self._matching_phase2_hand_indices(hand_of_cards, self.phase2_post_talent_template_names)

        if step == "play":
            if visible_ids:
                action = visible_ids[-1]
            elif self.phase2_post_talent_snapshot_index is not None and 0 <= self.phase2_post_talent_snapshot_index < len(hand_of_cards):
                action = self.phase2_post_talent_snapshot_index
            else:
                action = self._phase2_random_transition_move_action(hand_of_cards)
        else:
            if visible_ids:
                origin_idx = visible_ids[-1]
            elif self.phase2_post_talent_snapshot_index is not None and 0 <= self.phase2_post_talent_snapshot_index < len(hand_of_cards):
                origin_idx = self.phase2_post_talent_snapshot_index
            else:
                origin_idx = None

            if origin_idx is None:
                action = self._phase2_random_transition_move_action(hand_of_cards)
            else:
                target_idx = origin_idx + 1 if origin_idx < len(hand_of_cards) - 1 else origin_idx - 1
                if target_idx < 0 or target_idx == origin_idx:
                    action = self._phase2_random_transition_move_action(hand_of_cards)
                else:
                    self.phase2_post_talent_snapshot_index = target_idx
                    action = [origin_idx, target_idx]

        if not self.phase2_post_talent_steps:
            self._clear_phase2_post_talent_plan()

        return action

    def _play_card(self, list_of_cards, index, window_location, screenshot=None):
        if isinstance(index, Integral) and index == -1:
            print("Dogs Floor 4 safety guard: strategy returned no valid card action.")
            if IFighter.current_phase == 2:
                if hasattr(self.battle_strategy, "should_finish_phase2_turn_early") and self.battle_strategy.should_finish_phase2_turn_early(list_of_cards):
                    print(
                        "Phase 2 safety guard: lethal damage is already secured and only protected/unavailable cards remain. "
                        "Finishing the turn early."
                    )
                    self.finish_turn()
                    return Card()
                self._trigger_phase_reset(
                    "No valid safe Phase 2 action was found. Resetting fight instead of risking sacred-card misuse."
                )
            return Card()

        if isinstance(index, Integral) and self._should_block_phase1_turn1_card(list_of_cards, index):
            return Card()

        target_side = None
        expected_auto_merges = 0

        if IFighter.current_phase == 2 and isinstance(index, Integral):
            strategy_cls = type(self.battle_strategy)
            use_talent = getattr(strategy_cls, "phase2_use_talent_before_next_play", False)
            if use_talent:
                snapshot_hand_of_cards = list_of_cards
                self.phase2_post_talent_mode = True
                self._activate_phase3_talent(window_location)
                time.sleep(1.0)
                post_talent_screenshot, _ = capture_window()
                live_hand_of_cards = get_hand_cards()
                if self._phase2_turn2_dogded_visible(post_talent_screenshot):
                    self._prepare_phase2_post_talent_plan(live_hand_of_cards, snapshot_hand_of_cards)
                    dead_action = self._phase2_post_talent_action(live_hand_of_cards)
                    strategy_cls.phase2_use_talent_before_next_play = False
                    if dead_action is None:
                        self.finish_turn()
                        return Card()
                    index = dead_action
                    list_of_cards = live_hand_of_cards
                    screenshot = post_talent_screenshot
                else:
                    self.phase2_post_talent_mode = False
                strategy_cls.phase2_use_talent_before_next_play = False

        if IFighter.current_phase == 3 and isinstance(index, Integral):
            strategy_cls = type(self.battle_strategy)
            use_talent = getattr(strategy_cls, "phase3_use_talent_before_next_play", False)
            target_side = getattr(strategy_cls, "phase3_next_target_side", None)

            if use_talent:
                self._activate_phase3_talent(window_location)
                if hasattr(self.battle_strategy, "register_phase3_talent_use"):
                    self.battle_strategy.register_phase3_talent_use()
                strategy_cls.phase3_use_talent_before_next_play = False

            if target_side in {"left", "right"}:
                if not self._ensure_phase3_target_selected(target_side, window_location):
                    return Card()
                strategy_cls.phase3_next_target_side = None

        if isinstance(index, Integral) and hasattr(self.battle_strategy, "estimate_auto_merge_count_after_play"):
            expected_auto_merges = self.battle_strategy.estimate_auto_merge_count_after_play(list_of_cards, index)

        played_card = super()._play_card(list_of_cards, index=index, window_location=window_location, screenshot=screenshot)
        self.turn_actions_taken += 1
        self.turn_completion_wait_logged = False

        if hasattr(self.battle_strategy, "register_confirmed_action"):
            self.battle_strategy.register_confirmed_action(list_of_cards, index, played_card)

        if IFighter.current_phase == 3 and isinstance(index, Integral) and hasattr(self.battle_strategy, "register_phase3_card_play"):
            self.battle_strategy.register_phase3_card_play(played_card, target_side=target_side)

        if expected_auto_merges > 0:
            merge_wait = 0.55 + (expected_auto_merges - 1) * 0.35
            print(
                "Dogs Floor 4 merge guard: this click should trigger "
                f"{expected_auto_merges} auto-merge(s), so waiting {merge_wait:.2f}s before the next action."
            )
            time.sleep(merge_wait)

        return played_card

    def finish_turn(self):
        self.turn_actions_taken = 0
        self.turn_completion_wait_logged = False
        self.awaiting_full_turn_open = True
        self.awaiting_full_turn_open_since = time.time()
        self._clear_phase2_post_talent_plan()
        if IFighter.current_phase == 3 and hasattr(self.battle_strategy, "handle_phase3_turn_end"):
            self.battle_strategy.handle_phase3_turn_end()
        if hasattr(self.battle_strategy, "register_turn_completed"):
            self.battle_strategy.register_turn_completed()
        return super().finish_turn()

    @IFighter.run_wrapper
    def run(self, floor=4):

        self._reset_dogs_floor4_state("Starting Dogs Floor 4 from fresh phase 1 state.")
        print(f"Fighting very hard on floor {floor}...")
        IFighter.current_floor = floor
        self.reset_pending = False
        self.reset_phase = None

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

            time.sleep(0.5)
