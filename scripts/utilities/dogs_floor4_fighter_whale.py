"""Dogs Floor 4 fighter: first MY_TURN waits for the Dogs Escalin talent marker."""

import time
from collections.abc import Callable
from numbers import Integral

from utilities.card_data import Card
from utilities.coordinates import Coordinates
import utilities.vision_images as vio
from utilities.dogs_fighter import DogsFighter
from utilities.dogs_floor4_fighting_strategies_whale import DogsFloor4WhaleBattleStrategy
from utilities.general_fighter_interface import FightingStates, IFighter
from utilities.utilities import capture_window, click_im, find


class DogsFloor4FighterWhale(DogsFighter):
    battle_strategy: DogsFloor4WhaleBattleStrategy
    SLOT_STALL_RETRY_THRESHOLD = 8
    SINGLE_AUTO_MERGE_WAIT_SECONDS = 0.6
    DOUBLE_AUTO_MERGE_WAIT_SECONDS = 1.1
    TARGET_CONFIRM_RETRIES = 3
    TARGET_CONFIRM_TIMEOUT_SECONDS = 0.8
    TARGET_CONFIRM_POLL_SECONDS = 0.08

    activate_phase3_escalin_talent = False
    _f4_first_my_turn_pending = True
    _fight_turn_incremented_at_turn_start = False

    def __init__(self, battle_strategy: type[DogsFloor4WhaleBattleStrategy], callback: Callable | None = None):
        super().__init__(battle_strategy=battle_strategy, callback=callback)
        self._reset_slot_stall_guard()
        self.target_selected_phase = None

    @staticmethod
    def _dogs_talent_marker_visible(screenshot) -> bool:
        return find(vio.dogs_escalin_talent, screenshot, threshold=0.75)

    def _try_enter_my_turn(self, screenshot) -> bool:
        if DogsFloor4FighterWhale._f4_first_my_turn_pending:
            if not self._dogs_talent_marker_visible(screenshot):
                # Do not use empty-slot detection yet; wait until the talent button is visible.
                return False
            available = DogsFighter.count_empty_card_slots(screenshot, threshold=0.8)
            if available <= 0:
                available = 4
            if available >= 3 and self._check_disabled_hand():
                print("Our hand is fully disabled, let's restart the fight!")
                self.current_state = FightingStates.EXIT_FIGHT
                return True
            self.available_card_slots = available
            print(f"MY TURN (Floor 4 first turn: Dogs Escalin talent), selecting {available} cards...")
            self.current_state = FightingStates.MY_TURN
            DogsFloor4FighterWhale._f4_first_my_turn_pending = False
            return True

        entered = super()._try_enter_my_turn(screenshot)
        if entered:
            DogsFloor4FighterWhale._f4_first_my_turn_pending = False
        return entered

    def _maybe_increment_fight_turn_at_turn_start(self):
        """Floor 4: count turns at turn start using talent visibility first, slots second.

        Runs every MY_TURN loop tick before ``play_cards``; mid-turn ticks are skipped via ``picked_cards[0]``.
        Every Floor 4 phase starts from a fresh counter, and ``finish_turn`` never increments it.
        This keeps ``fight_turn`` meaning consistent across phases: it increments exactly once, at the
        start of a turn. If Escalin talent is visible, that is treated as a definitive turn-start signal.
        Otherwise we fall back to the normal 3+/4-slot opening rule. If units die and neither signal is
        observed cleanly, the counter remains best-effort and cleanup turns may not be counted.

        Opening slot count may be nudged up from vision when it exceeds ``available_card_slots``
        (same idea as ``play_cards``).
        """
        if DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start:
            return

        if self.picked_cards[0].card_image is not None:
            return

        screenshot, _ = capture_window()
        empty = DogsFighter.count_empty_card_slots(screenshot, threshold=0.8)
        self._try_increment_fight_turn_from_start_signals(
            screenshot,
            empty_card_slots=empty,
            talent_log="Turn start detected from Dogs Escalin talent visibility.",
            slots_log_prefix="Turn start detected from empty card slots",
        )

    def my_turn_state(self):
        if not self._identify_current_phase():
            return
        self._maybe_increment_fight_turn_at_turn_start()
        if self._should_exit_before_play_cards() or self._consume_requested_reset_if_any():
            return
        self.play_cards()

    def play_cards(self, **kwargs):
        """Re-check the turn-limit cutoff after the late slot-detection fallback.

        Floor 4 can discover a normal 3+/4-slot opening only inside ``play_cards``.
        When that path bumps ``fight_turn`` to 10, we must still forfeit before the
        first card pick rather than letting one card slip through.
        """
        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot)

        self._before_pick_cards(
            screenshot=screenshot, window_location=window_location, empty_card_slots=empty_card_slots
        )

        if empty_card_slots > self.available_card_slots:
            self.available_card_slots = empty_card_slots

        slot_index = max(0, self.available_card_slots - empty_card_slots)
        slot_already_used = (
            0 <= slot_index < len(self.picked_cards) and self.picked_cards[slot_index].card_image is not None
        )
        if slot_already_used:
            if slot_index >= max(0, self.available_card_slots - 1):
                self._reset_slot_stall_guard()
                print(
                    "Dogs Floor 4 turn-end guard: the last slot was already used, "
                    "but empty-slot detection still reports one opening. Treating the turn as complete."
                )
                return self.finish_turn()
            repeated_stall = (
                self._stalled_slot_index == slot_index and self._stalled_slot_empty_slots == empty_card_slots
            )
            self._stalled_slot_index = slot_index
            self._stalled_slot_empty_slots = empty_card_slots
            self._stalled_slot_repeats = self._stalled_slot_repeats + 1 if repeated_stall else 1
            if self._stalled_slot_repeats >= self.SLOT_STALL_RETRY_THRESHOLD:
                print(
                    "Dogs Floor 4 stall recovery: slot",
                    slot_index,
                    "never cleared after",
                    self._stalled_slot_repeats,
                    "checks, so re-arming that action and trying again.",
                )
                self.picked_cards[slot_index] = Card()
                self._reset_slot_stall_guard()
                slot_already_used = False
            else:
                print(
                    "Dogs Floor 4 slot guard: slot",
                    slot_index,
                    "was already consumed, so waiting for the hand to settle before sending another card.",
                )
                return
        else:
            self._reset_slot_stall_guard()

        if self._should_exit_before_play_cards() or self._consume_requested_reset_if_any():
            return

        is_last_action_slot = slot_index >= max(0, self.available_card_slots - 1)
        result = super().play_cards(**kwargs)
        self._reset_slot_stall_guard()
        if (
            result is None
            and is_last_action_slot
            and self.current_state == FightingStates.MY_TURN
        ):
            print(
                "Dogs Floor 4 turn-end guard: the last action slot was already sent, "
                "so finishing the turn without waiting for slot vision to catch up."
            )
            return self.finish_turn()

        return result

    def _should_exit_before_play_cards(self) -> bool:
        is_turn_start = self.picked_cards[0].card_image is None
        fight_turn = self.battle_strategy.fight_turn
        if IFighter.current_phase in {2, 3}:
            print(f"Phase {IFighter.current_phase} turn {fight_turn}")
        if IFighter.current_phase not in {2, 3} or not is_turn_start or fight_turn < 10:
            return False

        print(
            f"Phase {IFighter.current_phase} reached the turn limit; manually forfeiting before playing cards.",
            f"fight_turn={fight_turn}",
        )
        self.current_state = FightingStates.EXIT_FIGHT
        return True

    def _consume_requested_reset_if_any(self) -> bool:
        consume_reset = getattr(self.battle_strategy, "consume_requested_reset_reason", None)
        if not callable(consume_reset):
            return False

        reset_reason = consume_reset()
        if not reset_reason:
            return False

        print(reset_reason)
        self.current_state = FightingStates.EXIT_FIGHT
        return True

    def _before_pick_cards(self, *, screenshot, window_location, empty_card_slots: int) -> None:
        """Floor 4 fallback: count a turn late if talent or slot detection stabilizes inside ``play_cards``.

        Race we are handling:
        - ``_try_enter_my_turn`` and the early turn-start check may still see only 1 empty slot
        - the shared ``play_cards`` flow may then see 3+ empty slots moments later on the first pick
          of the same turn

        In that case, count this as a normal Floor 4 turn here using the same slot-count observation
        that will drive slot-index calculation and card selection. We still keep the overall policy
        of start-only counting and never increment at ``finish_turn``.
        """
        if DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start:
            return
        if self.picked_cards[0].card_image is not None:
            return
        self._try_increment_fight_turn_from_start_signals(
            screenshot,
            empty_card_slots=empty_card_slots,
            talent_log="Late turn-start detection from Dogs Escalin talent visibility.",
            slots_log_prefix="Late turn-start detection from empty card slots",
        )

    def _try_increment_fight_turn_from_start_signals(
        self,
        screenshot,
        *,
        empty_card_slots: int,
        talent_log: str,
        slots_log_prefix: str,
    ) -> bool:
        """Increment once from Floor 4 turn-start signals.

        Talent visibility is treated as definitive. When talent is absent, we
        fall back to the normal 3+/4-slot opening rule.
        """
        if self._dogs_talent_marker_visible(screenshot):
            print(talent_log)
            self.battle_strategy.increment_fight_turn()
            DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start = True
            return True

        if empty_card_slots > self.available_card_slots:
            self.available_card_slots = empty_card_slots

        if self.available_card_slots < 3:
            return False

        print(f"{slots_log_prefix}: available_card_slots={self.available_card_slots}")
        self.battle_strategy.increment_fight_turn()
        DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start = True
        return True

    def finish_turn(self):
        # Floor 4 turn counting is start-only for every phase. We deliberately avoid end-of-turn
        # increments so short turns (for example, 1-slot cleanup turns) do not create confusing jumps.
        DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start = False
        self._reset_slot_stall_guard()
        self._reset_instance_variables()
        print("Finished my turn!")
        return 1

    def _play_card(self, list_of_cards, index, window_location, screenshot=None):
        expected_auto_merges = 0
        estimate_auto_merge_count = getattr(self.battle_strategy, "estimate_auto_merge_count_after_play", None)
        if isinstance(index, Integral) and callable(estimate_auto_merge_count):
            expected_auto_merges = estimate_auto_merge_count(list_of_cards, index)

        played_card = super()._play_card(
            list_of_cards,
            index=index,
            window_location=window_location,
            screenshot=screenshot,
        )

        if expected_auto_merges > 0:
            merge_wait = (
                self.SINGLE_AUTO_MERGE_WAIT_SECONDS
                if expected_auto_merges == 1
                else self.DOUBLE_AUTO_MERGE_WAIT_SECONDS
            )
            print(
                "Dogs Floor 4 merge guard: this click should trigger",
                expected_auto_merges,
                f"auto-merge(s), so waiting {merge_wait:.2f}s before the next action.",
            )
            time.sleep(merge_wait)

        return played_card

    def _reset_slot_stall_guard(self) -> None:
        self._stalled_slot_index = None
        self._stalled_slot_empty_slots = None
        self._stalled_slot_repeats = 0

    def _check_disabled_hand(self) -> bool:
        """If we have a disabled hand (same criteria as BirdFighter)."""
        screenshot, _ = capture_window()
        return find(vio.skill_locked, screenshot, threshold=0.6)

    def _identify_current_phase(self):
        previous_phase = IFighter.current_phase
        screenshot, window_location = capture_window()

        if find(vio.phase_1, screenshot, threshold=0.8) and IFighter.current_phase != 1:
            if DogsFighter.count_empty_card_slots(screenshot, threshold=0.8) > 1:
                IFighter.current_phase = 1
                self.target_selected_phase = None
        elif find(vio.phase_2, screenshot, threshold=0.8) and IFighter.current_phase != 2:
            IFighter.current_phase = 2
            self.target_selected_phase = None
        elif find(vio.phase_3_dogs, screenshot, threshold=0.8) and IFighter.current_phase != 3:
            IFighter.current_phase = 3
            self.target_selected_phase = None

        if IFighter.current_phase == 1 and self.target_selected_phase != 1:
            if not self._ensure_dogs_target_selected("right", "light_dog", window_location):
                return False
            self.target_selected_phase = 1
        elif IFighter.current_phase in {2, 3} and self.target_selected_phase != IFighter.current_phase:
            if not self._ensure_dogs_target_selected("left", "dark_dog", window_location):
                return False
            self.target_selected_phase = IFighter.current_phase

        if previous_phase != IFighter.current_phase:
            print(f"Entered phase {IFighter.current_phase}! Resetting the Floor 4 turn counter...")
            self.battle_strategy.reset_fight_turn()
            DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start = False
        return True

    @staticmethod
    def _get_dogs_selected_target_sides(screenshot) -> set[str]:
        selected_sides = set()
        if find(vio.dogs_left_target_sel, screenshot, threshold=0.8):
            selected_sides.add("left")
        if find(vio.dogs_right_target_sel, screenshot, threshold=0.8) or find(
            vio.dogs_right_target_sel2,
            screenshot,
            threshold=0.8,
        ):
            selected_sides.add("right")
        return selected_sides

    def _wait_for_dogs_target_selection(self, target_side: str) -> bool:
        deadline = time.time() + self.TARGET_CONFIRM_TIMEOUT_SECONDS
        while time.time() < deadline:
            screenshot, _ = capture_window()
            if target_side in self._get_dogs_selected_target_sides(screenshot):
                return True
            time.sleep(self.TARGET_CONFIRM_POLL_SECONDS)
        return False

    def _ensure_dogs_target_selected(self, target_side: str, coordinate_key: str, window_location) -> bool:
        screenshot, _ = capture_window()
        if target_side in self._get_dogs_selected_target_sides(screenshot):
            print(f"Dogs target verification: {target_side} dog is already selected.")
            return True

        for attempt in range(1, self.TARGET_CONFIRM_RETRIES + 1):
            print(
                f"Dogs targeting: clicking the {target_side} dog for phase {IFighter.current_phase} "
                f"(attempt {attempt}/{self.TARGET_CONFIRM_RETRIES})."
            )
            click_im(Coordinates.get_coordinates(coordinate_key), window_location)
            if self._wait_for_dogs_target_selection(target_side):
                print(f"Dogs target verification: confirmed {target_side} dog selection.")
                return True

        print(
            f"Dogs target verification failed: could not confirm {target_side} dog selection "
            "after repeated clicks. Waiting for the next loop instead of firing cards blind."
        )
        return False

    def run(self, floor=4, meli3k_in_team=False, bluegow_in_team=False):
        self.battle_strategy.reset_run_state(
            meli3k_in_team=meli3k_in_team,
            bluegow_in_team=bluegow_in_team,
        )
        DogsFloor4FighterWhale._f4_first_my_turn_pending = True
        DogsFloor4FighterWhale._fight_turn_incremented_at_turn_start = False

        super().run(floor=floor)



