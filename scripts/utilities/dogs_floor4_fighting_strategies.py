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
STANCE_CONTROL_TEMPLATES: Final[tuple[str, ...]] = ("nasi_stun", "thonar_stance")
# Single-target gauge templates (thonar_gauge, cusack_gauge): same cap-removal / merge / GROUND rules as each other; Lillia AOE separate.
ST_GAUGE_TEMPLATES: Final[tuple[str, ...]] = ("thonar_gauge", "cusack_gauge")
GAUGE_REMOVAL_TEMPLATES: Final[tuple[str, ...]] = (*ST_GAUGE_TEMPLATES, "lillia_aoe")


class DogsFloor4BattleStrategy(IBattleStrategy):
    """Dogs Floor 4: per-phase hooks; default card picks from SmarterBattleStrategy."""

    turn = 0
    _phase_initialized = set()
    _last_phase_seen = None
    lillia_in_team = False
    roxy_in_team = False
    taunt_removed = True

    removed_damage_cap = False
    # Minimum fight_turn index where Escalin/Roxy HAM is allowed; block while fight_turn < this (-1 = unset).
    _defer_ham_cards_until_after_fight_turn = -1

    def _initialize_static_variables(self):
        DogsFloor4BattleStrategy._phase_initialized = set()
        DogsFloor4BattleStrategy._last_phase_seen = None
        DogsFloor4BattleStrategy.removed_damage_cap = False
        DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn = -1
        DogsFloor4BattleStrategy.taunt_removed = True

    def reset_run_state(self, *, lillia_in_team=False, roxy_in_team=False):
        """Called from DogsFloor4Fighter.run before the fight loop."""
        print("Resetting run state with Lillia in team:", lillia_in_team, "and Roxy in team:", roxy_in_team)
        DogsFloor4BattleStrategy.lillia_in_team = lillia_in_team
        DogsFloor4BattleStrategy.roxy_in_team = roxy_in_team
        self._initialize_static_variables()

    def _maybe_reset(self, phase_id: str):
        if phase_id not in DogsFloor4BattleStrategy._phase_initialized:
            DogsFloor4BattleStrategy._phase_initialized.add(phase_id)

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        if phase == 1 and DogsFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        DogsFloor4BattleStrategy._last_phase_seen = phase

        ## Common logic -- Protect gauge removal cards at all costs (non-Lillia teams only)!

        if not type(self).lillia_in_team:
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
            # Lillia teams: save the best AOE in phases 1/2, but hide all AOEs in phase 3 until cap-removal logic uses one.
            lillia_aoe_ids = self._matching_card_ids(
                hand_of_cards,
                ("lillia_aoe",),
                include_unplayable=True,
            )
            if phase == 3:
                for i in lillia_aoe_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND
            elif lillia_aoe_ids:
                hand_of_cards[lillia_aoe_ids[-1]].card_type = CardTypes.GROUND

        # Phase-specify logic here

        if phase == 1:
            return self.get_next_card_index_phase1(hand_of_cards, picked_cards, card_turn=card_turn)
        if phase == 2:
            return self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn=card_turn)
        return self.get_next_card_index_phase3(hand_of_cards, picked_cards, card_turn=card_turn)

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_1")

        # Let's start with Escalin's talent only on turn 2-onwards
        if IBattleStrategy.fight_turn > 1:
            screenshot, window_location = capture_window()
            if find_and_click(vio.talent_escalin, screenshot, window_location, threshold=0.7):
                print("Phase 1: activating Escalin talent!")
                time.sleep(2.5)

        # First, play one stance-control card on odd turns; otherwise hide them from Smarter.
        attack_debuff_ids = self._matching_card_ids(hand_of_cards, STANCE_CONTROL_TEMPLATES)
        played_attack_debuff_ids = self._matching_card_ids(picked_cards, STANCE_CONTROL_TEMPLATES)
        if attack_debuff_ids:
            last_ad = attack_debuff_ids[-1]
            even_fight_turn = IBattleStrategy.fight_turn % 2 == 0
            # Even turns: disable stance cancel. Odd + already played one: ground another. Odd + none played: play one.
            if even_fight_turn or played_attack_debuff_ids:
                hand_of_cards[last_ad].card_type = CardTypes.GROUND
                print("Disabling stance cancel cards.")
            else:
                print("Playing a stance-control card to remove stance!")
                return last_ad

        # Phase 1: First turn, play a sequence of cards
        if IBattleStrategy.fight_turn == 1:

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
        stance_cancel_ids = self._matching_card_ids(hand_of_cards, ("nasi_stun", "thonar_stance"))
        for i in stance_cancel_ids:
            hand_of_cards[i].card_type = CardTypes.DISABLED
            print("Disabling future stance cancel cards.")

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        self._maybe_reset("phase_2")

        print(f"Phase 2: fight turn {IBattleStrategy.fight_turn}")

        nasiens_ids = self._matching_card_ids(hand_of_cards, NASI_TEMPLATES)
        if card_turn == 0:
            has_nasiens_ult = any(self._card_matches_any(hand_of_cards[i], ("nasi_ult",)) for i in nasiens_ids)

            # If we still have no nasi_ult in hand, try to reshuffle: move the first non-GROUND Nasiens card one slot right.
            if not has_nasiens_ult and nasiens_ids:
                print("Moving Nasiens card to get ult...")
                return [nasiens_ids[-1], nasiens_ids[-1] + 1]

            if not type(self).lillia_in_team:
                # On the first pick only, spend one pick merging any available gauge-removal pair.
                drag = self._best_merge_drag_indices(hand_of_cards, ST_GAUGE_TEMPLATES, log_label="phase 2 gauge merge")
                if drag is not None:
                    return drag

        # Play one stance-control card on odd turns; otherwise hide them from Smarter.
        if attack_debuff_ids := self._matching_card_ids(hand_of_cards, STANCE_CONTROL_TEMPLATES):
            played_attack_debuff_ids = self._matching_card_ids(picked_cards, STANCE_CONTROL_TEMPLATES)
            last_ad = attack_debuff_ids[-1]
            # Even turns: disable stance cancel. Odd + already played one: ground another. Odd + none played: play one.
            if IBattleStrategy.fight_turn % 2 == 0 or played_attack_debuff_ids:
                hand_of_cards[last_ad].card_type = CardTypes.GROUND
                print("Disabling stance cancel cards.")
            else:
                print("Playing a stance-control card to remove stance!")
                return last_ad

        # Do not play Nasiens ult: mark it GROUND so SmarterBattleStrategy skips it (same idea as Escalin above).
        for i in nasiens_ids:
            if self._card_matches_any(hand_of_cards[i], ("nasi_ult",)):
                print("Disabling Nasiens ult!")
                hand_of_cards[i].card_type = CardTypes.GROUND

        # Phase 2: Tuck one SILVER/GOLD roxy_st so Smarter skips it (same pattern as _smarter_phase3).
        roxy_st_hi = (CardRanks.SILVER, CardRanks.GOLD)
        if type(self).roxy_in_team:
            if roxy_st_saveable := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=roxy_st_hi,
                include_unplayable=True,
            ):
                hand_of_cards[roxy_st_saveable[-1]].card_type = CardTypes.GROUND
        # All-GROUND confuses downstream; unstick one SILVER/GOLD roxy_st to DISABLED if needed.
        if hand_of_cards and all(c.card_type == CardTypes.GROUND for c in hand_of_cards):
            if rx := self._matching_card_ids(
                hand_of_cards,
                ("roxy_st",),
                ranks=roxy_st_hi,
                include_unplayable=True,
            ):
                hand_of_cards[rx[0]].card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int):
        """Important: In phase 3, fight turns start at 1!"""
        self._maybe_reset("phase_3")

        print(f"Phase 3: fight turn {IBattleStrategy.fight_turn}")
        if IBattleStrategy.fight_turn % 2 == 0 and card_turn == 0:
            print("Dog is putting up a taunt...")
            DogsFloor4BattleStrategy.taunt_removed = False

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

        # Pre-cap: play Nasiens ult before the gauge-removal turns.
        nasiens_ult_id = self._matching_card_ids(hand_of_cards, ("nasi_ult",))
        if nasiens_ult_id and IBattleStrategy.fight_turn <= 2:
            return nasiens_ult_id[-1]

        # Early turns: prioritize gauge merges, otherwise delegate to Smarter immediately.
        if IBattleStrategy.fight_turn <= 2 and not DogsFloor4BattleStrategy.lillia_in_team:
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
            played_lillia_ids = self._matching_card_ids(
                picked_cards,
                ("lillia_aoe",),
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            if len(played_st_gauge_ids) >= 2 or played_lillia_ids:
                DogsFloor4BattleStrategy.removed_damage_cap = True
                DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn = IBattleStrategy.fight_turn + 1
                return self._smarter_phase3(hand_of_cards, picked_cards)

            st_gauge_ids = self._matching_card_ids(
                hand_of_cards,
                ST_GAUGE_TEMPLATES,
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            lillia_aoe_ids = self._matching_card_ids(
                hand_of_cards,
                ("lillia_aoe",),
                ranks=(CardRanks.GOLD,),
                include_unplayable=True,
            )
            print(
                "These many gold ST gauge and lillia_aoe cards available:",
                len(st_gauge_ids),
                len(lillia_aoe_ids),
            )

            # Count GOLD ST gauge in hand plus already played this turn (picked_cards).
            if not lillia_aoe_ids and (len(played_st_gauge_ids) + len(st_gauge_ids)) < 2:
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
                not type(self).lillia_in_team  # We need Escalin talent to remove taunt with Roxy
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

            if lillia_aoe_ids:
                DogsFloor4BattleStrategy.removed_damage_cap = True
                DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn = IBattleStrategy.fight_turn + 1
                print("Playing a GOLD Lillia card!")
                return lillia_aoe_ids[-1]

            if len(played_st_gauge_ids) <= 1:
                if not DogsFloor4BattleStrategy.taunt_removed:
                    print("We have enough gold cards but taunt isn't removed :(")
                    return self._smarter_phase3(hand_of_cards, picked_cards)

                # Play gold ST gauge cards (two total to clear cap when no Lillia AOE).
                st_gauge_pick_id = st_gauge_ids[-1] if st_gauge_ids else -1
                if st_gauge_pick_id != -1:
                    print("Playing a GOLD ST gauge card!")
                    if len(played_st_gauge_ids) == 1:
                        DogsFloor4BattleStrategy.removed_damage_cap = True
                        DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn = (
                            IBattleStrategy.fight_turn + 1
                        )
                        print(
                            f"Damage cap removed on fight turn {IBattleStrategy.fight_turn}! "
                            f"HAM allowed starting fight turn "
                            f"{DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn}."
                        )
                    return st_gauge_pick_id

        else:
            # Do not use Escalin talent here; it may remove Nasiens buffs.
            for i, card in enumerate(hand_of_cards):
                if self._card_matches_any(card, GAUGE_REMOVAL_TEMPLATES):
                    hand_of_cards[i].card_type = CardTypes.ATTACK

            # Damage cap not visible: go HAM — play Escalin and Roxy's cards like crazy
            if IBattleStrategy.fight_turn < DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn:

                if nasiens_ult_id := self._matching_card_ids(hand_of_cards, ("nasi_ult",)):
                    return nasiens_ult_id[-1]

                if escalin_ult_ids := self._matching_card_ids(hand_of_cards, ("escalin_ult",)):
                    return escalin_ult_ids[-1]

                print(
                    f"We can't play HAM cards yet! fight_turn={IBattleStrategy.fight_turn}, "
                    f"HAM allowed when fight_turn >= "
                    f"{DogsFloor4BattleStrategy._defer_ham_cards_until_after_fight_turn}."
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
                ("lillia_aoe",),
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
        escalin_hide_type = CardTypes.GROUND if type(self).lillia_in_team else CardTypes.DISABLED
        # Keep Escalin off Smarter's pick list for this delegation.
        for item in hand_of_cards:
            if self._card_matches_any(item, ("escalin_st", "escalin_aoe")):
                print("Disabling Escalin cards")
                item.card_type = escalin_hide_type
            elif self._card_matches_any(item, ("escalin_ult",)):
                print("Disabling Escalin ult")
                item.card_type = CardTypes.GROUND
        # Pre-cap: hide one high-rank Roxy ST from Smarter until phase-3 logic plays it.
        if type(self).roxy_in_team and not DogsFloor4BattleStrategy.removed_damage_cap:
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
        if type(self).lillia_in_team:
            # If we're using Lillia, let's not remove taunt with Escalin ever!
            return

        if drag is None or card_turn != 0 or DogsFloor4BattleStrategy.taunt_removed:
            return

        future_hand = deepcopy(hand_of_cards)
        for card in future_hand:
            if self._card_matches_any(card, GAUGE_REMOVAL_TEMPLATES):
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
