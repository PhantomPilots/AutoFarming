from collections.abc import Sequence
from enum import Enum

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy
from utilities.utilities import crop_image, find


class DogsFloor4Phase3State(Enum):
    STALL_FOR_GAUGE = "STALL_FOR_GAUGE"
    TRIGGER_GIMMICK_1 = "TRIGGER_GIMMICK_1"
    KILL_BOTH_DOGS = "KILL_BOTH_DOGS"


class DogsFloor4BattleStrategy(IBattleStrategy):
    """Scripted Dogs Floor 4 strategy.

    Phase 1, Phase 2, and Phase 3 are implemented.
    """

    turn = 0
    _phase_initialized = set()
    _last_phase_seen = None
    stop_after_phase_2 = False
    ult_gauges = {
        "escalin": 0,
        "roxy": 0,
        "nasi": 0,
        "thonar": 0,
    }
    phase2_damage_state = {
        "escalin_st": 0,
        "other_damage": 0,
    }
    phase2_use_talent_before_next_play = False
    phase3_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
    phase3_current_gauges = {"left": 0, "right": 0}
    phase3_next_turn_gauges = {"left": 0, "right": 0}
    phase3_pending_gauge_reset = {"left": False, "right": False}
    phase3_last_seen_cards = {"left": [], "right": []}
    phase3_remaining_hp = {"left": 4_090_000, "right": 4_289_500}
    phase3_damage_applied = {"left": 0, "right": 0}
    phase3_gimmick1_completed = False
    phase3_trigger_turn_active = False
    phase3_trigger_gauge_targets_used = set()
    phase3_observed_turn = None
    phase3_observed_action_totals = {"left": 0, "right": 0}
    phase3_next_target_side = None
    phase3_use_talent_before_next_play = False
    phase3_trigger_used_nasi_ult = False
    phase3_trigger_sequence = None
    phase3_trigger_reserved_gauge_steps = 0
    phase3_dead_sides = set()
    phase3_detected_stage_turn = None
    phase3_missing_thonar_reset_pending = False
    phase3_gold_gauges_locked_in = False

    PHASE3_MAX_DOG_GAUGE = 7
    PHASE3_LEFT_HP = 4_090_000
    PHASE3_RIGHT_HP = 4_289_500
    PHASE3_PRE_GIMMICK_DAMAGE_CAP = {"left": 204_500, "right": 214_475}
    PHASE3_DAMAGE_CAP = {"left": 1_227_000, "right": 1_286_850}
    PHASE3_ESCALIN_ST_TOTAL_DAMAGE = {"left": 2_085_900, "right": 2_187_645}
    PHASE3_ROXY_PASSIVE_BONUS_DAMAGE = 70_000
    PHASE3_LOW_DAMAGE = {
        "dogs_nasi_stun": 100_000,
        "thonar_gauge_non_gold": 100_000,
        "thonar_stance": 150_000,
    }
    PHASE3_GOLD_THONAR_GAUGE_DAMAGE = 220_000
    PHASE3_TRIGGER_HEURISTIC_TURN = 2
    PHASE3_TRIGGER_HEURISTIC_MIN_OBSERVED_ACTIONS = 2
    PHASE3_GAUGE_DISPARITY_THRESHOLD = 2
    PHASE3_LEFT_TOP_LEFT = (70, 210)
    PHASE3_LEFT_BOTTOM_RIGHT = (220, 320)
    PHASE3_RIGHT_TOP_LEFT = (260, 210)
    PHASE3_RIGHT_BOTTOM_RIGHT = (400, 320)

    ESCALIN_TEMPLATES = ("escalin_st", "escalin_aoe", "escalin_ult")
    ESCALIN_NON_ULT_TEMPLATES = ("escalin_st", "escalin_aoe")
    ROXY_TEMPLATES = ("dogs_roxy_st", "dogs_roxy_aoe", "dogs_roxy_ult")
    ROXY_NON_ULT_TEMPLATES = ("dogs_roxy_st", "dogs_roxy_aoe")
    HEAVY_DAMAGE_TEMPLATES = (
        "escalin_st",
        "escalin_aoe",
        "escalin_ult",
        "dogs_roxy_st",
        "dogs_roxy_aoe",
        "dogs_roxy_ult",
        "thonar_ult",
    )
    NASI_TEMPLATES = ("dogs_nasi_heal", "dogs_nasi_stun", "dogs_nasi_ult")
    NASI_NON_ULT_TEMPLATES = ("dogs_nasi_heal", "dogs_nasi_stun")
    THONAR_TEMPLATES = ("thonar_stance", "thonar_gauge", "thonar_ult")

    def _initialize_static_variables(self):
        DogsFloor4BattleStrategy.turn = 0
        DogsFloor4BattleStrategy._phase_initialized = set()
        DogsFloor4BattleStrategy._last_phase_seen = None
        DogsFloor4BattleStrategy.ult_gauges = {
            "escalin": 0,
            "roxy": 0,
            "nasi": 0,
            "thonar": 0,
        }
        DogsFloor4BattleStrategy.phase2_damage_state = {
            "escalin_st": 0,
            "other_damage": 0,
        }
        DogsFloor4BattleStrategy.phase2_use_talent_before_next_play = False
        DogsFloor4BattleStrategy._reset_phase3_state()

    @classmethod
    def _reset_phase3_state(cls):
        cls.phase3_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
        cls.phase3_current_gauges = {"left": 0, "right": 0}
        cls.phase3_next_turn_gauges = {"left": 0, "right": 0}
        cls.phase3_pending_gauge_reset = {"left": False, "right": False}
        cls.phase3_last_seen_cards = {"left": [], "right": []}
        cls.phase3_remaining_hp = {"left": cls.PHASE3_LEFT_HP, "right": cls.PHASE3_RIGHT_HP}
        cls.phase3_damage_applied = {"left": 0, "right": 0}
        cls.phase3_gimmick1_completed = False
        cls.phase3_trigger_turn_active = False
        cls.phase3_trigger_gauge_targets_used = set()
        cls.phase3_observed_turn = None
        cls.phase3_observed_action_totals = {"left": 0, "right": 0}
        cls.phase3_next_target_side = None
        cls.phase3_use_talent_before_next_play = False
        cls.phase3_trigger_used_nasi_ult = False
        cls.phase3_trigger_sequence = None
        cls.phase3_trigger_reserved_gauge_steps = 0
        cls.phase3_dead_sides = set()
        cls.phase3_detected_stage_turn = None
        cls.phase3_missing_thonar_reset_pending = False
        cls.phase3_gold_gauges_locked_in = False

    def reset_run_state(self):
        self.reset_fight_turn()
        self._initialize_static_variables()

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        """Return the next scripted action for Dogs Floor 4."""

        if phase == 1 and DogsFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        DogsFloor4BattleStrategy._last_phase_seen = phase

        if phase == 1:
            action = self.get_next_card_index_phase1(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 2:
            action = self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 3:
            action = self.get_next_card_index_phase3(hand_of_cards, picked_cards, card_turn=card_turn)
        else:
            return -1

        return action

    def _maybe_reset(self, phase_id: str):
        if phase_id not in DogsFloor4BattleStrategy._phase_initialized:
            DogsFloor4BattleStrategy.turn = 0
            DogsFloor4BattleStrategy._phase_initialized.add(phase_id)
            if phase_id == "phase_2":
                DogsFloor4BattleStrategy.phase2_damage_state = {
                    "escalin_st": 0,
                    "other_damage": 0,
                }
                DogsFloor4BattleStrategy.phase2_use_talent_before_next_play = False
            elif phase_id == "phase_3":
                DogsFloor4BattleStrategy._reset_phase3_state()

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_1")

        if DogsFloor4BattleStrategy.turn == 0:
            action = self._phase1_turn1_action(hand_of_cards, card_turn)
        elif DogsFloor4BattleStrategy.turn == 1:
            action = self._phase1_turn2_action(hand_of_cards, picked_cards, card_turn)
        else:
            action = self._phase1_turn3plus_action(hand_of_cards, picked_cards, card_turn)

        return action

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_2")

        if DogsFloor4BattleStrategy.turn == 0:
            action = self._phase2_turn1_action(hand_of_cards, picked_cards, card_turn)
        elif DogsFloor4BattleStrategy.turn == 1:
            action = self._phase2_turn2_action(hand_of_cards, picked_cards, card_turn)
        else:
            action = self._phase2_turn3_action(hand_of_cards, picked_cards, card_turn)

        return action

    def _phase1_turn1_action(self, hand_of_cards: list[Card], card_turn: int):
        if card_turn == 0:
            return self._best_matching_card(hand_of_cards, ("thonar_stance",))
        if card_turn == 1:
            return self._best_matching_card(hand_of_cards, ("dogs_roxy_aoe",))
        if card_turn == 2:
            return self._best_matching_card(hand_of_cards, ("escalin_aoe",))
        if card_turn == 3:
            return self._best_matching_card(hand_of_cards, ("dogs_nasi_heal",))
        return -1

    def _phase1_turn2_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        return self._phase1_simple_turn_action(hand_of_cards, picked_cards, card_turn, scripted_turn=2)

    def _phase1_turn3plus_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        return self._phase1_simple_turn_action(
            hand_of_cards,
            picked_cards,
            card_turn,
            scripted_turn=DogsFloor4BattleStrategy.turn + 1,
        )

    def _phase1_simple_turn_action(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, scripted_turn: int
    ) -> int:
        keep_thonar_gauges = min(2, len(self._thonar_gauge_ids(hand_of_cards)))
        escalin_st_idx = self._best_matching_card(hand_of_cards, ("escalin_st",))
        keep_escalin_st = 1 if escalin_st_idx != -1 and self._played_count(picked_cards, ("escalin_st",)) == 0 else 0

        if card_turn == 0:
            roxy_st_idx = self._best_matching_card_with_ranks(
                hand_of_cards,
                ("dogs_roxy_st",),
                {CardRanks.SILVER, CardRanks.GOLD},
            )
            if roxy_st_idx == -1:
                roxy_st_idx = self._best_matching_card(hand_of_cards, ("dogs_roxy_st",))
            if roxy_st_idx != -1:
                print(f"Phase 1 turn {scripted_turn}: opening with roxy_st.")
                return roxy_st_idx

        if card_turn == 3 and escalin_st_idx != -1:
            print(f"Phase 1 turn {scripted_turn}: closing with escalin_st.")
            return escalin_st_idx

        filler_action = self._phase1_simple_filler_action(
            hand_of_cards,
            keep_nasi_stun=1,
            keep_thonar_gauges=keep_thonar_gauges,
            keep_escalin_st=keep_escalin_st,
        )
        if filler_action != -1:
            print(f"Phase 1 turn {scripted_turn}: spending a low-value filler card while preserving the keepers.")
            return filler_action

        if escalin_st_idx != -1:
            print(f"Phase 1 turn {scripted_turn}: no filler remained, so using escalin_st.")
            return escalin_st_idx

        return -1

    def _phase1_turn2_with_double_gauge_action(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int
    ) -> int:
        if card_turn == 0:
            opener_idx = self._phase1_preferred_turn2_opener(hand_of_cards)
            if opener_idx != -1:
                return opener_idx

        escalin_st_idx = self._best_matching_card(hand_of_cards, ("escalin_st",))
        if card_turn in {1, 2}:
            waste_action = self._phase1_phase3_cleanup_action(
                hand_of_cards,
                keep_nasi_stun=1,
                keep_thonar_gauges=2,
                keep_escalin_st=1 if self._played_count(picked_cards, ("escalin_st",)) == 0 else 0,
            )
            if waste_action != -1:
                print("Phase 1 turn 2: using a waste/setup card while preserving 2 sacred gauges.")
                return waste_action

            if escalin_st_idx != -1:
                filler_action = self._phase1_phase3_cleanup_action(
                    hand_of_cards,
                    keep_nasi_stun=1,
                    keep_thonar_gauges=2,
                    keep_escalin_st=0,
                )
                if filler_action != -1:
                    print("Phase 1 turn 2: sacred gauges are ready, so spending the remaining filler before escalin_st.")
                    return filler_action

        if self._played_count(picked_cards, ("escalin_st",)) == 0:
            if escalin_st_idx != -1 and card_turn in {2, 3}:
                print("Phase 1 turn 2: cashing in escalin_st to move toward Phase 2.")
                return escalin_st_idx

        waste_action = self._phase1_phase3_cleanup_action(
            hand_of_cards,
            keep_nasi_stun=1,
            keep_thonar_gauges=2,
            keep_escalin_st=0,
        )
        if waste_action != -1:
            print("Phase 1 turn 2: forced to throw away another card after securing the sacred setup.")
            return waste_action

        visible_fallback = self._phase1_any_visible_card_action(
            hand_of_cards,
            keep_nasi_stun=1,
            keep_thonar_gauges=2,
            keep_escalin_st=0,
        )
        if visible_fallback != -1:
            print("Phase 1 turn 2: template cleanup found nothing, so using a visible fallback card to avoid looping.")
            return visible_fallback

        return -1

    def _phase1_turn2_without_double_gauge_action(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int
    ) -> int:
        if card_turn == 0:
            opener_idx = self._phase1_preferred_turn2_opener(hand_of_cards)
            if opener_idx != -1:
                print("Phase 1 turn 2: sacred card is still missing, opening with one AOE or roxy_st while stalling.")
                return opener_idx

        waste_action = self._phase1_phase3_cleanup_action(
            hand_of_cards,
            keep_nasi_stun=1,
            keep_thonar_gauges=1,
            keep_escalin_st=1,
        )
        if waste_action != -1:
            print("Phase 1 turn 2: missing the second sacred card, wasting everything except the key keepers.")
            return waste_action

        visible_fallback = self._phase1_any_visible_card_action(
            hand_of_cards,
            keep_nasi_stun=1,
            keep_thonar_gauges=1,
            keep_escalin_st=1,
        )
        if visible_fallback != -1:
            print(
                "Phase 1 turn 2: template cleanup found nothing, so spending a visible non-protected card instead of stalling out."
            )
            return visible_fallback

        if self._played_count(picked_cards, ("escalin_st",)) == 0:
            escalin_st_idx = self._best_matching_card(hand_of_cards, ("escalin_st",))
            if escalin_st_idx != -1:
                print("Phase 1 turn 2: no other option left, spending escalin_st while keeping the stall pieces.")
                return escalin_st_idx

        return -1

    def _phase1_preferred_turn2_opener(self, hand_of_cards: list[Card]) -> int:
        for template_names in [("dogs_roxy_aoe",), ("escalin_aoe",), ("dogs_roxy_st",)]:
            opener_idx = self._best_matching_card(hand_of_cards, template_names)
            if opener_idx != -1:
                return opener_idx
        return -1

    def _phase1_phase3_cleanup_action(
        self,
        hand_of_cards: list[Card],
        keep_nasi_stun: int,
        keep_thonar_gauges: int,
        keep_escalin_st: int,
    ) -> int:
        protected_ids = set()
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("dogs_nasi_stun",), keep_nasi_stun))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("thonar_gauge",), keep_thonar_gauges))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("escalin_st",), keep_escalin_st))

        priority_groups = [
            ("thonar_stance",),
            ("dogs_nasi_heal",),
            ("dogs_nasi_stun",),
            ("thonar_gauge",),
            ("dogs_roxy_st",),
            ("dogs_roxy_aoe",),
            ("dogs_roxy_ult",),
            ("escalin_aoe",),
            ("escalin_ult",),
            ("thonar_ult",),
            ("escalin_st",),
        ]

        for template_names in priority_groups:
            candidate_ids = [
                idx for idx in self._matching_card_ids(hand_of_cards, template_names) if idx not in protected_ids
            ]
            if candidate_ids:
                return self._lowest_rank_rightmost_card_id(hand_of_cards, candidate_ids)

        return -1

    def _phase1_any_visible_card_action(
        self,
        hand_of_cards: list[Card],
        keep_nasi_stun: int,
        keep_thonar_gauges: int,
        keep_escalin_st: int,
    ) -> int:
        protected_ids = set()
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("dogs_nasi_stun",), keep_nasi_stun))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("thonar_gauge",), keep_thonar_gauges))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("escalin_st",), keep_escalin_st))

        visible_ids = [
            idx
            for idx, card in enumerate(hand_of_cards)
            if idx not in protected_ids and card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
        ]
        if not visible_ids:
            return -1

        type_priority = {
            CardTypes.RECOVERY: 0,
            CardTypes.ULTIMATE: 1,
            CardTypes.ATTACK: 2,
            CardTypes.ATTACK_DEBUFF: 3,
        }
        return min(
            visible_ids,
            key=lambda idx: (
                type_priority.get(hand_of_cards[idx].card_type, 9),
                hand_of_cards[idx].card_rank.value,
                -idx,
            ),
        )

    def _phase1_simple_filler_action(
        self,
        hand_of_cards: list[Card],
        keep_nasi_stun: int,
        keep_thonar_gauges: int,
        keep_escalin_st: int,
    ) -> int:
        protected_ids = set()
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("dogs_nasi_stun",), keep_nasi_stun))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("thonar_gauge",), keep_thonar_gauges))
        protected_ids.update(self._phase1_keep_best_ids(hand_of_cards, ("escalin_st",), keep_escalin_st))

        low_value_groups = [
            ("thonar_stance",),
            ("dogs_nasi_heal",),
            ("dogs_nasi_stun",),
            ("thonar_gauge",),
            ("dogs_roxy_st",),
        ]
        for template_names in low_value_groups:
            candidate_ids = [
                idx for idx in self._matching_card_ids(hand_of_cards, template_names) if idx not in protected_ids
            ]
            if candidate_ids:
                return self._lowest_rank_rightmost_card_id(hand_of_cards, candidate_ids)

        return self._phase1_any_visible_card_action(
            hand_of_cards,
            keep_nasi_stun=keep_nasi_stun,
            keep_thonar_gauges=keep_thonar_gauges,
            keep_escalin_st=keep_escalin_st,
        )

    def _phase1_keep_best_ids(self, hand_of_cards: list[Card], template_names: Sequence[str], keep_count: int) -> set[int]:
        if keep_count <= 0:
            return set()
        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        return set(matching_ids[-keep_count:])

    def _lowest_rank_rightmost_card_id(self, hand_of_cards: list[Card], candidate_ids: Sequence[int]) -> int:
        return min(candidate_ids, key=lambda idx: (hand_of_cards[idx].card_rank.value, -idx))

    def _phase2_turn1_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        if card_turn == 0:
            opener = self._best_matching_card_with_ranks(
                hand_of_cards, ("thonar_stance",), {CardRanks.SILVER, CardRanks.GOLD}
            )
            if opener != -1:
                return opener

            opener = self._best_matching_card_with_ranks(
                hand_of_cards, ("dogs_nasi_stun",), {CardRanks.SILVER, CardRanks.GOLD}
            )
            if opener != -1:
                return opener

            opener = self._best_matching_card(hand_of_cards, ("thonar_stance",))
            if opener != -1:
                return opener

            opener = self._best_matching_card(hand_of_cards, ("dogs_nasi_stun",))
            if opener != -1:
                return opener

        for template_names in [
            ("escalin_st",),
            self.ROXY_TEMPLATES,
            ("escalin_aoe",),
            ("thonar_ult",),
            ("escalin_ult",),
        ]:
            card_idx = self._best_nonlethal_phase2_card(hand_of_cards, template_names)
            if card_idx != -1:
                return card_idx

        for template_names in [("thonar_stance",), ("dogs_nasi_stun",)]:
            card_idx = self._best_allowed_card(hand_of_cards, template_names)
            if card_idx != -1:
                return card_idx

        expendable_gauge = self._expendable_thonar_gauge_ids(hand_of_cards)
        if expendable_gauge:
            return self._lowest_expendable_thonar_gauge_id(hand_of_cards)

        move_action = self._phase2_move_action(hand_of_cards)
        if move_action is not None:
            return move_action

        last_resort_move = self._phase2_last_resort_move_action(hand_of_cards)
        if last_resort_move is not None:
            return last_resort_move

        return self._phase2_fallback_action(hand_of_cards, picked_cards)

    def _phase2_turn2_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        if card_turn == 0:
            DogsFloor4BattleStrategy.phase2_use_talent_before_next_play = True
            nasi_heal = self._best_matching_card(hand_of_cards, ("dogs_nasi_heal",))
            if nasi_heal != -1:
                return nasi_heal
            nasi_ult_unlock = self._phase2_nasi_ult_unlock_action(hand_of_cards)
            if nasi_ult_unlock != -1:
                print("Phase 2 turn 2: using nasi_ult as an unlock fallback because normal cards are locked.")
                return nasi_ult_unlock

        for template_names in [
            ("escalin_st",),
            self.ROXY_TEMPLATES,
            ("escalin_aoe",),
            ("thonar_ult",),
            ("escalin_ult",),
            ("thonar_stance",),
            ("dogs_nasi_stun",),
        ]:
            card_idx = self._best_phase2_lethal_setup_card(hand_of_cards, template_names, remaining_turn_slots=4 - card_turn)
            if card_idx != -1:
                return card_idx

        for template_names in [
            ("escalin_st",),
            self.ROXY_TEMPLATES,
            ("escalin_aoe",),
            ("thonar_ult",),
            ("escalin_ult",),
            ("thonar_stance",),
            ("dogs_nasi_stun",),
        ]:
            card_idx = self._best_allowed_card(hand_of_cards, template_names)
            if card_idx != -1:
                return card_idx

        expendable_gauge = self._expendable_thonar_gauge_ids(hand_of_cards)
        if expendable_gauge:
            return self._lowest_expendable_thonar_gauge_id(hand_of_cards)

        move_action = self._phase2_move_action(hand_of_cards)
        if move_action is not None:
            return move_action

        last_resort_move = self._phase2_last_resort_move_action(hand_of_cards)
        if last_resort_move is not None:
            return last_resort_move

        return self._phase2_fallback_action(hand_of_cards, picked_cards)

    def _phase2_turn3_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        if card_turn == 0:
            opener = self._best_matching_card_with_ranks(
                hand_of_cards,
                ("thonar_stance",),
                {CardRanks.SILVER, CardRanks.GOLD},
            )
            if opener != -1:
                return opener

            opener = self._best_matching_card_with_ranks(
                hand_of_cards,
                ("dogs_nasi_stun",),
                {CardRanks.SILVER, CardRanks.GOLD},
            )
            if opener != -1:
                return opener

            for template_names in [("escalin_ult",), ("escalin_aoe",), ("dogs_roxy_aoe",)]:
                card_idx = self._best_allowed_card(hand_of_cards, template_names)
                if card_idx != -1:
                    print("Phase 2 turn 3: right-dog taunt is expected, so prioritizing AOE damage.")
                    return card_idx

            nasi_ult_unlock = self._phase2_nasi_ult_unlock_action(hand_of_cards)
            if nasi_ult_unlock != -1:
                print("Phase 2 turn 3: using nasi_ult as an unlock fallback because normal cards are locked.")
                return nasi_ult_unlock

        for template_names in [
            ("escalin_ult",),
            ("escalin_aoe",),
            ("dogs_roxy_aoe",),
            ("escalin_st",),
            ("dogs_roxy_st",),
            ("dogs_roxy_ult",),
            ("thonar_ult",),
            ("thonar_stance",),
            ("dogs_nasi_stun",),
        ]:
            card_idx = self._best_phase2_lethal_setup_card(hand_of_cards, template_names, remaining_turn_slots=4 - card_turn)
            if card_idx != -1:
                return card_idx

        for template_names in [
            ("escalin_ult",),
            ("escalin_aoe",),
            ("dogs_roxy_aoe",),
            ("escalin_st",),
            ("dogs_roxy_st",),
            ("dogs_roxy_ult",),
            ("thonar_ult",),
            ("thonar_stance",),
            ("dogs_nasi_stun",),
        ]:
            card_idx = self._best_allowed_card(hand_of_cards, template_names)
            if card_idx != -1:
                return card_idx

        move_action = self._phase2_move_action(hand_of_cards)
        if move_action is not None:
            return move_action

        last_resort_move = self._phase2_last_resort_move_action(hand_of_cards)
        if last_resort_move is not None:
            return last_resort_move

        return self._phase2_fallback_action(hand_of_cards, picked_cards)

    def _phase2_fallback_action(self, hand_of_cards: list[Card], picked_cards: list[Card]):
        nasi_ult_unlock = self._phase2_nasi_ult_unlock_action(hand_of_cards)
        if nasi_ult_unlock != -1:
            print("Phase 2 fallback: using nasi_ult as an unlock fallback because normal cards are locked.")
            return nasi_ult_unlock
        move_action = self._phase2_move_action(hand_of_cards)
        if move_action is not None:
            return move_action
        last_resort_move = self._phase2_last_resort_move_action(hand_of_cards)
        if last_resort_move is not None:
            return last_resort_move
        if self._phase2_is_lethal_damage_profile(*self._phase2_damage_counts()):
            expendable_gauge = self._expendable_thonar_gauge_ids(hand_of_cards)
            if expendable_gauge:
                print("Phase 2 fallback: lethal line is already secured, so spending an extra thonar_gauge is acceptable.")
                return self._lowest_expendable_thonar_gauge_id(hand_of_cards)
        visible_card = self._phase2_any_visible_card(hand_of_cards)
        if visible_card != -1:
            print("Phase 2 fallback: no ideal safe action was found, but a visible filler card can still advance the run.")
            return visible_card
        return self._phase2_any_allowed_card(hand_of_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_3")
        DogsFloor4BattleStrategy.phase3_use_talent_before_next_play = False
        DogsFloor4BattleStrategy.phase3_next_target_side = None

        if card_turn == 0:
            print(
                "Phase 3 start-of-turn context -> "
                f"state={DogsFloor4BattleStrategy.phase3_state.value}, "
                f"gauges={DogsFloor4BattleStrategy.phase3_current_gauges}, "
                f"remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
            )

        if card_turn == 0 and DogsFloor4BattleStrategy.phase3_state != DogsFloor4Phase3State.TRIGGER_GIMMICK_1:
            nasi_ult = self._best_matching_card(hand_of_cards, ("dogs_nasi_ult",))
            if nasi_ult != -1:
                print("Phase 3 priority: nasi_ult is available, so using it as the first card.")
                return nasi_ult

        if DogsFloor4BattleStrategy.phase3_state == DogsFloor4Phase3State.STALL_FOR_GAUGE:
            action = self._phase3_stall_action(hand_of_cards, picked_cards, card_turn)
        elif DogsFloor4BattleStrategy.phase3_state == DogsFloor4Phase3State.TRIGGER_GIMMICK_1:
            action = self._phase3_trigger_action(hand_of_cards, picked_cards, card_turn)
        else:
            action = self._phase3_kill_action(hand_of_cards, picked_cards, card_turn)

        return action

    def observe_phase3_turn_start(self, screenshot, hand_of_cards: list[Card]):
        if "phase_3" not in DogsFloor4BattleStrategy._phase_initialized:
            DogsFloor4BattleStrategy._phase_initialized.add("phase_3")
            DogsFloor4BattleStrategy.turn = 0
            DogsFloor4BattleStrategy._reset_phase3_state()
            print("Phase 3 turn-start observer initialized fresh phase 3 state.")

        if DogsFloor4BattleStrategy.phase3_observed_turn == DogsFloor4BattleStrategy.turn:
            return

        current_gauges = dict(DogsFloor4BattleStrategy.phase3_next_turn_gauges)
        reset_applied = {"left": False, "right": False}
        for side in ("left", "right"):
            if DogsFloor4BattleStrategy.phase3_pending_gauge_reset[side]:
                current_gauges[side] = 0
                DogsFloor4BattleStrategy.phase3_pending_gauge_reset[side] = False
                reset_applied[side] = True

        left_region = crop_image(
            screenshot,
            self.PHASE3_LEFT_TOP_LEFT,
            self.PHASE3_LEFT_BOTTOM_RIGHT,
        )
        right_region = crop_image(
            screenshot,
            self.PHASE3_RIGHT_TOP_LEFT,
            self.PHASE3_RIGHT_BOTTOM_RIGHT,
        )
        left_cards = self._detect_phase3_dog_cards(left_region, side="left")
        right_cards = self._detect_phase3_dog_cards(right_region, side="right")
        left_ult_seen = bool(find(vio.dogs_ult, left_region, threshold=0.8))
        right_ult_seen = bool(find(vio.dogs_ult, right_region, threshold=0.8))

        if DogsFloor4BattleStrategy.phase3_gimmick1_completed:
            if not left_cards:
                self._phase3_mark_side_dead(
                    "left",
                    "Phase 3 observation inferred that the left dog is dead because no visible dog cards were found in its area.",
                )
            if not right_cards:
                self._phase3_mark_side_dead(
                    "right",
                    "Phase 3 observation inferred that the right dog is dead because no visible dog cards were found in its area.",
                )
        for side in DogsFloor4BattleStrategy.phase3_dead_sides:
            current_gauges[side] = 0

        DogsFloor4BattleStrategy.phase3_current_gauges = current_gauges
        DogsFloor4BattleStrategy.phase3_last_seen_cards = {
            "left": left_cards,
            "right": right_cards,
        }
        DogsFloor4BattleStrategy.phase3_observed_action_totals["left"] += len(left_cards)
        DogsFloor4BattleStrategy.phase3_observed_action_totals["right"] += len(right_cards)
        DogsFloor4BattleStrategy.phase3_next_turn_gauges = {
            "left": (
                0
                if "left" in DogsFloor4BattleStrategy.phase3_dead_sides
                else min(self.PHASE3_MAX_DOG_GAUGE, current_gauges["left"] + len(left_cards))
            ),
            "right": (
                0
                if "right" in DogsFloor4BattleStrategy.phase3_dead_sides
                else min(self.PHASE3_MAX_DOG_GAUGE, current_gauges["right"] + len(right_cards))
            ),
        }
        DogsFloor4BattleStrategy.phase3_pending_gauge_reset["left"] = left_ult_seen and not reset_applied["left"]
        DogsFloor4BattleStrategy.phase3_pending_gauge_reset["right"] = right_ult_seen and not reset_applied["right"]
        DogsFloor4BattleStrategy.phase3_observed_turn = DogsFloor4BattleStrategy.turn

        detected_turn = self._phase3_detect_turn_from_talent(screenshot)
        DogsFloor4BattleStrategy.phase3_detected_stage_turn = detected_turn
        if detected_turn is not None:
            print(f"Phase 3 turn marker -> escalin_talent indicates setup turn {detected_turn}.")

        print(
            "Phase 3 dog gauge observation -> "
            f"left cards={left_cards}, gauge now={current_gauges['left']}, next={DogsFloor4BattleStrategy.phase3_next_turn_gauges['left']}; "
            f"right cards={right_cards}, gauge now={current_gauges['right']}, next={DogsFloor4BattleStrategy.phase3_next_turn_gauges['right']}; "
            f"ult markers left={left_ult_seen}, right={right_ult_seen}; "
            f"observed action totals={DogsFloor4BattleStrategy.phase3_observed_action_totals}"
        )

        self._update_phase3_state(hand_of_cards)

    def _phase3_detect_turn_from_talent(self, screenshot) -> int | None:
        if find(vio.dogs_escalin_talent_min2, screenshot, threshold=0.75):
            return 1
        if find(vio.dogs_escalin_talent_min1, screenshot, threshold=0.75):
            return 2
        if find(vio.dogs_escalin_talent, screenshot, threshold=0.75):
            return 3
        return None

    def _phase3_activate_trigger_state(self):
        DogsFloor4BattleStrategy.phase3_trigger_turn_active = True
        DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used = set()
        DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult = False
        DogsFloor4BattleStrategy.phase3_trigger_sequence = None
        DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = 0

    def handle_phase3_turn_end(self):
        if not DogsFloor4BattleStrategy.phase3_trigger_turn_active:
            return

        if {"left", "right"}.issubset(DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used):
            DogsFloor4BattleStrategy.phase3_gimmick1_completed = True
            DogsFloor4BattleStrategy.phase3_state = DogsFloor4Phase3State.KILL_BOTH_DOGS
            print("Phase 3 gimmick 1 completed. Switching to KILL_BOTH_DOGS.")
        else:
            print(
                "Phase 3 trigger turn ended without both gauge removals. "
                f"Observed targets={DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used}. Returning to stall."
            )
            DogsFloor4BattleStrategy.phase3_state = DogsFloor4Phase3State.STALL_FOR_GAUGE

        DogsFloor4BattleStrategy.phase3_trigger_turn_active = False
        DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used = set()
        DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult = False
        DogsFloor4BattleStrategy.phase3_trigger_sequence = None
        DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = 0

    def _update_phase3_state(self, hand_of_cards: list[Card]):
        previous_state = DogsFloor4BattleStrategy.phase3_state
        gauges = DogsFloor4BattleStrategy.phase3_current_gauges
        both_gauges_ready = gauges["left"] >= 3 and gauges["right"] >= 3
        observed_actions = DogsFloor4BattleStrategy.phase3_observed_action_totals
        detected_turn = DogsFloor4BattleStrategy.phase3_detected_stage_turn
        has_thonar_card = bool(self._matching_card_ids(hand_of_cards, self.THONAR_TEMPLATES))
        DogsFloor4BattleStrategy.phase3_missing_thonar_reset_pending = False
        heuristic_ready = (
            DogsFloor4BattleStrategy.turn >= self.PHASE3_TRIGGER_HEURISTIC_TURN
            and min(observed_actions.values()) >= self.PHASE3_TRIGGER_HEURISTIC_MIN_OBSERVED_ACTIONS
        )
        gold_gauges = self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})
        gold_gauges_ready = DogsFloor4BattleStrategy.phase3_gold_gauges_locked_in or len(gold_gauges) >= 2

        if DogsFloor4BattleStrategy.phase3_gimmick1_completed:
            new_state = DogsFloor4Phase3State.KILL_BOTH_DOGS
            reason = "gimmick 1 already completed"
        elif detected_turn in {1, 2}:
            new_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
            reason = f"escalin_talent marker confirmed phase 3 setup turn {detected_turn}"
        elif detected_turn == 3 and not has_thonar_card:
            new_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
            DogsFloor4BattleStrategy.phase3_missing_thonar_reset_pending = True
            reason = "escalin_talent marker confirmed phase 3 turn 3, but no Thonar card was found"
        elif detected_turn == 3:
            new_state = DogsFloor4Phase3State.TRIGGER_GIMMICK_1
            reason = "escalin_talent marker confirmed phase 3 turn 3 / Stage 2"
            self._phase3_activate_trigger_state()
        elif both_gauges_ready and gold_gauges_ready:
            new_state = DogsFloor4Phase3State.TRIGGER_GIMMICK_1
            reason = "both dogs are at >=3 ult gauge and 2 gold thonar_gauge cards are available"
            self._phase3_activate_trigger_state()
        elif heuristic_ready and gold_gauges_ready:
            new_state = DogsFloor4Phase3State.TRIGGER_GIMMICK_1
            reason = (
                "turn-3 heuristic triggered: both dogs have shown at least 2 total observed actions across the setup turns, "
                "so we are forcing the Stage 2 sequence with 2 gold thonar_gauge cards available"
            )
            self._phase3_activate_trigger_state()
        elif both_gauges_ready:
            new_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
            reason = f"both dogs are ready, but only {len(gold_gauges)} gold thonar_gauge card(s) are available"
        else:
            new_state = DogsFloor4Phase3State.STALL_FOR_GAUGE
            reason = "waiting for both dogs to reach >=3 ult gauge"

        DogsFloor4BattleStrategy.phase3_state = new_state
        print(
            "Phase 3 sub-state update -> "
            f"{previous_state.value} -> {new_state.value}. Reason: {reason}. "
            f"Current gauges: {DogsFloor4BattleStrategy.phase3_current_gauges}. "
            f"Observed actions: {DogsFloor4BattleStrategy.phase3_observed_action_totals}"
        )

    def _phase3_stall_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        if DogsFloor4BattleStrategy.turn == 0 and card_turn == 0:
            nasi_ult = self._best_matching_card(hand_of_cards, ("dogs_nasi_ult",))
            if nasi_ult != -1:
                print("Phase 3 stall: Turn 1 hard rule -> using nasi_ult first.")
                return nasi_ult

        if DogsFloor4BattleStrategy.turn == 0:
            low_value_card = self._phase3_low_value_play_action(hand_of_cards)
            if low_value_card != -1:
                print("Phase 3 stall: Turn 1 spending a low-value card to cycle the hand.")
                return low_value_card

        gauge_balance_action = self._phase3_stall_gauge_balance_action(hand_of_cards)
        if gauge_balance_action != -1:
            return gauge_balance_action

        if (
            DogsFloor4BattleStrategy.phase3_current_gauges["left"] >= 3
            and DogsFloor4BattleStrategy.phase3_current_gauges["right"] >= 3
            and len(self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})) < 2
        ):
            move_action = self._move_card_once(hand_of_cards, ("thonar_gauge",))
            if move_action is not None:
                print("Phase 3 stall: gauges are ready but 2 gold thonar_gauge cards are not. Merging/repositioning gauge cards.")
                return move_action

        move_action = self._phase3_preserved_nasi_move_action(hand_of_cards)
        if move_action is not None:
            print("Phase 3 stall: moving a preserved nasi card to rebuild toward nasi_ult again.")
            return move_action

        low_value_card = self._phase3_low_value_play_action(hand_of_cards)
        if low_value_card != -1:
            print("Phase 3 stall: using a low-value card to rebuild and cycle draws.")
            return low_value_card

        for template_names in [self.NASI_NON_ULT_TEMPLATES, ("thonar_stance",)]:
            merge_action = self._find_merge_move(hand_of_cards, template_names)
            if merge_action is not None:
                print(f"Phase 3 stall: using merge action for setup with {template_names}.")
                return merge_action

        move_action = self._move_card_once(hand_of_cards, ("thonar_gauge",))
        if move_action is not None:
            print("Phase 3 stall: moving thonar_gauge as a last-resort setup action.")
            return move_action

        for template_names in [
            self.NASI_TEMPLATES,
            ("thonar_stance",),
            ("escalin_st",),
            ("escalin_aoe",),
            ("dogs_roxy_st",),
            ("dogs_roxy_aoe",),
            ("escalin_ult",),
            ("dogs_roxy_ult",),
            ("thonar_ult",),
        ]:
            move_action = self._move_card_once(hand_of_cards, template_names)
            if move_action is not None:
                print(f"Phase 3 stall: using a reposition move with {template_names} instead of spending damage.")
                return move_action

        print("Phase 3 stall: no safe setup move was found, falling back to any non-gauge card.")
        return self._phase3_any_non_gauge_card(hand_of_cards)

    def _phase3_low_value_play_action(self, hand_of_cards: list[Card]) -> int:
        nasi_ult = self._best_matching_card(hand_of_cards, ("dogs_nasi_ult",))
        if nasi_ult != -1:
            return nasi_ult

        thonar_stance = self._best_matching_card(hand_of_cards, ("thonar_stance",))
        if thonar_stance != -1:
            return thonar_stance

        nasi_ids = self._matching_card_ids(hand_of_cards, self.NASI_NON_ULT_TEMPLATES)
        if len(nasi_ids) > 1:
            preserved_nasi_id = nasi_ids[-1]
            expendable_nasi_ids = [idx for idx in nasi_ids if idx != preserved_nasi_id]
            if expendable_nasi_ids:
                return self._lowest_rank_rightmost_card_id(hand_of_cards, expendable_nasi_ids)
        return -1

    def _phase3_preserved_nasi_move_action(self, hand_of_cards: list[Card]) -> list[int] | None:
        nasi_ids = self._matching_card_ids(hand_of_cards, self.NASI_NON_ULT_TEMPLATES)
        if not nasi_ids:
            return None

        preserved_nasi_id = nasi_ids[-1]
        target_idx = preserved_nasi_id + 1 if preserved_nasi_id < len(hand_of_cards) - 1 else preserved_nasi_id - 1
        if target_idx < 0 or target_idx == preserved_nasi_id:
            return None

        return [preserved_nasi_id, target_idx]

    def _phase3_stall_gauge_balance_action(self, hand_of_cards: list[Card]) -> int:
        gauges = DogsFloor4BattleStrategy.phase3_current_gauges
        gauge_delta = abs(gauges["left"] - gauges["right"])
        if gauge_delta < self.PHASE3_GAUGE_DISPARITY_THRESHOLD:
            return -1

        gold_gauge_ids = self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})
        if len(gold_gauge_ids) < 2:
            return -1

        expendable_non_gold_gauges = self._phase3_expendable_non_gold_thonar_gauge_ids(hand_of_cards)
        if not expendable_non_gold_gauges:
            return -1

        if DogsFloor4BattleStrategy.turn == 1:
            target_side = "right"
        else:
            target_side = "left" if gauges["left"] > gauges["right"] else "right"
        chosen_idx = self._lowest_rank_rightmost_card_id(hand_of_cards, expendable_non_gold_gauges)
        DogsFloor4BattleStrategy.phase3_next_target_side = target_side
        print(
            "Phase 3 stall: using an expendable non-gold thonar_gauge to reduce ult-gauge disparity -> "
            f"target={target_side}, gauges={gauges}"
        )
        return chosen_idx

    def _phase3_expendable_non_gold_thonar_gauge_ids(self, hand_of_cards: list[Card]) -> list[int]:
        gauge_ids = self._thonar_gauge_ids(hand_of_cards)
        non_gold_gauge_ids = [idx for idx in gauge_ids if hand_of_cards[idx].card_rank != CardRanks.GOLD]
        if len(self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})) < 2:
            return []
        return non_gold_gauge_ids

    def _phase3_thonar_gauge_reduction(self, card: Card) -> int:
        if card.card_rank == CardRanks.GOLD:
            return 3
        if card.card_rank in {CardRanks.BRONZE, CardRanks.SILVER}:
            return 1
        return 0

    def _phase3_is_gimmick_damage_active(self) -> bool:
        return DogsFloor4BattleStrategy.phase3_gimmick1_completed or {"left", "right"}.issubset(
            DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used
        )

    def _phase3_damage_value(self, target_side: str, base_damage: int, add_roxy_bonus: bool) -> int:
        return base_damage + (self.PHASE3_ROXY_PASSIVE_BONUS_DAMAGE if add_roxy_bonus else 0)

    def _phase3_apply_flat_damage(self, target_side: str, amount: int):
        if target_side not in {"left", "right"} or amount <= 0:
            return

        DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] = max(
            0,
            DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] - amount,
        )
        DogsFloor4BattleStrategy.phase3_damage_applied["left"] = (
            self.PHASE3_LEFT_HP - DogsFloor4BattleStrategy.phase3_remaining_hp["left"]
        )
        DogsFloor4BattleStrategy.phase3_damage_applied["right"] = (
            self.PHASE3_RIGHT_HP - DogsFloor4BattleStrategy.phase3_remaining_hp["right"]
        )

    def _apply_phase3_gauge_reduction(self, target_side: str, reduction: int):
        if reduction <= 0:
            return

        DogsFloor4BattleStrategy.phase3_current_gauges[target_side] = max(
            0,
            DogsFloor4BattleStrategy.phase3_current_gauges[target_side] - reduction,
        )
        DogsFloor4BattleStrategy.phase3_next_turn_gauges[target_side] = max(
            0,
            DogsFloor4BattleStrategy.phase3_next_turn_gauges[target_side] - reduction,
        )
        print(
            "Phase 3 gauge update after thonar_gauge -> "
            f"target={target_side}, reduction={reduction}, "
            f"current={DogsFloor4BattleStrategy.phase3_current_gauges}, "
            f"next={DogsFloor4BattleStrategy.phase3_next_turn_gauges}"
        )

    def _phase3_trigger_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        gold_gauge_ids = self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})
        any_gauge_idx = self._best_matching_card(hand_of_cards, ("thonar_gauge",))
        nasi_ult_idx = self._best_matching_card(hand_of_cards, ("dogs_nasi_ult",))
        escalin_ult_idx = self._best_matching_card(hand_of_cards, ("escalin_ult",))
        trigger_sequence = DogsFloor4BattleStrategy.phase3_trigger_sequence

        if card_turn == 0:
            roxy_st_idx = self._best_matching_card_with_ranks(
                hand_of_cards,
                ("dogs_roxy_st",),
                {CardRanks.SILVER, CardRanks.GOLD},
            )
            if roxy_st_idx != -1:
                DogsFloor4BattleStrategy.phase3_trigger_sequence = "roxy_opener"
                DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult = False
                DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = 2
                DogsFloor4BattleStrategy.phase3_next_target_side = "right"
                print(
                    "Phase 3 trigger: alternate sequence -> opening with "
                    f"{hand_of_cards[roxy_st_idx].card_rank.name.lower()} roxy_st on the right dog."
                )
                return roxy_st_idx

            DogsFloor4BattleStrategy.phase3_use_talent_before_next_play = True
            print("Phase 3 trigger: activating talent before the first card.")
            if nasi_ult_idx != -1:
                DogsFloor4BattleStrategy.phase3_trigger_sequence = "standard_with_nasi"
                DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult = True
                DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = 2
                print("Phase 3 trigger: nasi_ult is available, using the nasi_ult sequence.")
                return nasi_ult_idx

            if gold_gauge_ids or any_gauge_idx != -1:
                DogsFloor4BattleStrategy.phase3_trigger_sequence = "standard_no_nasi"
                DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult = False
                DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = 2
                print("Phase 3 trigger: nasi_ult is not available, starting with the available right-side thonar_gauge.")
                return self._phase3_pick_trigger_gauge_action(
                    hand_of_cards,
                    target_side="right",
                    step_label="Phase 3 trigger first gold-gauge step",
                )
            print("Phase 3 trigger: expected a gold thonar_gauge for the right dog, but none was found.")
            return -1

        if trigger_sequence == "roxy_opener":
            if card_turn == 1:
                print("Phase 3 trigger: alternate sequence -> select right dog, use 1 gold thonar_gauge.")
                return self._phase3_pick_trigger_gauge_action(
                    hand_of_cards,
                    target_side="right",
                    step_label="Phase 3 trigger alternate right gold-gauge step",
                )
            if card_turn == 2:
                print("Phase 3 trigger: alternate sequence -> select left dog, use the other gold thonar_gauge.")
                return self._phase3_pick_trigger_gauge_action(
                    hand_of_cards,
                    target_side="left",
                    step_label="Phase 3 trigger alternate left gold-gauge step",
                )
            if card_turn == 3:
                if nasi_ult_idx != -1:
                    print("Phase 3 trigger: alternate sequence -> closing with nasi_ult.")
                    return nasi_ult_idx
                if escalin_ult_idx != -1:
                    print("Phase 3 trigger: alternate sequence -> preferring escalin_ult before other AOE options.")
                    return escalin_ult_idx
                return self._phase3_select_damage_action(
                    hand_of_cards,
                    remaining_turn_slots=1,
                    prefer_aoe=True,
                    reason="Phase 3 trigger alternate final slot",
                    prefer_escalin_st_target_side="left",
                )
            return -1

        if trigger_sequence == "standard_with_nasi" or (
            trigger_sequence is None and DogsFloor4BattleStrategy.phase3_trigger_used_nasi_ult
        ):
            if card_turn == 1:
                print("Phase 3 trigger: explicit sequence -> select right dog, use 1 gold thonar_gauge.")
                return self._phase3_pick_trigger_gauge_action(
                    hand_of_cards,
                    target_side="right",
                    step_label="Phase 3 trigger explicit right gold-gauge step",
                )
            if card_turn == 2:
                print("Phase 3 trigger: explicit sequence -> select left dog, use the other gold thonar_gauge.")
                return self._phase3_pick_trigger_gauge_action(
                    hand_of_cards,
                    target_side="left",
                    step_label="Phase 3 trigger explicit left gold-gauge step",
                )
            if card_turn == 3:
                if escalin_ult_idx != -1:
                    print("Phase 3 trigger: final slot -> preferring escalin_ult before other AOE options.")
                    return escalin_ult_idx
                return self._phase3_select_damage_action(
                    hand_of_cards,
                    remaining_turn_slots=1,
                    prefer_aoe=True,
                    reason="Phase 3 trigger final slot",
                    prefer_escalin_st_target_side="left",
                )
            return -1

        if card_turn == 1:
            print("Phase 3 trigger: explicit sequence -> select left dog, use the other gold thonar_gauge.")
            return self._phase3_pick_trigger_gauge_action(
                hand_of_cards,
                target_side="left",
                step_label="Phase 3 trigger explicit left gold-gauge step",
            )

        if card_turn in {2, 3}:
            if escalin_ult_idx != -1:
                print("Phase 3 trigger: remaining damage slot -> preferring escalin_ult before other AOE options.")
                return escalin_ult_idx
            return self._phase3_select_damage_action(
                hand_of_cards,
                remaining_turn_slots=max(1, 4 - card_turn),
                prefer_aoe=True,
                reason="Phase 3 trigger remaining damage slot",
                prefer_escalin_st_target_side="left",
            )

        return -1

    def _phase3_pick_trigger_gauge_action(self, hand_of_cards: list[Card], target_side: str, step_label: str) -> int:
        gold_gauge_ids = self._thonar_gauge_ids_with_ranks(hand_of_cards, {CardRanks.GOLD})
        if gold_gauge_ids:
            DogsFloor4BattleStrategy.phase3_next_target_side = target_side
            return gold_gauge_ids[-1]

        print(
            f"{step_label}: expected a remaining trigger thonar_gauge for the {target_side} dog, "
            "but no gold thonar_gauge was detected on this reread."
        )
        return -1

    def _phase3_kill_action(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        return self._phase3_select_damage_action(
            hand_of_cards,
            remaining_turn_slots=max(1, 4 - card_turn),
            prefer_aoe=True,
            reason="Phase 3 kill planning",
        )

    def _phase3_any_non_gauge_card(self, hand_of_cards: list[Card]) -> int:
        preserved_nasi_ids = set()
        nasi_ids = self._matching_card_ids(hand_of_cards, self.NASI_NON_ULT_TEMPLATES)
        if nasi_ids:
            preserved_nasi_ids.add(nasi_ids[-1])

        for idx, card in reversed(list(enumerate(hand_of_cards))):
            if card.card_type in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND):
                continue
            if idx in preserved_nasi_ids:
                continue
            if self._card_matches_any(card, ("thonar_gauge",)):
                continue
            return idx
        return -1

    def _phase3_select_damage_action(
        self,
        hand_of_cards: list[Card],
        remaining_turn_slots: int,
        prefer_aoe: bool,
        reason: str,
        prefer_escalin_st_target_side: str | None = None,
    ) -> int:
        damage_options = self._phase3_damage_options(
            hand_of_cards,
            prefer_escalin_st_target_side=prefer_escalin_st_target_side,
        )
        if not damage_options:
            print(f"{reason}: no huge-damage cards found, falling back to any non-gauge card.")
            return self._phase3_any_non_gauge_card(hand_of_cards)

        guaranteed_options = []
        for option in damage_options:
            simulated_hp = self._phase3_simulate_option(DogsFloor4BattleStrategy.phase3_remaining_hp, option)
            remaining_options = [other_option for other_option in damage_options if other_option["idx"] != option["idx"]]
            if self._phase3_can_finish_both(simulated_hp, remaining_options, remaining_turn_slots - 1):
                guaranteed_options.append((option, simulated_hp))

        escalin_ult_guaranteed = [item for item in guaranteed_options if item[0]["template_name"] == "escalin_ult"]
        if escalin_ult_guaranteed:
            chosen_option, simulated_hp = max(
                escalin_ult_guaranteed,
                key=lambda item: self._phase3_guaranteed_option_score(item[0], item[1], prefer_aoe=prefer_aoe),
            )
            print(
                f"{reason}: preferring escalin_ult over the other AOE finishers. "
                f"Projected HP after use would be {simulated_hp}."
            )
            DogsFloor4BattleStrategy.phase3_next_target_side = chosen_option["target_side"]
            return chosen_option["idx"]

        if guaranteed_options:
            chosen_option, simulated_hp = max(
                guaranteed_options,
                key=lambda item: self._phase3_guaranteed_option_score(item[0], item[1], prefer_aoe=prefer_aoe),
            )
            print(
                f"{reason}: found a guaranteed kill line with {chosen_option['template_name']} "
                f"target={chosen_option['target_side']}. Remaining HP after use would be {simulated_hp}."
            )
        else:
            scored_options = [
                (
                    option,
                    self._phase3_simulate_option(DogsFloor4BattleStrategy.phase3_remaining_hp, option),
                )
                for option in damage_options
            ]
            chosen_option, simulated_hp = max(
                scored_options,
                key=lambda item: self._phase3_fallback_option_score(item[0], item[1], prefer_aoe=prefer_aoe),
            )
            escalin_ult_scored = [item for item in scored_options if item[0]["template_name"] == "escalin_ult"]
            if escalin_ult_scored:
                chosen_option, simulated_hp = max(
                    escalin_ult_scored,
                    key=lambda item: self._phase3_fallback_option_score(item[0], item[1], prefer_aoe=prefer_aoe),
                )
                print(
                    f"{reason}: preferring escalin_ult over the other AOE finishers. "
                    f"Projected HP after use would be {simulated_hp}."
                )
                DogsFloor4BattleStrategy.phase3_next_target_side = chosen_option["target_side"]
                return chosen_option["idx"]
            print(
                f"{reason}: no guaranteed kill line. Best fallback is {chosen_option['template_name']} "
                f"target={chosen_option['target_side']} -> projected HP {simulated_hp}."
            )

        DogsFloor4BattleStrategy.phase3_next_target_side = chosen_option["target_side"]
        if chosen_option["template_name"] == "escalin_st":
            print(
                "Phase 3 escalin_st target selection -> "
                f"{chosen_option['target_side']} (reason: maximize same-turn double-kill odds)."
            )
        return chosen_option["idx"]

    def _phase3_damage_options(
        self,
        hand_of_cards: list[Card],
        prefer_escalin_st_target_side: str | None = None,
    ) -> list[dict]:
        options = []
        alive_target_sides = self._phase3_alive_target_sides()
        for idx, card in enumerate(hand_of_cards):
            if card.card_type in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND):
                continue

            if self._card_matches_any(card, ("escalin_ult", "escalin_aoe", "dogs_roxy_aoe")):
                options.append(
                    {
                        "idx": idx,
                        "template_name": self._phase3_template_name(card),
                        "target_side": None,
                        "kind": "aoe",
                    }
                )
                continue

            if self._card_matches_any(card, ("escalin_st",)):
                target_sides = alive_target_sides
                if prefer_escalin_st_target_side in target_sides:
                    target_sides = [prefer_escalin_st_target_side]
                for target_side in target_sides:
                    options.append(
                        {
                            "idx": idx,
                            "template_name": "escalin_st",
                            "target_side": target_side,
                            "kind": "escalin_st",
                        }
                    )
                continue

            if self._card_matches_any(card, ("dogs_roxy_st", "dogs_roxy_ult", "thonar_ult")):
                for target_side in alive_target_sides:
                    options.append(
                        {
                            "idx": idx,
                            "template_name": self._phase3_template_name(card),
                            "target_side": target_side,
                            "kind": "single_target",
                        }
                    )

        return options

    def _phase3_alive_target_sides(self) -> list[str]:
        alive_sides = [
            side
            for side in ("left", "right")
            if side not in DogsFloor4BattleStrategy.phase3_dead_sides
            and DogsFloor4BattleStrategy.phase3_remaining_hp[side] > 0
        ]
        return alive_sides or ["left", "right"]

    def _phase3_template_name(self, card: Card) -> str:
        for template_name in (
            "escalin_ult",
            "escalin_aoe",
            "escalin_st",
            "dogs_roxy_aoe",
            "dogs_roxy_st",
            "dogs_roxy_ult",
            "thonar_ult",
        ):
            if self._card_matches_any(card, (template_name,)):
                return template_name
        return "unknown"

    def _phase3_guaranteed_option_score(self, option: dict, simulated_hp: dict, prefer_aoe: bool) -> tuple:
        template_priority = self._phase3_template_priority(option["template_name"])
        aoe_bonus = 1 if prefer_aoe and option["kind"] == "aoe" else 0
        return (
            aoe_bonus,
            template_priority,
            -sum(simulated_hp.values()),
            -max(simulated_hp.values()),
        )

    def _phase3_fallback_option_score(self, option: dict, simulated_hp: dict, prefer_aoe: bool) -> tuple:
        template_priority = self._phase3_template_priority(option["template_name"])
        aoe_bonus = 1 if prefer_aoe and option["kind"] == "aoe" else 0
        return (
            -sum(simulated_hp.values()),
            -max(simulated_hp.values()),
            aoe_bonus,
            template_priority,
        )

    def _phase3_template_priority(self, template_name: str) -> int:
        priorities = {
            "escalin_ult": 7,
            "escalin_aoe": 6,
            "dogs_roxy_aoe": 6,
            "escalin_st": 5,
            "dogs_roxy_st": 4,
            "dogs_roxy_ult": 3,
            "thonar_ult": 2,
            "unknown": 0,
        }
        return priorities.get(template_name, 0)

    def _phase3_can_finish_both(self, remaining_hp: dict, options: list[dict], remaining_slots: int) -> bool:
        if remaining_hp["left"] <= 0 and remaining_hp["right"] <= 0:
            return True
        if remaining_slots <= 0 or not options:
            return False

        for option in options:
            next_remaining_hp = self._phase3_simulate_option(remaining_hp, option)
            next_options = [other_option for other_option in options if other_option["idx"] != option["idx"]]
            if self._phase3_can_finish_both(next_remaining_hp, next_options, remaining_slots - 1):
                return True
        return False

    def _phase3_simulate_option(self, remaining_hp: dict, option: dict) -> dict:
        updated_hp = dict(remaining_hp)
        if option["kind"] == "aoe":
            if option["template_name"] == "escalin_ult":
                left_damage = self.PHASE3_DAMAGE_CAP["left"]
                right_damage = self.PHASE3_DAMAGE_CAP["right"]
            else:
                left_damage = self._phase3_damage_value("left", self.PHASE3_DAMAGE_CAP["left"], add_roxy_bonus=True)
                right_damage = self._phase3_damage_value("right", self.PHASE3_DAMAGE_CAP["right"], add_roxy_bonus=True)
            updated_hp["left"] = max(0, updated_hp["left"] - left_damage)
            updated_hp["right"] = max(0, updated_hp["right"] - right_damage)
            return updated_hp

        target_side = option["target_side"]
        other_side = "right" if target_side == "left" else "left"

        if option["kind"] == "single_target":
            base_damage = self.PHASE3_DAMAGE_CAP[target_side]
            add_roxy_bonus = option["template_name"] != "thonar_ult"
            updated_hp[target_side] = max(
                0,
                updated_hp[target_side] - self._phase3_damage_value(target_side, base_damage, add_roxy_bonus),
            )
            return updated_hp

        if option["kind"] == "escalin_st":
            base_damage = self.PHASE3_DAMAGE_CAP[target_side]
            if updated_hp[target_side] <= base_damage:
                spill_damage = base_damage * 0.7
                kill_bonus_damage = (base_damage + spill_damage) * 0.5
                updated_hp[target_side] = 0
                updated_hp[other_side] = max(0, updated_hp[other_side] - spill_damage - kill_bonus_damage)
            else:
                updated_hp[target_side] = max(
                    0,
                    updated_hp[target_side] - self.PHASE3_ESCALIN_ST_TOTAL_DAMAGE[target_side],
                )
            updated_hp[target_side] = max(0, updated_hp[target_side] - self.PHASE3_ROXY_PASSIVE_BONUS_DAMAGE)
            return updated_hp

        return updated_hp

    def _pixel_similarity(self, region, template, x: int, y: int) -> float:
        template_height, template_width = template.shape[:2]
        patch = region[y : y + template_height, x : x + template_width]
        if patch.shape != template.shape:
            return 0.0

        absolute_diff = np.abs(patch.astype(np.float32) - template.astype(np.float32))
        return 1.0 - float(np.mean(absolute_diff) / 255.0)

    def _collect_phase3_template_candidates(
        self,
        region,
        template_map: Sequence[tuple[str, object]],
        threshold=0.7,
        max_candidates_per_template=12,
    ) -> list[dict]:
        candidates = []
        for label, vision_image in template_map:
            template = vision_image.needle_img
            if template is None:
                continue

            result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
            match_locations = np.where(result >= threshold)
            template_height, template_width = template.shape[:2]

            raw_candidates = []
            for x, y in zip(match_locations[1], match_locations[0]):
                match_score = float(result[y, x])
                pixel_score = self._pixel_similarity(region, template, x, y)
                combined_score = (match_score * 0.65) + (pixel_score * 0.35)
                raw_candidates.append(
                    {
                        "label": label,
                        "x": int(x),
                        "y": int(y),
                        "w": int(template_width),
                        "h": int(template_height),
                        "combined_score": combined_score,
                    }
                )

            raw_candidates.sort(key=lambda candidate: candidate["combined_score"], reverse=True)
            kept_candidates = []
            for candidate in raw_candidates:
                if len(kept_candidates) >= max_candidates_per_template:
                    break
                if any(
                    abs(candidate["x"] - existing["x"]) <= max(4, candidate["w"] // 3)
                    and abs(candidate["y"] - existing["y"]) <= max(4, candidate["h"] * 2)
                    for existing in kept_candidates
                ):
                    continue
                kept_candidates.append(candidate)

            candidates.extend(kept_candidates)

        return candidates

    def _phase3_same_card_position(self, candidate_a: dict, candidate_b: dict) -> bool:
        center_x_a = candidate_a["x"] + (candidate_a["w"] / 2)
        center_x_b = candidate_b["x"] + (candidate_b["w"] / 2)
        center_y_a = candidate_a["y"] + (candidate_a["h"] / 2)
        center_y_b = candidate_b["y"] + (candidate_b["h"] / 2)
        overlap_width = min(candidate_a["x"] + candidate_a["w"], candidate_b["x"] + candidate_b["w"]) - max(
            candidate_a["x"],
            candidate_b["x"],
        )

        return (
            abs(center_x_a - center_x_b) <= max(10, min(candidate_a["w"], candidate_b["w"]) * 0.6)
            and abs(center_y_a - center_y_b) <= max(8, max(candidate_a["h"], candidate_b["h"]) * 2.5)
        ) or overlap_width >= min(candidate_a["w"], candidate_b["w"]) * 0.45

    def _detect_phase3_dog_cards(self, region, side: str) -> list[str]:
        if side == "left":
            template_map = (
                ("atk", vio.dogs_atk_bronze),
                ("atk", vio.dogs_atk_silver),
                ("left_debuff1", vio.dogs_left_debuff1),
                ("left_debuff2", vio.dogs_left_debuff2),
            )
        else:
            template_map = (
                ("atk", vio.dogs_atk_bronze),
                ("atk", vio.dogs_atk_silver),
                ("atk", vio.dogs_right_special),
                ("right_buff", vio.dogs_right_buff),
            )

        candidates = self._collect_phase3_template_candidates(region, template_map, threshold=0.8)
        chosen_candidates = []
        for candidate in sorted(candidates, key=lambda item: item["combined_score"], reverse=True):
            if any(self._phase3_same_card_position(candidate, chosen) for chosen in chosen_candidates):
                continue
            chosen_candidates.append(candidate)
            if len(chosen_candidates) >= 5:
                break

        chosen_candidates.sort(key=lambda item: item["x"])
        return [candidate["label"] for candidate in chosen_candidates]

    def _phase3_mark_side_dead(self, side: str, reason: str):
        if side in DogsFloor4BattleStrategy.phase3_dead_sides:
            return

        DogsFloor4BattleStrategy.phase3_dead_sides.add(side)
        DogsFloor4BattleStrategy.phase3_current_gauges[side] = 0
        DogsFloor4BattleStrategy.phase3_next_turn_gauges[side] = 0
        DogsFloor4BattleStrategy.phase3_pending_gauge_reset[side] = False
        DogsFloor4BattleStrategy.phase3_last_seen_cards[side] = []
        DogsFloor4BattleStrategy.phase3_remaining_hp[side] = 0
        DogsFloor4BattleStrategy.phase3_damage_applied[side] = (
            self.PHASE3_LEFT_HP if side == "left" else self.PHASE3_RIGHT_HP
        )
        print(reason)

    def handle_phase3_target_selection_failure(self, screenshot, target_side: str) -> bool:
        if not DogsFloor4BattleStrategy.phase3_gimmick1_completed:
            return False
        if target_side in DogsFloor4BattleStrategy.phase3_dead_sides:
            return True

        top_left = self.PHASE3_LEFT_TOP_LEFT if target_side == "left" else self.PHASE3_RIGHT_TOP_LEFT
        bottom_right = self.PHASE3_LEFT_BOTTOM_RIGHT if target_side == "left" else self.PHASE3_RIGHT_BOTTOM_RIGHT
        target_region = crop_image(screenshot, top_left, bottom_right)
        visible_cards = self._detect_phase3_dog_cards(target_region, side=target_side)
        if visible_cards:
            return False

        self._phase3_mark_side_dead(
            target_side,
            f"Phase 3 target-selection failure inferred that the {target_side} dog is dead because no dog cards were visible in its area.",
        )
        return True

    def _best_nonlethal_phase2_card(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        allowed_ids = [idx for idx in matching_ids if not self._is_forbidden_phase2_card(hand_of_cards, idx)]
        safe_ids = [idx for idx in allowed_ids if not self._phase2_would_be_lethal_with_card(hand_of_cards, idx)]
        return safe_ids[-1] if safe_ids else -1

    def _best_phase2_lethal_setup_card(
        self, hand_of_cards: list[Card], template_names: Sequence[str], remaining_turn_slots: int
    ) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        allowed_ids = [idx for idx in matching_ids if not self._is_forbidden_phase2_card(hand_of_cards, idx)]

        for idx in reversed(allowed_ids):
            if self._phase2_card_keeps_lethal_line(hand_of_cards, idx, remaining_turn_slots):
                return idx

        return -1

    def _best_matching_card(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        return matching_ids[-1] if matching_ids else -1

    def _best_matching_card_with_ranks(
        self, hand_of_cards: list[Card], template_names: Sequence[str], ranks: set[CardRanks]
    ) -> int:
        matching_ids = [
            idx for idx in self._matching_card_ids(hand_of_cards, template_names) if hand_of_cards[idx].card_rank in ranks
        ]
        return matching_ids[-1] if matching_ids else -1

    def _matching_card_ids(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> list[int]:
        return sorted(
            [
                idx
                for idx, card in enumerate(hand_of_cards)
                if card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
                and self._card_matches_any(card, template_names)
            ],
            key=lambda idx: (hand_of_cards[idx].card_rank.value, idx),
        )

    def _card_matches_any(self, card: Card, template_names: Sequence[str]) -> bool:
        if card.card_image is None:
            return False
        return any(find(getattr(vio, template_name), card.card_image) for template_name in template_names)

    def _card_template_name(self, card: Card, template_names: Sequence[str]) -> str | None:
        return next(
            (template_name for template_name in template_names if self._card_matches_any(card, (template_name,))),
            None,
        )

    def estimate_auto_merge_count_after_play(self, hand_of_cards: list[Card], played_idx: int) -> int:
        if not (0 <= played_idx < len(hand_of_cards)):
            return 0

        simulated_cards = []
        for idx, card in enumerate(hand_of_cards):
            if idx == played_idx:
                continue
            template_name = self._card_template_name(
                card,
                self.ESCALIN_TEMPLATES + self.ROXY_TEMPLATES + self.NASI_TEMPLATES + self.THONAR_TEMPLATES,
            )
            simulated_cards.append(
                {
                    "template_name": template_name,
                    "card_rank": card.card_rank,
                }
            )

        merge_count = 0
        cursor = 0
        while cursor < len(simulated_cards) - 1:
            left_card = simulated_cards[cursor]
            right_card = simulated_cards[cursor + 1]
            if (
                left_card["template_name"] is not None
                and left_card["template_name"] == right_card["template_name"]
                and left_card["card_rank"] == right_card["card_rank"]
                and left_card["card_rank"] in {CardRanks.BRONZE, CardRanks.SILVER}
            ):
                next_rank = CardRanks.SILVER if left_card["card_rank"] == CardRanks.BRONZE else CardRanks.GOLD
                simulated_cards[cursor] = {
                    "template_name": left_card["template_name"],
                    "card_rank": next_rank,
                }
                del simulated_cards[cursor + 1]
                merge_count += 1
                cursor = max(0, cursor - 1)
                continue
            cursor += 1

        return merge_count

    def _phase2_move_action(self, hand_of_cards: list[Card]) -> list[int] | None:
        for template_names in [
            self.NASI_NON_ULT_TEMPLATES,
            ("escalin_st", "escalin_aoe"),
            self.ROXY_NON_ULT_TEMPLATES,
            ("thonar_stance",),
        ]:
            move_action = self._move_card_once(hand_of_cards, template_names)
            if move_action is not None:
                return move_action
        return None

    def _phase2_last_resort_move_action(self, hand_of_cards: list[Card]) -> list[int] | None:
        for template_names in [
            self.NASI_TEMPLATES,
            ("thonar_stance",),
            ("escalin_st", "escalin_aoe", "escalin_ult"),
            self.ROXY_TEMPLATES,
            ("thonar_ult",),
            ("thonar_gauge",),
        ]:
            move_action = self._move_card_once(hand_of_cards, template_names)
            if move_action is not None:
                return move_action
        return None

    def _phase2_nasi_ult_unlock_action(self, hand_of_cards: list[Card]) -> int:
        nasi_ult = self._best_matching_card(hand_of_cards, ("dogs_nasi_ult",))
        if nasi_ult == -1:
            return -1
        if self._best_matching_card(hand_of_cards, ("dogs_nasi_heal",)) != -1:
            return -1

        for template_names in [
            ("escalin_st",),
            self.ROXY_NON_ULT_TEMPLATES,
            ("escalin_aoe",),
            ("thonar_stance",),
            ("dogs_nasi_stun",),
        ]:
            if self._best_allowed_card(hand_of_cards, template_names) != -1:
                return -1

        if self._phase2_move_action(hand_of_cards) is not None:
            return -1

        return nasi_ult

    def _phase2_any_visible_card(self, hand_of_cards: list[Card], allow_protected_gauges=False) -> int:
        visible_ids = []
        for idx, card in enumerate(hand_of_cards):
            if card.card_type in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND):
                continue
            if self._card_matches_any(card, ("dogs_nasi_ult",)):
                continue
            if not allow_protected_gauges and idx in self._protected_thonar_gauge_ids(hand_of_cards):
                continue
            visible_ids.append(idx)
        return visible_ids[-1] if visible_ids else -1

    def _move_card_once(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> list[int] | None:
        if merge_move := self._find_merge_move(hand_of_cards, template_names):
            return merge_move

        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        if not matching_ids:
            return None

        origin_idx = matching_ids[-1]
        target_idx = origin_idx + 1 if origin_idx < len(hand_of_cards) - 1 else origin_idx - 1
        if target_idx < 0 or target_idx == origin_idx:
            return None

        return [origin_idx, target_idx]

    def _find_merge_move(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> list[int] | None:
        groups: dict[tuple[str, CardRanks], list[int]] = {}
        for idx in self._matching_card_ids(hand_of_cards, template_names):
            card = hand_of_cards[idx]
            if card.card_rank not in {CardRanks.BRONZE, CardRanks.SILVER}:
                continue

            template_name = self._card_template_name(card, template_names)
            if template_name is None:
                continue

            key = (template_name, card.card_rank)
            groups.setdefault(key, []).append(idx)

        for (_, _), ids in sorted(groups.items(), key=lambda item: item[0][1].value, reverse=True):
            if len(ids) >= 2:
                return [ids[0], ids[1]]

        return None

    def _played_count(self, picked_cards: list[Card], template_names: Sequence[str]) -> int:
        return sum(self._card_matches_any(card, template_names) for card in picked_cards if card.card_image is not None)

    def _has_card_in_hand_or_picked(
        self, hand_of_cards: list[Card], picked_cards: list[Card], template_names: Sequence[str]
    ) -> bool:
        return any(self._card_matches_any(card, template_names) for card in hand_of_cards if card.card_image is not None) or any(
            self._card_matches_any(card, template_names) for card in picked_cards if card.card_image is not None
        )

    def _should_restrict_phase2_turn1_heavy_damage(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> bool:
        escalin_st_in_plan = self._has_card_in_hand_or_picked(hand_of_cards, picked_cards, ("escalin_st",))
        has_other_big_damage = self._has_card_in_hand_or_picked(hand_of_cards, picked_cards, ("escalin_aoe",)) or (
            self._has_card_in_hand_or_picked(hand_of_cards, picked_cards, self.ROXY_NON_ULT_TEMPLATES)
        )
        return escalin_st_in_plan and not has_other_big_damage

    def _phase2_turn1_heavy_damage_cap_reached(self, picked_cards: list[Card], restrict_heavy_damage: bool) -> bool:
        if not restrict_heavy_damage:
            return False
        heavy_damage_count = self._played_count(picked_cards, self.HEAVY_DAMAGE_TEMPLATES)
        return heavy_damage_count >= 2

    def _phase2_damage_counts(self) -> tuple[int, int]:
        state = DogsFloor4BattleStrategy.phase2_damage_state
        return state["escalin_st"], state["other_damage"]

    def _phase2_damage_counts_with_card(self, hand_of_cards: list[Card], idx: int) -> tuple[int, int]:
        escalin_st_count, other_damage_count = self._phase2_damage_counts()
        escalin_st_gain, other_damage_gain = self._phase2_card_damage_gain(hand_of_cards[idx])
        return escalin_st_count + escalin_st_gain, other_damage_count + other_damage_gain

    def _phase2_card_damage_gain(self, card: Card) -> tuple[int, int]:
        if self._card_matches_any(card, ("escalin_st",)):
            return 1, 0
        if self._card_matches_any(card, self.HEAVY_DAMAGE_TEMPLATES):
            return 0, 1
        return 0, 0

    def _phase2_is_lethal_damage_profile(self, escalin_st_count: int, other_damage_count: int) -> bool:
        total_damage = escalin_st_count + other_damage_count
        return (
            escalin_st_count >= 2
            or (escalin_st_count >= 1 and other_damage_count >= 2)
            or total_damage >= 4
        )

    def _phase2_would_be_lethal_with_card(self, hand_of_cards: list[Card], idx: int) -> bool:
        escalin_st_count, other_damage_count = self._phase2_damage_counts_with_card(hand_of_cards, idx)
        return self._phase2_is_lethal_damage_profile(escalin_st_count, other_damage_count)

    def _phase2_card_keeps_lethal_line(
        self, hand_of_cards: list[Card], idx: int, remaining_turn_slots: int
    ) -> bool:
        escalin_st_count, other_damage_count = self._phase2_damage_counts_with_card(hand_of_cards, idx)
        if self._phase2_is_lethal_damage_profile(escalin_st_count, other_damage_count):
            return True

        slots_after_pick = max(0, remaining_turn_slots - 1)
        if slots_after_pick == 0:
            return False

        remaining_escalin_st = 0
        remaining_other_damage = 0
        for other_idx, other_card in enumerate(hand_of_cards):
            if other_idx == idx or self._is_forbidden_phase2_card(hand_of_cards, other_idx):
                continue

            escalin_st_gain, other_damage_gain = self._phase2_card_damage_gain(other_card)
            remaining_escalin_st += escalin_st_gain
            remaining_other_damage += other_damage_gain

        max_escalin_st_to_take = min(remaining_escalin_st, slots_after_pick)
        for extra_escalin_st in range(max_escalin_st_to_take + 1):
            max_other_damage_to_take = min(remaining_other_damage, slots_after_pick - extra_escalin_st)
            for extra_other_damage in range(max_other_damage_to_take + 1):
                if self._phase2_is_lethal_damage_profile(
                    escalin_st_count + extra_escalin_st,
                    other_damage_count + extra_other_damage,
                ):
                    return True

        return False

    def _thonar_gauge_ids(self, hand_of_cards: list[Card]) -> list[int]:
        return self._matching_card_ids(hand_of_cards, ("thonar_gauge",))

    def _thonar_gauge_ids_with_ranks(self, hand_of_cards: list[Card], ranks: set[CardRanks]) -> list[int]:
        return [idx for idx in self._thonar_gauge_ids(hand_of_cards) if hand_of_cards[idx].card_rank in ranks]

    def _protected_thonar_gauge_ids(self, hand_of_cards: list[Card]) -> set[int]:
        gauge_ids = self._thonar_gauge_ids(hand_of_cards)
        if len(gauge_ids) <= 2:
            return set(gauge_ids)
        return set(gauge_ids[-2:])

    def _expendable_thonar_gauge_ids(self, hand_of_cards: list[Card]) -> list[int]:
        protected_ids = self._protected_thonar_gauge_ids(hand_of_cards)
        return [idx for idx in self._thonar_gauge_ids(hand_of_cards) if idx not in protected_ids]

    def _lowest_expendable_thonar_gauge_id(self, hand_of_cards: list[Card]) -> int:
        expendable_ids = self._expendable_thonar_gauge_ids(hand_of_cards)
        if not expendable_ids:
            return -1
        return self._lowest_rank_rightmost_card_id(hand_of_cards, expendable_ids)

    def _is_forbidden_phase2_card(self, hand_of_cards: list[Card], idx: int) -> bool:
        card = hand_of_cards[idx]
        if self._card_matches_any(card, ("dogs_nasi_ult",)):
            return True
        if idx in self._protected_thonar_gauge_ids(hand_of_cards):
            return True
        return False

    def _best_allowed_card(self, hand_of_cards: list[Card], template_names: Sequence[str]) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names)
        allowed_ids = [idx for idx in matching_ids if not self._is_forbidden_phase2_card(hand_of_cards, idx)]
        return allowed_ids[-1] if allowed_ids else -1

    def _phase2_any_allowed_card(self, hand_of_cards: list[Card]) -> int:
        allowed_ids = [
            idx
            for idx, card in enumerate(hand_of_cards)
            if card.card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
            and not self._is_forbidden_phase2_card(hand_of_cards, idx)
        ]
        return allowed_ids[-1] if allowed_ids else -1

    def should_finish_phase2_turn_early(self, hand_of_cards: list[Card]) -> bool:
        if not self._phase2_is_lethal_damage_profile(*self._phase2_damage_counts()):
            return False
        if self._phase2_any_visible_card(hand_of_cards) != -1:
            return False
        if self._phase2_move_action(hand_of_cards) is not None:
            return False
        return True

    def register_confirmed_action(self, hand_of_cards: list[Card], action, played_card: Card | None = None):
        if isinstance(action, int):
            if played_card is None or played_card.card_image is None:
                return
            if unit_name := self._unit_name_from_card(played_card):
                self._register_play_action(unit_name, played_card)
        elif isinstance(action, (list, tuple)) and len(action) == 2:
            origin_idx, target_idx = action
            if 0 <= origin_idx < len(hand_of_cards) and 0 <= target_idx < len(hand_of_cards):
                if unit_name := self._unit_name_from_card(hand_of_cards[origin_idx]):
                    merged = self._move_creates_merge(hand_of_cards, origin_idx, target_idx)
                    self._register_move_action(unit_name, merged=merged)

    def register_turn_completed(self):
        DogsFloor4BattleStrategy.turn += 1

    def _register_and_return_action(self, hand_of_cards: list[Card], action):
        if isinstance(action, int):
            if 0 <= action < len(hand_of_cards):
                if unit_name := self._unit_name_from_card(hand_of_cards[action]):
                    self._register_play_action(unit_name, hand_of_cards[action])
        elif isinstance(action, (list, tuple)) and len(action) == 2:
            origin_idx, target_idx = action
            if 0 <= origin_idx < len(hand_of_cards) and 0 <= target_idx < len(hand_of_cards):
                if unit_name := self._unit_name_from_card(hand_of_cards[origin_idx]):
                    merged = self._move_creates_merge(hand_of_cards, origin_idx, target_idx)
                    self._register_move_action(unit_name, merged=merged)
        return action

    def _unit_name_from_card(self, card: Card) -> str | None:
        if self._card_matches_any(card, self.ESCALIN_TEMPLATES):
            return "escalin"
        if self._card_matches_any(card, self.ROXY_TEMPLATES):
            return "roxy"
        if self._card_matches_any(card, self.NASI_TEMPLATES):
            return "nasi"
        if self._card_matches_any(card, self.THONAR_TEMPLATES):
            return "thonar"
        return None

    def _move_creates_merge(self, hand_of_cards: list[Card], origin_idx: int, target_idx: int) -> bool:
        origin_card = hand_of_cards[origin_idx]
        target_card = hand_of_cards[target_idx]
        origin_unit = self._unit_name_from_card(origin_card)
        target_unit = self._unit_name_from_card(target_card)
        if origin_unit is None or origin_unit != target_unit:
            return False
        if origin_card.card_rank != target_card.card_rank:
            return False
        return origin_card.card_rank in {CardRanks.BRONZE, CardRanks.SILVER}

    def _register_play_action(self, unit_name: str, card: Card):
        ult_templates = {
            "escalin": ("escalin_ult",),
            "roxy": ("dogs_roxy_ult",),
            "nasi": ("dogs_nasi_ult",),
            "thonar": ("thonar_ult",),
        }
        is_ult = self._card_matches_any(card, ult_templates[unit_name])
        self._register_phase2_damage_card(card)
        if unit_name == "thonar":
            for other_unit in DogsFloor4BattleStrategy.ult_gauges:
                self._add_gauge(other_unit, 1)

        if is_ult:
            DogsFloor4BattleStrategy.ult_gauges[unit_name] = 0
        else:
            self._add_gauge(unit_name, 1)

    def _register_move_action(self, unit_name: str, merged=False):
        gain = 2 if merged else 1
        if unit_name == "thonar":
            for other_unit in DogsFloor4BattleStrategy.ult_gauges:
                self._add_gauge(other_unit, gain)
        else:
            self._add_gauge(unit_name, gain)

    def _add_gauge(self, unit_name: str, amount: int):
        DogsFloor4BattleStrategy.ult_gauges[unit_name] = min(
            5, DogsFloor4BattleStrategy.ult_gauges[unit_name] + amount
        )

    def _register_phase2_damage_card(self, card: Card):
        if DogsFloor4BattleStrategy._last_phase_seen != 2:
            return

        escalin_st_gain, other_damage_gain = self._phase2_card_damage_gain(card)
        DogsFloor4BattleStrategy.phase2_damage_state["escalin_st"] += escalin_st_gain
        DogsFloor4BattleStrategy.phase2_damage_state["other_damage"] += other_damage_gain

    def register_phase3_card_play(self, card: Card, target_side: str | None = None):
        if DogsFloor4BattleStrategy._last_phase_seen != 3 or card.card_image is None:
            return

        if self._card_matches_any(card, ("thonar_gauge",)) and target_side in {"left", "right"}:
            reduction = self._phase3_thonar_gauge_reduction(card)
            self._apply_phase3_gauge_reduction(target_side, reduction)
            DogsFloor4BattleStrategy.phase3_trigger_gauge_targets_used.add(target_side)
            DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps = max(
                0,
                DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps - 1,
            )
            print(
                "Phase 3 trigger tracking: used thonar_gauge on "
                f"{target_side} dog (rank={card.card_rank.name}, reduction={reduction}, "
                f"reserved_steps_remaining={DogsFloor4BattleStrategy.phase3_trigger_reserved_gauge_steps})."
            )
            damage_amount = (
                self.PHASE3_GOLD_THONAR_GAUGE_DAMAGE
                if card.card_rank == CardRanks.GOLD
                else self.PHASE3_LOW_DAMAGE["thonar_gauge_non_gold"]
            )
            self._phase3_apply_flat_damage(target_side, damage_amount)
            print(
                "Phase 3 damage update after thonar_gauge -> "
                f"target={target_side}, damage={damage_amount}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
            )
            return

        if self._card_matches_any(card, ("dogs_nasi_stun",)):
            resolved_target = target_side or self._phase3_side_with_highest_remaining_hp()
            self._phase3_apply_flat_damage(resolved_target, self.PHASE3_LOW_DAMAGE["dogs_nasi_stun"])
            print(
                "Phase 3 damage update after nasi_stun -> "
                f"target={resolved_target}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
            )
            return

        if self._card_matches_any(card, ("thonar_stance",)):
            resolved_target = target_side or self._phase3_side_with_highest_remaining_hp()
            self._phase3_apply_flat_damage(resolved_target, self.PHASE3_LOW_DAMAGE["thonar_stance"])
            print(
                "Phase 3 damage update after thonar_stance -> "
                f"target={resolved_target}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
            )
            return

        if self._card_matches_any(card, ("escalin_ult", "escalin_aoe", "dogs_roxy_aoe")):
            caps = self.PHASE3_DAMAGE_CAP if self._phase3_is_gimmick_damage_active() else self.PHASE3_PRE_GIMMICK_DAMAGE_CAP
            add_roxy_bonus = not self._card_matches_any(card, ("escalin_ult",))
            left_damage = self._phase3_damage_value("left", caps["left"], add_roxy_bonus)
            right_damage = self._phase3_damage_value("right", caps["right"], add_roxy_bonus)
            self._phase3_apply_flat_damage("left", left_damage)
            self._phase3_apply_flat_damage("right", right_damage)
            print(f"Phase 3 damage update after AOE -> remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}")
            return

        if self._card_matches_any(card, ("escalin_st",)):
            self._apply_phase3_escalin_st_damage(target_side)
            return

        if self._card_matches_any(card, ("dogs_roxy_st",)):
            resolved_target = target_side or self._phase3_side_with_highest_remaining_hp()
            caps = self.PHASE3_DAMAGE_CAP if self._phase3_is_gimmick_damage_active() else self.PHASE3_PRE_GIMMICK_DAMAGE_CAP
            damage_amount = self._phase3_damage_value(resolved_target, caps[resolved_target], add_roxy_bonus=True)
            self._phase3_apply_flat_damage(resolved_target, damage_amount)
            print(
                "Phase 3 damage update after roxy_st -> "
                f"target={resolved_target}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
            )
            return

        if self._card_matches_any(card, ("dogs_roxy_ult", "thonar_ult")):
            resolved_target = target_side or self._phase3_side_with_highest_remaining_hp()
            caps = self.PHASE3_DAMAGE_CAP if self._phase3_is_gimmick_damage_active() else self.PHASE3_PRE_GIMMICK_DAMAGE_CAP
            self._apply_phase3_single_target_damage(resolved_target, damage_amount=caps[resolved_target])

    def _apply_phase3_single_target_damage(self, target_side: str | None, damage_amount: int | None = None):
        target_side = target_side or self._phase3_side_with_highest_remaining_hp()
        if damage_amount is None:
            damage_amount = self.PHASE3_DAMAGE_CAP[target_side]
        self._phase3_apply_flat_damage(
            target_side,
            damage_amount,
        )
        print(
            "Phase 3 damage update after single-target huge card -> "
            f"target={target_side}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
        )

    def _apply_phase3_escalin_st_damage(self, target_side: str | None):
        target_side = target_side or self._phase3_side_with_highest_remaining_hp()
        other_side = "right" if target_side == "left" else "left"
        base_damage = self.PHASE3_DAMAGE_CAP[target_side]

        if DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] <= base_damage:
            spill_damage = base_damage * 0.7
            kill_bonus_damage = (base_damage + spill_damage) * 0.5
            DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] = 0
            DogsFloor4BattleStrategy.phase3_remaining_hp[other_side] = max(
                0,
                DogsFloor4BattleStrategy.phase3_remaining_hp[other_side] - spill_damage - kill_bonus_damage,
            )
        else:
            DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] = max(
                0,
                DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] - self.PHASE3_ESCALIN_ST_TOTAL_DAMAGE[target_side],
            )
        DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] = max(
            0,
            DogsFloor4BattleStrategy.phase3_remaining_hp[target_side] - self.PHASE3_ROXY_PASSIVE_BONUS_DAMAGE,
        )

        DogsFloor4BattleStrategy.phase3_damage_applied["left"] = self.PHASE3_LEFT_HP - DogsFloor4BattleStrategy.phase3_remaining_hp["left"]
        DogsFloor4BattleStrategy.phase3_damage_applied["right"] = self.PHASE3_RIGHT_HP - DogsFloor4BattleStrategy.phase3_remaining_hp["right"]
        print(
            "Phase 3 damage update after escalin_st -> "
            f"target={target_side}, remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
        )

    def register_phase3_talent_use(self):
        if DogsFloor4BattleStrategy._last_phase_seen != 3:
            return

        self._phase3_apply_flat_damage(
            "left",
            self._phase3_damage_value("left", self.PHASE3_PRE_GIMMICK_DAMAGE_CAP["left"], add_roxy_bonus=True),
        )
        self._phase3_apply_flat_damage(
            "right",
            self._phase3_damage_value("right", self.PHASE3_PRE_GIMMICK_DAMAGE_CAP["right"], add_roxy_bonus=True),
        )
        print(
            "Phase 3 damage update after talent -> "
            f"remaining_hp={DogsFloor4BattleStrategy.phase3_remaining_hp}"
        )

    def _phase3_side_with_highest_remaining_hp(self) -> str:
        alive_sides = self._phase3_alive_target_sides()
        if len(alive_sides) == 1:
            return alive_sides[0]
        if DogsFloor4BattleStrategy.phase3_remaining_hp["left"] >= DogsFloor4BattleStrategy.phase3_remaining_hp["right"]:
            return "left"
        return "right"
