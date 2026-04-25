import time
from collections.abc import Sequence
from copy import deepcopy
from typing import Final

import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.utilities import (
    capture_window,
    click_im,
    determine_card_merge,
    find,
)

ESCALIN_TEMPLATES: Final[tuple[str, ...]] = ("escalin_st", "escalin_aoe", "escalin_ult")
MELI3K_TEMPLATES: Final[tuple[str, ...]] = ("meli3k_st", "meli3k_aoe", "meli3k_ult")
GOW_TEMPLATES: Final[tuple[str, ...]] = ("gow_atk", "gow_debuff", "gow_ult")
NASI_TEMPLATES: Final[tuple[str, ...]] = ("nasi_heal", "nasi_stun", "nasi_ult")
MERGE_GUARD_TEMPLATES: Final[tuple[str, ...]] = (
    *ESCALIN_TEMPLATES,
    *MELI3K_TEMPLATES,
    *GOW_TEMPLATES,
    *NASI_TEMPLATES,
)
PHASE2_ODD_STANCE_SINS_TEMPLATES: Final[tuple[str, ...]] = (
    *ESCALIN_TEMPLATES,
    *MELI3K_TEMPLATES,
    "gow_atk",
)


class DogsFloor4WhaleBattleStrategy(IBattleStrategy):
    """Dogs Floor 4 whale strategy for Escalin, Meli3k, Blue Gowther, and Nasiens."""

    turn = 0
    _phase_initialized = set()
    _last_phase_seen = None
    meli3k_in_team = False
    bluegow_in_team = False
    _requested_reset_reason = None

    def _initialize_static_variables(self):
        DogsFloor4WhaleBattleStrategy._phase_initialized = set()
        DogsFloor4WhaleBattleStrategy._last_phase_seen = None
        DogsFloor4WhaleBattleStrategy._requested_reset_reason = None

    def reset_run_state(self, *, meli3k_in_team=False, bluegow_in_team=False):
        """Called from DogsFloor4FighterWhale.run before the fight loop."""
        print(
            "Resetting whale run state with Meli3k in team:",
            meli3k_in_team,
            "Blue Gowther in team:",
            bluegow_in_team,
        )
        DogsFloor4WhaleBattleStrategy.meli3k_in_team = meli3k_in_team
        DogsFloor4WhaleBattleStrategy.bluegow_in_team = bluegow_in_team
        self._initialize_static_variables()

    def request_fight_reset(self, reason: str) -> None:
        DogsFloor4WhaleBattleStrategy._requested_reset_reason = reason

    def consume_requested_reset_reason(self) -> str | None:
        reason = DogsFloor4WhaleBattleStrategy._requested_reset_reason
        DogsFloor4WhaleBattleStrategy._requested_reset_reason = None
        return reason

    def _maybe_reset(self, phase_id: str):
        if phase_id not in DogsFloor4WhaleBattleStrategy._phase_initialized:
            DogsFloor4WhaleBattleStrategy._phase_initialized.add(phase_id)

    def _get_next_card_index_whale(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        phase: int,
        *,
        card_turn: int,
    ) -> int | list[int]:
        if phase == 1:
            return self._get_next_card_index_whale_phase1(hand_of_cards, picked_cards, card_turn)
        if phase == 2:
            return self._get_next_card_index_whale_phase2(hand_of_cards, picked_cards, card_turn)
        return self._get_next_card_index_whale_phase3(hand_of_cards, picked_cards, card_turn)

    def _get_next_card_index_whale_phase1(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        self._maybe_reset("phase_1_whale")

        if IBattleStrategy.fight_turn > 2:
            self.request_fight_reset("Dogs Floor 4 whale mode: phase 1 went off script, resetting the fight.")
            return 0

        if IBattleStrategy.fight_turn == 1:
            if card_turn in {0, 1}:
                move_action = self._best_nasi_setup_move(hand_of_cards)
                if move_action is None:
                    self.request_fight_reset(
                        "Dogs Floor 4 whale mode: phase 1 turn 1 needed a Nasi setup move, but none was found."
                    )
                    return 0
                return move_action
            if card_turn == 2:
                gow_aoe_id = self._best_card_from_priority(hand_of_cards, [("gow_atk",)])
                if gow_aoe_id == -1:
                    self.request_fight_reset(
                        "Dogs Floor 4 whale mode: phase 1 turn 1 expected Gow AOE, but it was missing."
                    )
                    return 0
                return gow_aoe_id
            meli_aoe_id = self._best_matching_card(hand_of_cards, ("meli3k_aoe",))
            if meli_aoe_id == -1:
                self.request_fight_reset(
                    "Dogs Floor 4 whale mode: phase 1 turn 1 expected Meli3k AOE, but it was missing."
                )
                return 0
            return meli_aoe_id

        if card_turn == 0 and not self._activate_escalin_talent_or_reset("phase 1 turn 2"):
            return 0

        phase1_turn2_priorities: tuple[tuple[str, ...], ...] = (
            ("nasi_heal",),
            ("meli3k_st",),
            ("escalin_aoe",),
            ("escalin_st",),
        )
        idx = self._best_card_from_priority(hand_of_cards, [phase1_turn2_priorities[card_turn]])
        if idx == -1:
            self.request_fight_reset(
                f"Dogs Floor 4 whale mode: phase 1 turn 2 was missing its scripted action {card_turn + 1}."
            )
            return 0
        return idx

    def _get_next_card_index_whale_phase2(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        self._maybe_reset("phase_2_whale")

        if IBattleStrategy.fight_turn == 1:
            return self._phase2_turn1_whale_action(hand_of_cards, picked_cards, card_turn)

        if IBattleStrategy.fight_turn % 2 == 0:
            return self._phase2_even_turn_whale_action(hand_of_cards, picked_cards, card_turn)

        return self._phase2_odd_turn_whale_action(hand_of_cards, picked_cards, card_turn)

    def _phase2_turn1_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        nasi_ids = self._matching_card_ids(hand_of_cards, NASI_TEMPLATES)
        hi_stun_ids = self._matching_card_ids(hand_of_cards, ("nasi_stun",), ranks=(CardRanks.SILVER, CardRanks.GOLD))
        if card_turn == 0:
            if len(nasi_ids) >= 2:
                random_nasi_id = self._phase2_random_nasi_opener_id(hand_of_cards)
                if random_nasi_id == -1:
                    self.request_fight_reset(
                        "Dogs Floor 4 whale mode: phase 2 turn 1 expected an opener Nasi card, but none was usable."
                    )
                    return 0
                return random_nasi_id
            if len(nasi_ids) == 1 and hi_stun_ids:
                move_action = self._adjacent_occupied_move(hand_of_cards, hi_stun_ids[-1])
                if move_action is None:
                    self.request_fight_reset(
                        "Dogs Floor 4 whale mode: phase 2 turn 1 needed to move the lone silver/gold Nasi stun, but no move target was found."
                    )
                    return 0
                return move_action
            print(
                "Dogs Floor 4 whale mode: phase 2 turn 1 could not identify the scripted Nasi opener, "
                "so falling back to the odd-turn stance-break logic."
            )
            return self._phase2_odd_turn_whale_action(hand_of_cards, picked_cards, card_turn)

        if card_turn == 1:
            if hi_stun_ids:
                return hi_stun_ids[-1]
            print(
                "Dogs Floor 4 whale mode: phase 2 turn 1 lost sight of the silver/gold Nasi stun, "
                "so falling back to the odd-turn stance-break logic."
            )
            return self._phase2_odd_turn_whale_action(hand_of_cards, picked_cards, card_turn)

        return self._phase2_turn1_whale_nuke_action(hand_of_cards, picked_cards, card_turn)

    def _phase2_turn1_whale_nuke_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        meli_ids = self._matching_card_ids(hand_of_cards, MELI3K_TEMPLATES)
        esca_ids = self._matching_card_ids(hand_of_cards, ESCALIN_TEMPLATES)
        played_meli = self._turn_has_any(picked_cards, MELI3K_TEMPLATES)
        played_esca = self._turn_has_any(picked_cards, ESCALIN_TEMPLATES)

        if meli_ids and esca_ids:
            if not played_esca:
                idx = self._best_card_from_priority(hand_of_cards, [("escalin_st",), ("escalin_aoe",), ("escalin_ult",)])
                if idx != -1:
                    return idx
            idx = self._best_card_from_priority(hand_of_cards, [("meli3k_st",), ("meli3k_aoe",), ("meli3k_ult",)])
            if idx != -1:
                return idx

        if meli_ids and not esca_ids:
            if not played_meli:
                idx = self._best_card_from_priority(hand_of_cards, [("meli3k_st",), ("meli3k_aoe",), ("meli3k_ult",)])
                if idx != -1:
                    return idx
            idx = self._best_card_from_priority(hand_of_cards, [("meli3k_aoe",), ("meli3k_st",), ("meli3k_ult",)])
            if idx != -1:
                return idx

        if esca_ids and not meli_ids:
            esca_st_ids = self._matching_card_ids(hand_of_cards, ("escalin_st",))
            if len(esca_st_ids) >= 2:
                return esca_st_ids[-1]
            idx = self._best_card_from_priority(hand_of_cards, [("escalin_st",), ("escalin_aoe",)])
            if idx != -1:
                return idx

        filler_action = self._phase2_support_filler_action(hand_of_cards, picked_cards, allow_silver_stun_merge=False)
        if filler_action != -1:
            return filler_action

        fallback_action = self._phase2_last_resort_action(hand_of_cards, picked_cards)
        if fallback_action != -1:
            return fallback_action

        self.request_fight_reset(
            "Dogs Floor 4 whale mode: phase 2 turn 1 reached its filler path with no safe action available."
        )
        return 0

    def _phase2_even_turn_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        nuke_action = self._phase2_even_turn_nuke_action(hand_of_cards)
        if nuke_action != -1:
            return nuke_action

        filler_action = self._phase2_support_filler_action(hand_of_cards, picked_cards, allow_silver_stun_merge=False)
        if filler_action != -1:
            return filler_action

        fallback_action = self._phase2_last_resort_action(hand_of_cards, picked_cards)
        if fallback_action != -1:
            return fallback_action

        self.request_fight_reset(
            "Dogs Floor 4 whale mode: phase 2 even turn had neither a nuke card nor a safe filler action."
        )
        return 0

    def _phase2_odd_turn_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        played_heal = self._turn_has_any(picked_cards, ("nasi_heal",))
        played_hi_stun = self._turn_has_any(picked_cards, ("nasi_stun",), ranks=(CardRanks.SILVER, CardRanks.GOLD))
        played_meli_ult = self._turn_has_any(picked_cards, ("meli3k_ult",))
        sins_played_count = self._turn_match_count(picked_cards, PHASE2_ODD_STANCE_SINS_TEMPLATES)

        if not played_heal:
            nasi_heal_id = self._best_matching_card(hand_of_cards, ("nasi_heal",))
            if nasi_heal_id != -1:
                return nasi_heal_id

        if played_hi_stun or played_meli_ult or sins_played_count >= 3:
            nuke_action = self._phase2_even_turn_nuke_action(hand_of_cards)
            if nuke_action != -1:
                return nuke_action
            filler_action = self._phase2_support_filler_action(hand_of_cards, picked_cards, allow_silver_stun_merge=False)
            if filler_action != -1:
                return filler_action
            fallback_action = self._phase2_last_resort_action(hand_of_cards, picked_cards)
            if fallback_action != -1:
                return fallback_action
            self.request_fight_reset(
                "Dogs Floor 4 whale mode: phase 2 odd turn cleared stance, but no follow-up action was available."
            )
            return 0

        hi_stun_id = self._best_matching_card(hand_of_cards, ("nasi_stun",), ranks=(CardRanks.SILVER, CardRanks.GOLD))
        if hi_stun_id != -1:
            return hi_stun_id

        meli_ult_id = self._best_matching_card(hand_of_cards, ("meli3k_ult",))
        if meli_ult_id != -1:
            return meli_ult_id

        sins_action = self._phase2_odd_turn_sins_sequence_action(hand_of_cards, picked_cards)
        if sins_action != -1:
            return sins_action

        self.request_fight_reset(
            "Dogs Floor 4 whale mode: phase 2 odd turn could not remove stance with either Nasi stun or the 3-Sins sequence."
        )
        return 0

    def _get_next_card_index_whale_phase3(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        self._maybe_reset("phase_3_whale")

        if IBattleStrategy.fight_turn == 1:
            return self._phase3_turn1_whale_action(hand_of_cards, picked_cards, card_turn)
        if IBattleStrategy.fight_turn == 2:
            return self._phase3_turn2_whale_action(hand_of_cards, picked_cards, card_turn)
        if IBattleStrategy.fight_turn == 3:
            return self._phase3_turn3_whale_action(hand_of_cards, picked_cards, card_turn)
        return self._phase3_nuke_action(hand_of_cards, picked_cards)

    def _phase3_turn1_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        if card_turn == 0:
            nasi_ult_id = self._best_matching_card(hand_of_cards, ("nasi_ult",))
            if nasi_ult_id == -1:
                self.request_fight_reset("Dogs Floor 4 whale mode: phase 3 turn 1 must open with Nasi ult.")
                return 0
            return nasi_ult_id
        return self._phase3_setup_action(
            hand_of_cards,
            picked_cards,
            card_turn=card_turn,
            prefer_heal=True,
            use_reserved_on_last_action=False,
        )

    def _phase3_turn2_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        return self._phase3_setup_action(
            hand_of_cards,
            picked_cards,
            card_turn=card_turn,
            prefer_heal=True,
            use_reserved_on_last_action=card_turn >= 3,
        )

    def _phase3_turn3_whale_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
    ) -> int | list[int]:
        gow_ult_missing_in_hand = self._best_matching_card(hand_of_cards, ("gow_ult",)) == -1
        gow_ult_already_played = self._turn_has_any(picked_cards, ("gow_ult",))
        if gow_ult_missing_in_hand and not gow_ult_already_played:
            self.request_fight_reset("Dogs Floor 4 whale mode: phase 3 turn 3 expected Gow ult, so resetting.")
            return 0

        idx = self._best_card_from_priority(
            hand_of_cards,
            [
                ("gow_ult",),
                ("escalin_ult",),
                ("meli3k_ult",),
                ("escalin_aoe",),
                ("meli3k_aoe",),
                ("nasi_heal",),
                ("gow_debuff",),
                ("gow_atk",),
                ("nasi_stun",),
            ],
        )
        if idx != -1:
            return idx

        noop_move = self._phase3_turn3_noop_move(hand_of_cards)
        if noop_move is not None:
            print("Dogs Floor 4 whale mode: phase 3 turn 3 had no junk card, so using a 6 -> 7 hand cycle move.")
            return noop_move

        self.request_fight_reset("Dogs Floor 4 whale mode: phase 3 turn 3 had no valid scripted follow-up.")
        return 0

    def _phase3_nuke_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
    ) -> int | list[int]:
        idx = self._best_card_from_priority(
            hand_of_cards,
            [
                ("escalin_ult",),
                ("meli3k_ult",),
                ("escalin_aoe",),
                ("meli3k_aoe",),
                ("escalin_st",),
                ("meli3k_st",),
                ("gow_ult",),
                ("gow_debuff",),
                ("gow_atk",),
            ],
        )
        if idx != -1:
            return idx

        filler_action = self._phase2_support_filler_action(hand_of_cards, picked_cards, allow_silver_stun_merge=False)
        if filler_action != -1:
            return filler_action

        self.request_fight_reset("Dogs Floor 4 whale mode: phase 3 nuke phase ran out of usable actions.")
        return 0

    def _phase2_even_turn_nuke_action(self, hand_of_cards: list[Card]) -> int:
        return self._best_card_from_priority(
            hand_of_cards,
            [
                ("escalin_st",),
                ("meli3k_st",),
                ("escalin_aoe",),
                ("meli3k_aoe",),
                ("escalin_ult",),
                ("meli3k_ult",),
            ],
        )

    def _phase2_odd_turn_sins_sequence_action(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        sins_played_count = self._turn_match_count(picked_cards, PHASE2_ODD_STANCE_SINS_TEMPLATES)
        if sins_played_count >= 2:
            return self._best_card_from_priority(
                hand_of_cards,
                [("meli3k_st",), ("meli3k_aoe",), ("meli3k_ult",)],
            )

        future_meli_ids = self._matching_card_ids(hand_of_cards, MELI3K_TEMPLATES)
        non_meli_sins_id = self._best_card_from_priority(
            hand_of_cards,
            [("gow_atk",), ("escalin_st",), ("escalin_aoe",), ("escalin_ult",)],
        )
        if non_meli_sins_id != -1 and future_meli_ids:
            return non_meli_sins_id

        if len(future_meli_ids) >= 2 - sins_played_count + 1:
            return self._best_card_from_priority(
                hand_of_cards,
                [("meli3k_st",), ("meli3k_aoe",), ("meli3k_ult",)],
            )

        return -1

    def _phase3_setup_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        *,
        card_turn: int,
        prefer_heal: bool,
        use_reserved_on_last_action: bool,
    ) -> int | list[int]:
        if prefer_heal and not self._turn_has_any(picked_cards, ("nasi_heal",)):
            nasi_heal_id = self._best_matching_card(hand_of_cards, ("nasi_heal",))
            if nasi_heal_id != -1:
                return nasi_heal_id

        if self._best_matching_card(hand_of_cards, ("gow_ult",)) == -1:
            preserve_action = self._phase3_gow_setup_action(
                hand_of_cards,
                use_reserved_on_last_action=use_reserved_on_last_action,
            )
            if preserve_action != -1:
                return preserve_action
            self.request_fight_reset(
                "Dogs Floor 4 whale mode: phase 3 setup needed to preserve a Gow card, but no safe preserve action was found."
            )
            return 0

        esca_ult_missing = self._best_matching_card(hand_of_cards, ("escalin_ult",)) == -1
        meli_ult_missing = self._best_matching_card(hand_of_cards, ("meli3k_ult",)) == -1
        if esca_ult_missing:
            preserve_action = self._phase3_preserve_unit_action(
                hand_of_cards,
                ESCALIN_TEMPLATES,
                keep_one_aoe=True,
                use_reserved_on_last_action=use_reserved_on_last_action,
            )
            if preserve_action != -1:
                return preserve_action
            self.request_fight_reset(
                "Dogs Floor 4 whale mode: phase 3 setup needed to preserve an Escalin card, but no safe preserve action was found."
            )
            return 0
        if meli_ult_missing:
            preserve_action = self._phase3_preserve_unit_action(
                hand_of_cards,
                MELI3K_TEMPLATES,
                keep_one_aoe=True,
                use_reserved_on_last_action=use_reserved_on_last_action,
            )
            if preserve_action != -1:
                return preserve_action
            self.request_fight_reset(
                "Dogs Floor 4 whale mode: phase 3 setup needed to preserve a Meli3k card, but no safe preserve action was found."
            )
            return 0

        reserved_ids = set()
        extra_aoe_id = self._best_card_from_priority(hand_of_cards, [("escalin_aoe",), ("meli3k_aoe",)])
        if extra_aoe_id != -1:
            reserved_ids.add(extra_aoe_id)
        idx = self._best_card_from_priority(
            hand_of_cards,
            [
                ("gow_debuff",),
                ("gow_atk",),
                ("nasi_heal",),
                ("nasi_stun",),
                ("nasi_ult",),
                ("escalin_st",),
                ("meli3k_st",),
            ],
            exclude_ids=reserved_ids,
        )
        if idx != -1:
            return idx
        if extra_aoe_id != -1:
            move_action = self._adjacent_occupied_move(hand_of_cards, extra_aoe_id)
            if move_action is not None:
                return move_action
        self.request_fight_reset("Dogs Floor 4 whale mode: phase 3 setup ran out of preserve/cycle actions.")
        return 0

    def _phase3_gow_setup_action(
        self,
        hand_of_cards: list[Card],
        *,
        use_reserved_on_last_action: bool,
    ) -> int | list[int]:
        gow_ids = self._matching_card_ids(hand_of_cards, GOW_TEMPLATES)
        if not gow_ids:
            return -1

        reserve_builder_id = gow_ids[-1]
        spendable_gow_ids = [idx for idx in gow_ids if idx != reserve_builder_id]
        if spendable_gow_ids:
            return spendable_gow_ids[-1]

        if use_reserved_on_last_action:
            return reserve_builder_id

        move_action = self._adjacent_occupied_move(hand_of_cards, reserve_builder_id)
        if move_action is not None:
            return move_action

        return reserve_builder_id

    def _phase3_preserve_unit_action(
        self,
        hand_of_cards: list[Card],
        unit_templates: Sequence[str],
        *,
        keep_one_aoe: bool,
        use_reserved_on_last_action: bool,
    ) -> int | list[int]:
        reserved_ids = set()
        reserve_builder_id = self._best_card_from_priority(
            hand_of_cards,
            [(tuple(t for t in unit_templates if "aoe" in t)), unit_templates],
        )
        if reserve_builder_id != -1:
            reserved_ids.add(reserve_builder_id)

        if keep_one_aoe:
            extra_aoe_id = self._best_card_from_priority(hand_of_cards, [("escalin_aoe",), ("meli3k_aoe",)])
            if extra_aoe_id != -1:
                reserved_ids.add(extra_aoe_id)

        spend_id = self._best_card_from_priority(
            hand_of_cards,
            [
                ("gow_debuff",),
                ("gow_atk",),
                ("nasi_heal",),
                ("nasi_stun",),
                unit_templates,
                ("nasi_ult",),
            ],
            exclude_ids=reserved_ids,
        )
        if spend_id != -1:
            return spend_id

        if reserve_builder_id != -1:
            if use_reserved_on_last_action:
                return reserve_builder_id
            move_action = self._adjacent_occupied_move(hand_of_cards, reserve_builder_id)
            if move_action is not None:
                return move_action

        return -1

    def _phase3_turn3_noop_move(self, hand_of_cards: list[Card]) -> list[int] | None:
        if len(hand_of_cards) > 7:
            idx6 = hand_of_cards[6]
            idx7 = hand_of_cards[7]
            if idx6.card_type not in (CardTypes.NONE, CardTypes.GROUND) and idx7.card_type not in (
                CardTypes.NONE,
                CardTypes.GROUND,
            ):
                return [6, 7]
        return None

    def _phase2_support_filler_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        *,
        allow_silver_stun_merge: bool,
    ) -> int | list[int]:
        bronze_merge = self._best_merge_drag_indices(hand_of_cards, ("nasi_stun",), rank=CardRanks.BRONZE)
        if bronze_merge is not None:
            return bronze_merge

        if allow_silver_stun_merge:
            silver_merge = self._best_merge_drag_indices(hand_of_cards, ("nasi_stun",), rank=CardRanks.SILVER)
            if silver_merge is not None:
                return silver_merge

        if not self._turn_has_any(picked_cards, ("nasi_heal",)):
            nasi_heal_id = self._best_matching_card(hand_of_cards, ("nasi_heal",))
            if nasi_heal_id != -1:
                return nasi_heal_id

        gow_ids = self._matching_card_ids(hand_of_cards, GOW_TEMPLATES)
        gow_id = self._best_card_from_priority(hand_of_cards, [("gow_debuff",), ("gow_atk",)])
        if gow_id != -1 and len(gow_ids) >= 2:
            return gow_id

        return -1

    def _phase2_last_resort_action(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
    ) -> int:
        return self._best_card_from_priority(
            hand_of_cards,
            [
                ("nasi_heal",),
                ("gow_debuff",),
                ("gow_atk",),
                ("nasi_stun",),
                ("escalin_st",),
                ("meli3k_st",),
                ("escalin_aoe",),
                ("meli3k_aoe",),
            ],
        )

    def _best_nasi_setup_move(self, hand_of_cards: list[Card]) -> list[int] | None:
        nasi_ids = self._matching_card_ids(hand_of_cards, ("nasi_heal", "nasi_stun"))
        if not nasi_ids:
            nasi_ids = self._matching_card_ids(hand_of_cards, ("nasi_ult",))
        if not nasi_ids:
            return None
        origin_idx = nasi_ids[-1]
        return self._adjacent_occupied_move(hand_of_cards, origin_idx)

    def _phase2_random_nasi_opener_id(self, hand_of_cards: list[Card]) -> int:
        candidate_ids = [
            idx
            for idx in self._matching_card_ids(hand_of_cards, NASI_TEMPLATES)
            if hand_of_cards[idx].card_rank not in {CardRanks.SILVER, CardRanks.GOLD}
            or not self._card_matches_any(hand_of_cards[idx], ("nasi_stun",))
        ]
        if candidate_ids:
            return min(candidate_ids, key=lambda idx: (hand_of_cards[idx].card_rank.value, -idx))

        fallback_ids = self._matching_card_ids(hand_of_cards, NASI_TEMPLATES)
        if fallback_ids:
            return min(fallback_ids, key=lambda idx: (hand_of_cards[idx].card_rank.value, -idx))
        return -1

    def _activate_escalin_talent_or_reset(self, context_label: str) -> bool:
        screenshot, window_location = capture_window()
        marker_was_visible = self._dogs_talent_marker_visible(screenshot)
        for attempt in range(1, 4):
            print(f"Dogs Floor 4 whale mode: clicking Escalin talent for {context_label} (attempt {attempt}/3).")
            click_im(Coordinates.get_coordinates("talent"), window_location)

            deadline = time.perf_counter() + 1.2
            while time.perf_counter() < deadline:
                time.sleep(0.08)
                screenshot, _ = capture_window()
                if not self._dogs_talent_marker_visible(screenshot):
                    print(f"Dogs Floor 4 whale mode: confirmed Escalin talent for {context_label}.")
                    time.sleep(2.5)
                    return True

            if not marker_was_visible:
                print(
                    "Dogs Floor 4 whale mode: the Dogs talent marker was not visible before the click, "
                    "so proceeding after the normal talent delay."
                )
                time.sleep(2.5)
                return True

        self.request_fight_reset(
            f"Dogs Floor 4 whale mode: expected Escalin talent before {context_label}, but the button was not found."
        )
        return False

    @staticmethod
    def _dogs_talent_marker_visible(screenshot) -> bool:
        return find(vio.dogs_escalin_talent, screenshot, threshold=0.75)

    def _adjacent_occupied_move(self, hand_of_cards: list[Card], origin_idx: int) -> list[int] | None:
        if not (0 <= origin_idx < len(hand_of_cards)):
            return None
        for step in range(1, len(hand_of_cards)):
            for target_idx in (origin_idx + step, origin_idx - step):
                if not (0 <= target_idx < len(hand_of_cards)):
                    continue
                if hand_of_cards[target_idx].card_type in (CardTypes.NONE, CardTypes.GROUND):
                    continue
                return [origin_idx, target_idx]
        return None

    def _best_card_from_priority(
        self,
        hand_of_cards: list[Card],
        priorities: Sequence[Sequence[str]],
        *,
        exclude_ids: set[int] | None = None,
    ) -> int:
        blocked = exclude_ids or set()
        for template_names in priorities:
            matching_ids = [idx for idx in self._matching_card_ids(hand_of_cards, template_names) if idx not in blocked]
            if matching_ids:
                return matching_ids[-1]
        return -1

    def _turn_has_any(
        self,
        picked_cards: list[Card],
        template_names: Sequence[str],
        *,
        ranks: Sequence[CardRanks] | None = None,
    ) -> bool:
        return self._turn_match_count(picked_cards, template_names, ranks=ranks) > 0

    def _turn_match_count(
        self,
        picked_cards: list[Card],
        template_names: Sequence[str],
        *,
        ranks: Sequence[CardRanks] | None = None,
    ) -> int:
        allowed_ranks = frozenset(ranks) if ranks is not None else None
        count = 0
        for card in picked_cards:
            if card.card_image is None:
                continue
            if allowed_ranks is not None and card.card_rank not in allowed_ranks:
                continue
            if self._card_matches_any(card, template_names):
                count += 1
        return count

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        if phase == 1 and DogsFloor4WhaleBattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        DogsFloor4WhaleBattleStrategy._last_phase_seen = phase

        return self._get_next_card_index_whale(hand_of_cards, picked_cards, phase, card_turn=card_turn)

    def _best_matching_card(
        self,
        hand_of_cards: list[Card],
        template_names: Sequence[str],
        *,
        ranks: Sequence[CardRanks] | None = None,
    ) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names, ranks=ranks)
        return matching_ids[-1] if matching_ids else -1

    def _matching_card_ids(
        self,
        hand_of_cards: list[Card],
        template_names: Sequence[str],
        *,
        ranks: Sequence[CardRanks] | None = None,
        include_unplayable: bool = False,
    ) -> list[int]:
        """Return matching card indices sorted by ``(rank, index)`` ascending.

        By default this only returns cards that are currently playable by the
        generic strategy. Set ``include_unplayable=True`` when phase logic needs
        to inspect matching cards regardless of their current ``card_type``.
        """
        allowed_ranks = frozenset(ranks) if ranks is not None else None
        blocked_types = () if include_unplayable else (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
        matching_ids = [
            idx
            for idx, card in enumerate(hand_of_cards)
            if card.card_type not in blocked_types
            and self._card_matches_any(card, template_names)
            and (allowed_ranks is None or card.card_rank in allowed_ranks)
        ]
        matching_ids.sort(key=lambda idx: (hand_of_cards[idx].card_rank.value, idx))
        return matching_ids

    def _best_merge_drag_indices(
        self,
        hand_of_cards: list[Card],
        templates: Sequence[str],
        *,
        rank: CardRanks | None = None,
        log_label: str | None = None,
    ) -> tuple[int, int] | None:
        """Drag originâ†’target to merge two cards matching ``templates``.

        Scan copy sets matching cards to ATTACK so merge prediction sees them (hand may use GROUND).

        Prefer the rightmost merge: maximize target index b, then origin a (lexicographic on (b, a)).
        """
        n = len(hand_of_cards)
        if n < 2:
            return None
        scan = deepcopy(hand_of_cards)
        for card in scan:
            if self._card_matches_any(card, templates):
                card.card_type = CardTypes.ATTACK
        best: tuple[int, int] | None = None
        for a in range(n - 1):
            for b in range(a + 1, n):
                ca, cb = scan[a], scan[b]
                if not self._card_matches_any(ca, templates):
                    continue
                if not self._card_matches_any(cb, templates):
                    continue
                if rank is not None and (ca.card_rank != rank or cb.card_rank != rank):
                    continue
                if not determine_card_merge(ca, cb):
                    continue
                if best is None or (b, a) > (best[1], best[0]):
                    best = (a, b)
        if best is not None:
            label = log_label or "merge"
            print(f"Dragging {label} {best[0]} â†’ {best[1]}")
        return best

    def _card_matches_any(self, card: Card, template_names: Sequence[str]) -> bool:
        if card.card_image is None:
            return False
        for template_name in template_names:
            vision = getattr(vio, template_name, None)
            if vision is None:
                continue
            if find(vision, card.card_image):
                return True
        return False

    def _card_template_name(self, card: Card, template_names: Sequence[str]) -> str | None:
        return next((template_name for template_name in template_names if self._card_matches_any(card, (template_name,))), None)

    def estimate_auto_merge_count_after_play(self, hand_of_cards: list[Card], played_idx: int) -> int:
        if not (0 <= played_idx < len(hand_of_cards)):
            return 0

        simulated_cards = []
        for idx, card in enumerate(hand_of_cards):
            if idx == played_idx or card.card_type in {CardTypes.NONE, CardTypes.GROUND}:
                continue
            template_name = self._card_template_name(card, MERGE_GUARD_TEMPLATES)
            simulated_cards.append({"template_name": template_name, "card_rank": card.card_rank})

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
                simulated_cards[cursor] = {"template_name": left_card["template_name"], "card_rank": next_rank}
                del simulated_cards[cursor + 1]
                merge_count += 1
                cursor = max(0, cursor - 1)
                continue
            cursor += 1

        return merge_count





