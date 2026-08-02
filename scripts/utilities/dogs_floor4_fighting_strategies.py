import time
from collections.abc import Sequence
from copy import copy, deepcopy
from typing import Final

import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import (
    capture_window,
    click_im,
    determine_card_merge,
    find,
    find_and_click,
)

ESCALIN_TEMPLATES: Final[tuple[str, ...]] = ("escalin_st", "escalin_aoe", "escalin_ult")
ROXY_TEMPLATES: Final[tuple[str, ...]] = ("roxy_st", "roxy_aoe", "roxy_ult")
NASI_TEMPLATES: Final[tuple[str, ...]] = ("nasi_heal", "nasi_stun", "nasi_ult")
THONAR_TEMPLATES: Final[tuple[str, ...]] = ("thonar_stance", "thonar_gauge", "thonar_ult")
STANCE_CONTROL_TEMPLATES: Final[tuple[str, ...]] = ("nasi_stun", "thonar_stance", "b_thonar_stance")
# Single-target gauge templates (thonar_gauge, cusack_gauge): same cap-removal / merge / GROUND rules as each other.
ST_GAUGE_TEMPLATES: Final[tuple[str, ...]] = ("thonar_gauge", "cusack_gauge")
AOE_GAUGE_TEMPLATES: Final[tuple[str, ...]] = ("lillia_aoe", "b_thonar_gauge")


class DogsFloor4BattleStrategy(IBattleStrategy):
    """Dogs Floor 4: per-phase hooks; default card picks from SmarterBattleStrategy."""

    _phase_initialized = set()
    _last_phase_seen = None
    lillia_in_team = False
    roxy_in_team = False
    b_thonar_in_team = False
    taunt_removed = True

    removed_damage_cap = False
    # Minimum phase_turn index where Escalin/Roxy HAM is allowed; block while phase_turn < this (-1 = unset).
    _defer_ham_cards_until_after_phase_turn = -1

    def _initialize_static_variables(self):
        DogsFloor4BattleStrategy._phase_initialized = set()
        DogsFloor4BattleStrategy._last_phase_seen = None
        DogsFloor4BattleStrategy.removed_damage_cap = False
        DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn = -1
        DogsFloor4BattleStrategy.taunt_removed = True

    def reset_run_state(self, *, lillia_in_team=False, roxy_in_team=False, b_thonar_in_team=False):
        """Called from DogsFloor4Fighter.run before the fight loop."""
        print(
            "Resetting run state with Lillia in team:",
            lillia_in_team,
            "Roxy in team:",
            roxy_in_team,
            "and Blue Thonar in team:",
            b_thonar_in_team,
        )
        DogsFloor4BattleStrategy.lillia_in_team = lillia_in_team
        DogsFloor4BattleStrategy.roxy_in_team = roxy_in_team
        DogsFloor4BattleStrategy.b_thonar_in_team = b_thonar_in_team
        self._initialize_static_variables()

    def _uses_aoe_gauge_strategy(self) -> bool:
        """Whether this team clears the phase-3 cap with one AOE-style gauge card."""
        return type(self).lillia_in_team or type(self).b_thonar_in_team

    def _aoe_gauge_templates(self) -> tuple[str, ...]:
        """Return the one-card gauge-removal template for the active team variant."""
        if type(self).b_thonar_in_team:
            return AOE_GAUGE_TEMPLATES[1:]
        if type(self).lillia_in_team:
            return AOE_GAUGE_TEMPLATES[:1]
        return ()

    def _gauge_removal_templates(self) -> tuple[str, ...]:
        return (*ST_GAUGE_TEMPLATES, *self._aoe_gauge_templates())

    def _stance_control_card_ids(
        self, hand_of_cards: list[Card], *, include_unplayable: bool = False
    ) -> list[int]:
        """Find eligible stance cancels for the active team.

        Nasiens and original Thonar require SILVER/GOLD. Blue Thonar's stance
        cancel follows the same timing but is also valid at BRONZE.
        """
        high_ranks = (CardRanks.SILVER, CardRanks.GOLD)
        high_rank_ids = self._matching_card_ids(
            hand_of_cards,
            STANCE_CONTROL_TEMPLATES[:2],
            ranks=high_ranks,
            include_unplayable=include_unplayable,
        )
        if not type(self).b_thonar_in_team:
            return high_rank_ids

        blue_ids = self._matching_card_ids(
            hand_of_cards,
            STANCE_CONTROL_TEMPLATES[2:],
            include_unplayable=include_unplayable,
        )
        return sorted(
            (*high_rank_ids, *blue_ids), key=lambda idx: (hand_of_cards[idx].card_rank.value, idx)
        )

    def _maybe_reset(self, phase_id: str):
        if phase_id not in DogsFloor4BattleStrategy._phase_initialized:
            DogsFloor4BattleStrategy._phase_initialized.add(phase_id)

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        if phase == 1 and DogsFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        DogsFloor4BattleStrategy._last_phase_seen = phase

        ## Common logic -- Protect gauge removal cards at all costs (non-AOE-gauge teams only)!

        if not self._uses_aoe_gauge_strategy():
            # Mark ST gauge cards GROUND so Smarter skips them unless phase logic explicitly plays them.
            ids = [i for i, c in enumerate(hand_of_cards) if self._card_matches_any(c, ST_GAUGE_TEMPLATES)]
            if ids:
                n_gold = sum(bool(hand_of_cards[i].card_rank == CardRanks.GOLD) for i in ids)
                if n_gold <= 1:
                    # Single (or no) gold: reserve every ST gauge — nothing safe to leave playable.
                    to_ground = ids
                else:
                    # Two+ golds: reserve only the two best ranks if that pair is both gold; else reserve all.
                    top2 = sorted(ids, key=lambda j: (hand_of_cards[j].card_rank.value, j), reverse=True)[:2]
                    to_ground = top2 if all(hand_of_cards[j].card_rank == CardRanks.GOLD for j in top2) else ids
                for i in to_ground:
                    hand_of_cards[i].card_type = CardTypes.GROUND

        else:
            # AOE-gauge teams: save the best card in phases 1/2, but hide all in phase 3 until cap-removal logic uses one.
            aoe_gauge_ids = self._matching_card_ids(
                hand_of_cards,
                self._aoe_gauge_templates(),
                include_unplayable=True,
            )
            if phase == 3:
                for i in aoe_gauge_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND
            elif aoe_gauge_ids:
                hand_of_cards[aoe_gauge_ids[-1]].card_type = CardTypes.GROUND

        # Phase-specify logic here

        if phase == 1:
            return self.get_next_card_index_phase1(hand_of_cards, picked_cards, card_turn=card_turn)
        if phase == 2:
            return self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn=card_turn)
        return self.get_next_card_index_phase3(hand_of_cards, picked_cards, card_turn=card_turn)

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_1")

        # Let's start with Escalin's talent only on turn 2-onwards
        if IBattleStrategy.phase_turn > 1:
            screenshot, window_location = capture_window()
            if find_and_click(vio.talent_escalin, screenshot, window_location, threshold=0.7):
                print("Phase 1: activating Escalin talent!")
                time.sleep(2.5)

        # First, play one eligible stance-control card on odd turns; otherwise hide it from Smarter.
        attack_debuff_ids = self._stance_control_card_ids(hand_of_cards)
        played_attack_debuff_ids = self._stance_control_card_ids(picked_cards)
        if attack_debuff_ids:
            last_ad = attack_debuff_ids[-1]
            even_phase_turn = IBattleStrategy.phase_turn % 2 == 0
            # Even turns: disable stance cancel. Odd + already played one: ground another. Odd + none played: play one.
            if even_phase_turn or played_attack_debuff_ids:
                hand_of_cards[last_ad].card_type = CardTypes.GROUND
                print("Disabling stance cancel cards.")
            else:
                print("Playing a stance-control card to remove stance!")
                return last_ad

        # Phase 1: First turn, play a sequence of cards
        if IBattleStrategy.phase_turn == 1:

            if DogsFloor4BattleStrategy.roxy_in_team:
                cusack_cleave_id = self._best_matching_card(hand_of_cards, ("cusack_cleave",))
                if cusack_cleave_id != -1:
                    print("Playing cusack cleave")
                    return cusack_cleave_id

                roxy_aoe_already_picked = bool(self._matching_card_ids(picked_cards, ("roxy_aoe",)))
                if not roxy_aoe_already_picked:
                    best_id = self._best_matching_card(hand_of_cards, ("roxy_aoe",))
                    if best_id != -1:
                        print("Playing roxy aoe")
                        return best_id

                roxy_st_already_picked = bool(self._matching_card_ids(picked_cards, ("roxy_st",)))
                if not roxy_st_already_picked:
                    best_id = self._best_matching_card(hand_of_cards, ("roxy_st",))
                    if best_id != -1:
                        print("Playing roxy st")
                        return best_id

                escalin_aoe_already_picked = bool(self._matching_card_ids(picked_cards, ("escalin_aoe",)))
                if not escalin_aoe_already_picked and card_turn == 3:
                    print("Playing escalin aoe")
                    return self._best_matching_card(hand_of_cards, ("escalin_aoe",))

            elif DogsFloor4BattleStrategy.lillia_in_team:
                if heal_ids := self._matching_card_ids(hand_of_cards, ("nasi_heal",)):
                    print("Playing nasi heal")
                    return heal_ids[-1]

                if thonar_gauge_ids := self._matching_card_ids(hand_of_cards, ("thonar_gauge",)):
                    print("Playing thonar gauge")
                    return thonar_gauge_ids[-1]

                if lillia_st_ids := self._matching_card_ids(hand_of_cards, ("lillia_st",)):
                    print("Playing lillia st")
                    return lillia_st_ids[-1]

                print("Desired card not found...")

        # Disable stance cancel cards even if level 1
        stance_cancel_ids = self._matching_card_ids(
            hand_of_cards, STANCE_CONTROL_TEMPLATES, include_unplayable=True
        )
        for i in stance_cancel_ids:
            hand_of_cards[i].card_type = CardTypes.DISABLED
            print("Disabling future stance cancel cards.")

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_2")

        print(f"Phase 2: phase turn {IBattleStrategy.phase_turn}")

        nasiens_ids = self._matching_card_ids(hand_of_cards, NASI_TEMPLATES)
        if card_turn == 0:
            has_nasiens_ult = any(self._card_matches_any(hand_of_cards[i], ("nasi_ult",)) for i in nasiens_ids)

            # If we still have no nasi_ult in hand, try to reshuffle: move the first non-GROUND Nasiens card one slot right.
            if not has_nasiens_ult and nasiens_ids:
                print("Moving Nasiens card to get ult...")
                return [nasiens_ids[-1], nasiens_ids[-1] + 1]

            if not self._uses_aoe_gauge_strategy():
                # On the first pick only, spend one pick merging any available gauge-removal pair.
                drag = self._best_merge_drag_indices(hand_of_cards, ST_GAUGE_TEMPLATES, log_label="phase 2 gauge merge")
                if drag is not None:
                    return drag

        screenshot, _ = capture_window()
        if find(vio.freeze_icon, screenshot):
            nasiens_ult_ids = self._matching_card_ids(hand_of_cards, ("nasi_ult",))
            if len(nasiens_ult_ids) > 0:
                print("Unfreezing with Nasiens ult.")
                return nasiens_ult_ids[-1]

        # Play one eligible stance-control card on odd turns; otherwise hide it from Smarter.
        if attack_debuff_ids := self._stance_control_card_ids(hand_of_cards):
            played_attack_debuff_ids = self._stance_control_card_ids(picked_cards)
            last_ad = attack_debuff_ids[-1]
            # Even turns: disable stance cancel. Odd + already played one: ground another. Odd + none played: play one.
            if IBattleStrategy.phase_turn % 2 == 0 or played_attack_debuff_ids:
                hand_of_cards[last_ad].card_type = CardTypes.GROUND
                print("Disabling stance cancel cards.")
            else:
                print("Playing a stance-control card to remove stance!")
                return last_ad

        # Tuck one Nasiens (prefer heal); never GROUND nasi_ult — Smarter plays it when appropriate.
        # include_unplayable: still tuck heal/stun if already DISABLED/GROUND (template match only).
        if heal_ids := self._matching_card_ids(hand_of_cards, ("nasi_heal",), include_unplayable=True):
            print("Disabling Nasiens heal.")
            hand_of_cards[heal_ids[-1]].card_type = CardTypes.GROUND
        elif stun_ids := self._matching_card_ids(
            hand_of_cards, STANCE_CONTROL_TEMPLATES, include_unplayable=True
        ):
            print("Disabling Nasiens stun.")
            hand_of_cards[stun_ids[-1]].card_type = CardTypes.GROUND

        # Legacy Roxy teams: tuck one SILVER/GOLD roxy_st so Smarter skips it (same pattern as _smarter_phase3).
        roxy_st_hi = (CardRanks.SILVER, CardRanks.GOLD)
        if type(self).roxy_in_team and not self._uses_aoe_gauge_strategy():
            if roxy_st_saveable := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=roxy_st_hi,
                include_unplayable=True,
            ):
                hand_of_cards[roxy_st_saveable[-1]].card_type = CardTypes.GROUND
        # All-GROUND confuses downstream; unstick one SILVER/GOLD roxy_st to DISABLED if needed.
        if (
            not self._uses_aoe_gauge_strategy()
            and hand_of_cards
            and all(c.card_type == CardTypes.GROUND for c in hand_of_cards)
        ):
            if rx := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=roxy_st_hi,
                include_unplayable=True,
            ):
                hand_of_cards[rx[0]].card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        """Phase turns are 1-based started-turn counters everywhere, including phase 3."""
        self._maybe_reset("phase_3")

        print(f"Phase 3: phase turn {IBattleStrategy.phase_turn}")
        if IBattleStrategy.phase_turn % 2 == 0 and card_turn == 0:
            print("Dog is putting up a taunt...")
            DogsFloor4BattleStrategy.taunt_removed = False

        nasiens_ult_ids = self._matching_card_ids(hand_of_cards, ("nasi_ult",))
        if nasiens_ult_ids and IBattleStrategy.phase_turn <= 2:
            return nasiens_ult_ids[-1]

        # If we're on the first turn, only force Nasiens setup when no ult is
        # available anywhere in this turn yet: neither still in hand nor already queued.
        nasiens_ult_available_this_turn = bool(
            nasiens_ult_ids or self._matching_card_ids(picked_cards, ("nasi_ult",))
        )
        if IBattleStrategy.phase_turn == 1 and not nasiens_ult_available_this_turn:
            nasi_ids = self._matching_card_ids(
                hand_of_cards, ("nasi_heal", "nasi_stun", "nasi_ult"), include_unplayable=True
            )
            for i, card in enumerate(hand_of_cards):
                # First, disable all cards that are not Nasiens cards
                if i not in nasi_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND

            if card_turn < 3 and nasi_ids:
                print("Moving Nasiens card to ensure ult...")
                return [nasi_ids[-1], nasi_ids[-1] + 1]

        # Reserve ST gauge cards unless phase-3 logic explicitly plays them.
        st_gauge_ids = [i for i, card in enumerate(hand_of_cards) if self._card_matches_any(card, ST_GAUGE_TEMPLATES)]
        for i in st_gauge_ids:
            hand_of_cards[i].card_type = CardTypes.GROUND

        # Pre-cap Roxy: BRONZE roxy_st merge when hand has no SILVER/GOLD roxy_st.
        # SILVER/GOLD tuck for Smarter is in _smarter_phase3.
        if (
            not DogsFloor4BattleStrategy.removed_damage_cap
            and not DogsFloor4BattleStrategy.taunt_removed
            and type(self).roxy_in_team
            and not self._uses_aoe_gauge_strategy()
        ):
            if roxy_st_ids := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=(CardRanks.SILVER, CardRanks.GOLD),
            ):
                DogsFloor4BattleStrategy.taunt_removed = True
                print("Removing taunt with Roxy!")
                return roxy_st_ids[-1]

            # We haven't removed the taunt and don't have a good Roxy ST saved to remove it...
            drag = self._best_merge_drag_indices(
                hand_of_cards,
                ("roxy_st",),
                rank=CardRanks.BRONZE,
                log_label="roxy_st BRONZE merge",
            )
            if drag is not None:
                return drag

        # Early turns: wait before damage-cap removal. Legacy teams can merge ST gauge cards;
        # AOE-gauge teams must not spend their one-card removal before turn 3.
        if IBattleStrategy.phase_turn <= 2:
            if not self._uses_aoe_gauge_strategy():
                drag = self._best_merge_drag_indices(
                    hand_of_cards, ST_GAUGE_TEMPLATES, log_label="gauge merge (insufficient gold)"
                )
                if drag is not None:
                    self._maybe_activate_escalin_before_gauge_merge(hand_of_cards, drag, card_turn=card_turn)
                    return drag

            return self._smarter_phase3(hand_of_cards, picked_cards)

        # Mid/late phase 3: either remove the damage cap or go HAM after it is gone.
        has_damage_cap = not DogsFloor4BattleStrategy.removed_damage_cap
        if has_damage_cap:
            screenshot, window_location = capture_window()
            # First, check if we've played enough
            played_st_gauge_ids = self._matching_card_ids(
                picked_cards,
                ST_GAUGE_TEMPLATES,
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            played_aoe_gauge_ids = self._matching_card_ids(
                picked_cards,
                self._aoe_gauge_templates(),
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            if (
                (not type(self).b_thonar_in_team and len(played_st_gauge_ids) >= 2)
                or played_aoe_gauge_ids
            ):
                DogsFloor4BattleStrategy.removed_damage_cap = True
                DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn = IBattleStrategy.phase_turn + 1
                return self._smarter_phase3(hand_of_cards, picked_cards)

            st_gauge_ids = self._matching_card_ids(
                hand_of_cards,
                ST_GAUGE_TEMPLATES,
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            aoe_gauge_ids = self._matching_card_ids(
                hand_of_cards,
                self._aoe_gauge_templates(),
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            print(
                "These many gold ST gauge and AOE gauge cards available:",
                len(st_gauge_ids),
                len(aoe_gauge_ids),
            )

            # Blue Thonar clears the cap exclusively with her gauge card. Never
            # fall back to the legacy two-card ST gauge route when it is missing.
            if type(self).b_thonar_in_team:
                if aoe_gauge_ids:
                    DogsFloor4BattleStrategy.removed_damage_cap = True
                    DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn = (
                        IBattleStrategy.phase_turn + 1
                    )
                    print("Playing a GOLD Blue Thonar gauge card!")
                    return aoe_gauge_ids[-1]
                return self._smarter_phase3(hand_of_cards, picked_cards)

            # Count GOLD ST gauge in hand plus already played this turn (picked_cards).
            if not aoe_gauge_ids and (len(played_st_gauge_ids) + len(st_gauge_ids)) < 2:
                drag = self._best_merge_drag_indices(
                    hand_of_cards, ST_GAUGE_TEMPLATES, log_label="gauge merge (insufficient gold)"
                )
                if drag is not None:
                    self._maybe_activate_escalin_before_gauge_merge(
                        hand_of_cards,
                        drag,
                        card_turn=card_turn,
                        played_gold_st_gauge_count=len(played_st_gauge_ids),
                        screenshot=screenshot,
                        window_location=window_location,
                    )
                    return drag
                print("Not enough gold cards to remove gauges...")
                print(f"{len(played_st_gauge_ids)} GOLD played and {len(st_gauge_ids)} GOLD in hand.")
                return self._smarter_phase3(hand_of_cards, picked_cards)

            if (
                not self._uses_aoe_gauge_strategy()  # Legacy teams need Escalin talent to remove taunt with Roxy.
                and not DogsFloor4BattleStrategy.taunt_removed
                and find_and_click(vio.talent_escalin, screenshot, window_location, threshold=0.7)
                and card_turn == 0
            ):
                print("Phase 3: activating Escalin talent!")
                DogsFloor4BattleStrategy.taunt_removed = True
                time.sleep(2.5)

            if len(played_st_gauge_ids) == 1:
                # Gotta click light dog after we've played the first remove gauge card
                print("Clicking light dog after playing the first remove gauge card!")
                click_im(Coordinates.get_coordinates("light_dog"), window_location)
                time.sleep(1)

            if aoe_gauge_ids:
                DogsFloor4BattleStrategy.removed_damage_cap = True
                DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn = IBattleStrategy.phase_turn + 1
                print("Playing a GOLD AOE gauge card!")
                return aoe_gauge_ids[-1]

            if len(played_st_gauge_ids) <= 1:
                if not DogsFloor4BattleStrategy.taunt_removed:
                    print("We have enough gold cards but taunt isn't removed :(")
                    return self._smarter_phase3(hand_of_cards, picked_cards)

                # Play gold ST gauge cards (two total to clear cap when no AOE gauge card).
                st_gauge_pick_id = st_gauge_ids[-1] if st_gauge_ids else -1
                if st_gauge_pick_id != -1:
                    print("Playing a GOLD ST gauge card!")
                    if len(played_st_gauge_ids) == 1:
                        DogsFloor4BattleStrategy.removed_damage_cap = True
                        DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn = (
                            IBattleStrategy.phase_turn + 1
                        )
                        print(
                            f"Damage cap removed on phase turn {IBattleStrategy.phase_turn}! "
                            f"HAM allowed starting phase turn "
                            f"{DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn}."
                        )
                    return st_gauge_pick_id

        else:
            # Do not use Escalin talent here; it may remove Nasiens buffs.
            for i, card in enumerate(hand_of_cards):
                if self._card_matches_any(card, self._gauge_removal_templates()):
                    hand_of_cards[i].card_type = CardTypes.ATTACK

            # Damage cap not visible: go HAM — play Escalin and Roxy's cards like crazy
            if IBattleStrategy.phase_turn < DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn:

                if nasiens_ult_id := self._matching_card_ids(hand_of_cards, ("nasi_ult",)):
                    return nasiens_ult_id[-1]

                if escalin_ult_ids := self._matching_card_ids(hand_of_cards, ("escalin_ult",)):
                    return escalin_ult_ids[-1]

                print(
                    f"We can't play HAM cards yet! phase_turn={IBattleStrategy.phase_turn}, "
                    f"HAM allowed when phase_turn >= "
                    f"{DogsFloor4BattleStrategy._defer_ham_cards_until_after_phase_turn}."
                )
                return self._smarter_phase3(hand_of_cards, picked_cards)

            print("No more damage cap, let's go HAM!")
            for templates in (
                ("escalin_ult",),
                ("escalin_aoe",),
                ("escalin_st",),
                ("roxy_aoe",),
                ("roxy_st",),
                (
                    "lillia_ult",
                    "roxy_ult",
                    "thonar_ult",
                ),
                self._aoe_gauge_templates(),
            ):
                if ids := self._matching_card_ids(hand_of_cards, templates):
                    return ids[-1]

            if ult_ids := [
                i
                for i, card in enumerate(hand_of_cards)
                if card.card_type == CardTypes.ULTIMATE and not find(vio.nasi_ult, card.card_image)
            ]:
                return ult_ids[-1]

            if att_deb_ids := sorted(
                [
                    i
                    for i, card in enumerate(hand_of_cards)
                    if card.card_type in {CardTypes.ATTACK, CardTypes.ATTACK_DEBUFF}
                ],
                key=lambda idx: (
                    hand_of_cards[idx].card_rank.value,
                    hand_of_cards[idx].card_type != CardTypes.ATTACK,
                    idx,
                ),
            ):
                return att_deb_ids[-1]

        return self._smarter_phase3(hand_of_cards, picked_cards)

    def _smarter_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Adjust the hand, then ask Smarter for the next card index.

        Hides Escalin cards from the default strategy (stance/AOE disabled, ult
        marked as ground). If the damage cap is still active and Roxy is on the
        team, also marks one SILVER or GOLD Roxy ST card as ground so it is not
        chosen until explicit phase-3 logic plays it.
        """
        roxy_st_hi = (CardRanks.SILVER, CardRanks.GOLD)
        escalin_hide_type = CardTypes.GROUND if self._uses_aoe_gauge_strategy() else CardTypes.DISABLED
        # Keep Escalin off Smarter's pick list for this delegation.
        for item in hand_of_cards:
            if self._card_matches_any(item, ("escalin_st", "escalin_aoe")):
                print("Disabling Escalin cards")
                item.card_type = escalin_hide_type
            elif self._card_matches_any(item, ("escalin_ult",)):
                print("Disabling Escalin ult")
                item.card_type = CardTypes.GROUND
        # Pre-cap: hide one high-rank Roxy ST from Smarter until phase-3 logic plays it.
        if (
            type(self).roxy_in_team
            and not self._uses_aoe_gauge_strategy()
            and not DogsFloor4BattleStrategy.removed_damage_cap
        ):
            if roxy_st_saveable := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=roxy_st_hi,
                include_unplayable=True,
            ):
                hand_of_cards[roxy_st_saveable[-1]].card_type = CardTypes.GROUND

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _best_matching_card(
        self,
        hand_of_cards: list[Card],
        template_names: Sequence[str],
        *,
        ranks: Sequence[CardRanks] | None = None,
    ) -> int:
        matching_ids = self._matching_card_ids(hand_of_cards, template_names, ranks=ranks)
        return matching_ids[-1] if matching_ids else -1

    def _maybe_activate_escalin_before_gauge_merge(
        self,
        hand_of_cards: list[Card],
        drag: tuple[int, int] | None,
        *,
        card_turn: int,
        played_gold_st_gauge_count: int = 0,
        screenshot=None,
        window_location=None,
    ) -> None:
        if self._uses_aoe_gauge_strategy():
            # AOE-gauge teams must not remove taunt with Escalin.
            return

        if drag is None or card_turn != 0 or DogsFloor4BattleStrategy.taunt_removed:
            return

        future_hand = deepcopy(hand_of_cards)
        for card in future_hand:
            if self._card_matches_any(card, self._gauge_removal_templates()):
                card.card_type = CardTypes.ATTACK

        future_hand = self._update_hand_of_cards(future_hand, [drag])
        future_gold_st_gauge_ids = self._matching_card_ids(
            future_hand,
            ST_GAUGE_TEMPLATES,
            ranks=(CardRanks.GOLD,),
            include_unplayable=True,
        )
        if played_gold_st_gauge_count + len(future_gold_st_gauge_ids) < 2:
            return

        if screenshot is None or window_location is None:
            screenshot, window_location = capture_window()
        if find_and_click(vio.talent_escalin, screenshot, window_location, threshold=0.7):
            print("Phase 3: activating Escalin talent before gauge merge!")
            DogsFloor4BattleStrategy.taunt_removed = True
            time.sleep(2.5)

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
        """Drag origin→target to merge two cards matching ``templates``.

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
            print(f"Dragging {label} {best[0]} → {best[1]}")
        return best

    def _card_matches_any(self, card: Card, template_names: Sequence[str]) -> bool:
        if card.card_image is None:
            return False
        return any(find(getattr(vio, template_name), card.card_image) for template_name in template_names)
