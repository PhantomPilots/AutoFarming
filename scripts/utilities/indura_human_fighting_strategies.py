import time

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, crop_region, find

# ─── Card catalogue ───────────────────────────────────────────────────────────
# Each entry: (vision_image, display_name, attack_type)
# attack_type: "melee" | "ranged" | "ult"
# Ults always bypass melee/ranged evasion.

_CARD_INFO = [
    (vio.indura_jin_st, "jinwoo st", "melee"),
    (vio.indura_jin_aoe, "jinwoo aoe", "ranged"),
    (vio.indura_jin_ult, "jinwoo ult", "ult"),
    (vio.roxy_st, "roxy att", "melee"),
    (vio.roxy_aoe, "roxy aoe", "ranged"),
    (vio.roxy_ult, "roxy ult", "ult"),
    (vio.indura_sho_att, "sho att", "melee"),
    (vio.indura_sho_aoe, "sho aoe", "ranged"),
    (vio.indura_sho_ult, "sho ult", "ult"),
    (vio.indura_freyr_att, "freyr att", "ranged"),
    (vio.indura_freyr_aoe, "freyr aoe", "ranged"),
    (vio.freyr_ult, "freyr ult", "ult"),
    (vio.indura_ban_att, "ban att", "ranged"),
    (vio.indura_ban_aoe, "ban aoe", "ranged"),
    (vio.indura_ban_ult, "ban ult", "ult"),
    (vio.indura_enjin_att, "enjin att", "melee"),
    (vio.indura_enjin_aoe, "enjin aoe", "melee"),
    (vio.indura_enjin_ult, "enjin ult", "ult"),
]

_RANK_LABEL = {
    CardRanks.BRONZE.value: "bronze",
    CardRanks.SILVER.value: "silver",
    CardRanks.GOLD.value: "gold",
    CardRanks.ULTIMATE.value: "ult-tier",
}


def _card_label(card: Card, rank_value: int) -> str:
    """Return a human-readable label, e.g. 'silver roxy att [melee]'."""
    rank_str = _RANK_LABEL.get(rank_value, "?")
    for img, name, attack_type in _CARD_INFO:
        if find(img, card.card_image):
            return f"{rank_str} {name} [{attack_type}]"
    return f"{rank_str} {card.card_type.name.lower()} [unknown]"


def _is_freyr_card(card: Card) -> bool:
    return any(
        find(img, card.card_image)
        for img in (
            vio.indura_freyr_att,
            vio.indura_freyr_aoe,
            vio.freyr_ult,
        )
    )


def _is_ban_card(card: Card) -> bool:
    return any(
        find(img, card.card_image)
        for img in (
            vio.indura_ban_att,
            vio.indura_ban_aoe,
            vio.indura_ban_ult,
        )
    )


def _is_enjin_card(card: Card) -> bool:
    return any(
        find(img, card.card_image)
        for img in (
            vio.indura_enjin_att,
            vio.indura_enjin_aoe,
            vio.indura_enjin_ult,
        )
    )


def _is_enjin_attack_card(card: Card) -> bool:
    return any(
        find(img, card.card_image)
        for img in (
            vio.indura_enjin_att,
            vio.indura_enjin_aoe,
        )
    )


def _is_melee_card(card: Card) -> bool:
    return any(atype == "melee" and find(img, card.card_image) for img, _, atype in _CARD_INFO)


def _is_ranged_card(card: Card) -> bool:
    return any(atype == "ranged" and find(img, card.card_image) for img, _, atype in _CARD_INFO)


# ─── Strategy ─────────────────────────────────────────────────────────────────


class InduraHumanBattleStrategy(IBattleStrategy):
    """Battle strategy for the Human-team Indura Death Match.

    Front line : Ban / Jin / Sho / Roxy / Freyr  (Freyr is optional)

    Phase overview
    ──────────────
    Phase 1 — Burst to try to one-shot, with a fixed damage-optimal opening.
              Opening (turn 1, no boss stance up — i.e. we move first):
                play a fixed sequence that supersedes the default logic.
                  · Default team : roxy_att -> sho_att -> sho_aoe
                    (sho_att before sho_aoe makes the AoE hit harder; the two
                     Sho cards self-freeze him, cleansed next turn by freyr_att)
                  · Jinwoo team  : jin_st -> jin_aoe -> roxy_att
                    (auto-selected when any Jinwoo card is seen on the team)
              Stance up (turn 2+, or turn 1 if we moved second):
                play a silver+ freyr_att to nullify the counter (also cleanses
                Sho's freeze), then press damage in the order
                sho_att, roxy_att, sho_aoe, roxy_aoe to clear the phase ASAP.
              No stance on a later turn: freyr_att benched, same damage order.
              Ults remain a fallback after the prioritized cards in every case.

    Phase 2 — Boss is tanky and loses damage reduction each turn.
              Turn 1: check if Sho's potential freeze can be handled — prefer
              freyr_att (cleanses + starts Freyr passive).  If no freyr on the
              team, check whether an ally King or Freyr card is already in the
              played slots and log it; fall through to ban/attack filler.
              Turn 2+ (cleanup): ban falls off AND freyr is avoided — the
              priority is ending the phase fast, so the fixed opening damage
              burst is replicated (an emergency card-seal cleanse still fires).
              Ultimates are held for P3 throughout; released only as a last
              resort if the hand is empty of anything else.

    Phase 3 — Boss is squishy but gains an HP buff if downed too fast.
              Boss applies a melee or ranged evasion buff each turn after the
              first — the ONLY way to clear it is landing an ultimate.
              If no ult is available on card_turn 0, the script waits 5.5s to
              observe whether an ally plays an ult to clear it.  After the wait,
              if evasion is still active, cards are filtered to those that can
              bypass the active restriction (melee cards for ranged evasion,
              ranged cards for melee evasion).
              Turn 1: the boss debuffs the whole team on entry — lead with
              freyr_att when available to cleanse it (team-wide heal), then
              hold ults, observe the teammate, and play attack cards.
              Turn 2+: full-send with roxy_ult / sho_ult, then any other ult.
              Freyr's att and ult carry a built-in cleanse for both the boss's
              card-seal debuff and Sho's freeze.

    Attack types
    ────────────
    Melee : jinwoo st, roxy att, sho att
    Ranged: jinwoo aoe, roxy aoe, sho aoe, freyr att, freyr aoe, ban att, ban aoe
    Ult   : all ultimates (always bypass evasion)

    Sho freeze note
    ───────────────
    If Sho uses two cards in one turn he freezes himself until cleansed.
    Freyr (att or ult), ally King, or ally Freyr cards all provide the cleanse.
    The script checks ally played cards in the 6-slot region for King/Freyr and
    logs what it finds.
    """

    _seen_enjin: bool = False

    # ── Logging helper ────────────────────────────────────────────────────────

    def _play(self, idx: int, hand_of_cards: list[Card], card_ranks: np.ndarray) -> int:
        """Log the identified card and return idx unchanged."""
        label = _card_label(hand_of_cards[idx], int(card_ranks[idx]))
        print(f"[HumanTeam] >> Playing {label}")
        return idx

    # ── Main method ───────────────────────────────────────────────────────────

    def get_next_card_index(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        phase: int = 1,
        card_turn: int = 0,
        **kwargs,
    ) -> int:
        screenshot, _ = capture_window()
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        # Turn number relative to the start of the current phase.
        phase_turn = IBattleStrategy.phase_turn

        print(f"[HumanTeam] phase={phase}  phase_turn={phase_turn}  card_turn={card_turn}")

        # ── Reusable card-index lists (sorted ascending by rank, so [-1] = best) ─
        def ids_where(pred):
            return sorted(
                [i for i, c in enumerate(hand_of_cards) if pred(c)],
                key=lambda idx: card_ranks[idx],
            )

        freyr_ids = ids_where(_is_freyr_card)
        freyr_att_ids = ids_where(lambda c: find(vio.indura_freyr_att, c.card_image))
        freyr_cleanse_ids = ids_where(  # freyr_att + freyr_ult both cleanse
            lambda c: find(vio.indura_freyr_att, c.card_image) or find(vio.freyr_ult, c.card_image)
        )
        ban_ids = ids_where(_is_ban_card)
        ban_aoe_ids = ids_where(lambda c: find(vio.indura_ban_aoe, c.card_image))
        ult_ids = ids_where(lambda c: c.card_type == CardTypes.ULTIMATE)
        enjin_attack_ids = ids_where(_is_enjin_attack_card)

        ENJIN_CARDS_PER_TURN = 2
        enjin_cards_played = sum(1 for c in picked_cards if _is_enjin_card(c))
        enjin_budget_left = enjin_cards_played < ENJIN_CARDS_PER_TURN

        def _best_attack_idx():
            attack_ids = sorted(
                [i for i, c in enumerate(hand_of_cards) if c.card_type == CardTypes.ATTACK],
                key=lambda idx: card_ranks[idx],
            )
            if not attack_ids:
                return None
            if enjin_budget_left:
                preferred = [i for i in attack_ids if _is_enjin_attack_card(hand_of_cards[i])]
            else:
                preferred = [i for i in attack_ids if not _is_enjin_attack_card(hand_of_cards[i])]
            return (preferred or attack_ids)[-1]

        # ── Fixed-sequence helpers ─────────────────────────────────────────
        def _img_in_cards(img, cards) -> bool:
            return any(find(img, c.card_image) for c in cards)

        def _next_in_sequence(sequence_imgs):
            """Index of the first card in `sequence_imgs` that is currently in
            hand AND has not already been played this turn.  Picks the highest
            rank if a card appears more than once.  Returns None if none match —
            the caller then falls through to its default logic.
            """
            for img in sequence_imgs:
                if _img_in_cards(img, picked_cards):
                    continue  # already played this turn — advance the sequence
                matches = sorted(
                    [i for i, c in enumerate(hand_of_cards) if find(img, c.card_image)],
                    key=lambda idx: card_ranks[idx],
                )
                if matches:
                    return matches[-1]
            return None

        # Jinwoo is on the team if any of his cards are seen this turn (hand or
        # already played).  Drives the alternate opening sequence below.
        jin_on_team = any(
            _img_in_cards(img, hand_of_cards) or _img_in_cards(img, picked_cards)
            for img in (vio.indura_jin_st, vio.indura_jin_aoe, vio.indura_jin_ult)
        )

        if phase == 1 and phase_turn == 1 and card_turn == 0:
            InduraHumanBattleStrategy._seen_enjin = False

        enjin_seen_this_pick = any(
            _img_in_cards(img, hand_of_cards) or _img_in_cards(img, picked_cards)
            for img in (vio.indura_enjin_att, vio.indura_enjin_aoe, vio.indura_enjin_ult)
        )
        if enjin_seen_this_pick and not InduraHumanBattleStrategy._seen_enjin:
            print("[HumanTeam] Enjin detected — enabling Enjin priorities")
        InduraHumanBattleStrategy._seen_enjin |= enjin_seen_this_pick
        enjin_on_team = InduraHumanBattleStrategy._seen_enjin

        # Fixed damage-optimal opening burst, shared by the Phase-1 opening turn
        # and the Phase-2 cleanup turn (turn 2+).  Jinwoo team leads with his combo.
        opening_seq = (
            [vio.indura_jin_st, vio.indura_jin_aoe, vio.roxy_st]
            if jin_on_team
            else [vio.roxy_st, vio.indura_sho_att, vio.indura_sho_aoe]
        )

        # ── PHASE 1 ───────────────────────────────────────────────────────
        if phase == 1:
            # Boss stance/counter detection.  When it's up, freyr_att nullifies
            # it (and cleanses Sho's freeze); when it's down on the opening turn
            # we go for the fixed damage-optimal burst instead.
            stance_up = bool(find(vio.snake_f3p2_counter, screenshot))

            # Damage-priority order used once the stance is dealt with (and on
            # later no-stance turns): single-target hits first, then the AoEs.
            DMG_PRIORITY = [
                vio.indura_sho_att,
                vio.roxy_st,
                vio.indura_sho_aoe,
                vio.roxy_aoe,
            ]

            ally_played_stance_cancel = False
            if stance_up:
                six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
                ally_played_stance_cancel = bool(find(vio.mini_king, six_slots))

            if stance_up and not freyr_att_ids and card_turn == 0:
                print("[HumanTeam] P1 stance up, no freyr counter — watching up to 8s for ally cancel...")
                deadline = time.time() + 8
                while time.time() < deadline:
                    screenshot, _ = capture_window()
                    six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
                    stance_up = bool(find(vio.snake_f3p2_counter, screenshot))
                    ally_played_stance_cancel = bool(find(vio.mini_king, six_slots))
                    if not stance_up or ally_played_stance_cancel:
                        break
                    time.sleep(1)
                if not stance_up:
                    print("[HumanTeam] Boss stance cleared — proceeding!")
                elif ally_played_stance_cancel:
                    print("[HumanTeam] Ally stance cancel detected — pressing damage")
                else:
                    print("[HumanTeam] No ally cancel after 8s — single-target lifesteal to tank counter")

            # ── Opening burst: we move first (turn 1, no stance up) ─────────
            # Fixed sequence, supersedes the default ult/attack logic.
            #   Jinwoo team : jin_st  -> jin_aoe -> roxy_att
            #   Default     : roxy_att -> sho_att -> sho_aoe
            # (Default deliberately uses two Sho cards; the resulting self-freeze
            #  is cleansed next turn by the freyr_att stance-nullify.)
            if phase_turn == 1 and not stance_up:
                seq_name = "Jinwoo: jin_st -> jin_aoe -> roxy_att" if jin_on_team else "roxy_att -> sho_att -> sho_aoe"
                print(f"[HumanTeam] P1 opening ({seq_name})")
                seq_idx = _next_in_sequence(opening_seq)
                if seq_idx is not None:
                    return self._play(seq_idx, hand_of_cards, card_ranks)
                # Requested card not in hand this pick — fall back to defaults.
                for idx in freyr_ids + ban_aoe_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # ── Stance up (turn 2+, or turn 1 if we moved second) ───────────
            elif stance_up:
                # A silver+ freyr_att safely absorbs the counter and cleanses
                # Sho's freeze.  Play it once per turn before pressing damage.
                played_freyr_att = _img_in_cards(vio.indura_freyr_att, picked_cards)
                if freyr_att_ids and not played_freyr_att:
                    preferred = [idx for idx in freyr_att_ids if card_ranks[idx] >= CardRanks.SILVER.value]
                    chosen = (preferred or freyr_att_ids)[-1]
                    print("[HumanTeam] P1 stance up — nullifying with freyr att")
                    return self._play(chosen, hand_of_cards, card_ranks)
                if not freyr_att_ids and not ally_played_stance_cancel:
                    lifesteal_idx = _next_in_sequence(
                        [
                            vio.indura_enjin_att,
                            vio.indura_jin_st,
                            vio.roxy_st,
                        ]
                    )
                    if lifesteal_idx is not None:
                        print("[HumanTeam] P1 stance persists — single-target lifesteal (enjin/jin/roxy st)")
                        return self._play(lifesteal_idx, hand_of_cards, card_ranks)
                # Stance handled (or no freyr): clear phase 1 ASAP with damage.
                dmg_idx = _next_in_sequence(DMG_PRIORITY)
                if dmg_idx is not None:
                    print("[HumanTeam] P1 stance handled — pressing damage (sho/roxy)")
                    return self._play(dmg_idx, hand_of_cards, card_ranks)

            # ── No stance on a later turn: keep pressing damage ─────────────
            else:
                # Bench freyr_att (nothing to absorb); leave freyr_ult/aoe live.
                for idx in freyr_att_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED
                dmg_idx = _next_in_sequence(DMG_PRIORITY)
                if dmg_idx is not None:
                    print("[HumanTeam] P1 no stance — pressing damage (sho/roxy)")
                    return self._play(dmg_idx, hand_of_cards, card_ranks)

            # P1 common: ults as fallback, then common attack logic
            if ult_ids:
                return self._play(ult_ids[-1], hand_of_cards, card_ranks)

        # ── PHASE 2 ───────────────────────────────────────────────────────
        elif phase == 2:
            # Hold ults for P3; keep a ref so we can release them as last resort
            held_ult_ids = list(ult_ids)
            for idx in held_ult_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Boss card-seal debuff: cleanse immediately with freyr_att or ult
            if find(vio.block_skill_debuf, screenshot):
                already_cleansed = [c for c in picked_cards if _is_freyr_card(c)]
                if freyr_cleanse_ids and not already_cleansed:
                    print("[HumanTeam] Card-seal debuff (P2) — using freyr cleanse")
                    return self._play(freyr_cleanse_ids[-1], hand_of_cards, card_ranks)

            if phase_turn == 1:
                if enjin_on_team:
                    st_idx = _next_in_sequence(
                        [
                            vio.indura_enjin_att,
                            vio.roxy_st,
                            vio.indura_jin_st,
                            vio.indura_sho_att,
                        ]
                    )
                    if st_idx is not None:
                        print("[HumanTeam] P2 turn 1 — Enjin overheat opening (enjin_st -> single-target burst)")
                        return self._play(st_idx, hand_of_cards, card_ranks)

                # Check if an ally King or Freyr is already in the played slots —
                # either of those can cleanse Sho's potential freeze from P1.
                six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
                ally_has_cleanse = find(vio.mini_king, six_slots) or any(
                    find(img, six_slots) for img in (vio.indura_freyr_att, vio.freyr_ult)
                )
                if ally_has_cleanse:
                    print("[HumanTeam] P2 turn 1 — ally cleanse (King or Freyr) detected in played slots")

                # Lead with freyr_att: cleanses Sho freeze + starts passive stack
                if freyr_att_ids:
                    print("[HumanTeam] P2 turn 1 — playing freyr att (passive + Sho cleanse)")
                    return self._play(freyr_att_ids[-1], hand_of_cards, card_ranks)
                if freyr_ids:
                    print("[HumanTeam] P2 turn 1 — playing freyr card (passive + cleanse)")
                    return self._play(freyr_ids[-1], hand_of_cards, card_ranks)

                # No freyr on team
                if ally_has_cleanse:
                    print("[HumanTeam] P2 turn 1 — no freyr; ally handling Sho cleanse")
                else:
                    print("[HumanTeam] P2 turn 1 — no freyr on team; no ally cleanse detected")

                if ban_ids:
                    return self._play(ban_ids[-1], hand_of_cards, card_ranks)

            else:
                # Turn 2+ (cleanup): ban falls off and freyr is avoided — the
                # priority is clearing the phase ASAP, so replicate the opening
                # damage burst (an emergency card-seal cleanse above still fires
                # if our skills are sealed).
                for idx in ban_ids + freyr_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED
                if enjin_attack_ids and enjin_budget_left:
                    print("[HumanTeam] P2 cleanup turn — leading with enjin attack")
                    return self._play(enjin_attack_ids[-1], hand_of_cards, card_ranks)
                seq_idx = _next_in_sequence(opening_seq)
                if seq_idx is not None:
                    print("[HumanTeam] P2 cleanup turn — opening-style damage burst")
                    return self._play(seq_idx, hand_of_cards, card_ranks)

            # Attack fallback for both P2 turns
            attack_idx = _best_attack_idx()
            if attack_idx is not None:
                return self._play(attack_idx, hand_of_cards, card_ranks)

            # Nothing left: release the held ults
            for idx in held_ult_ids:
                hand_of_cards[idx].card_type = CardTypes.ULTIMATE
            live_ults = [i for i, c in enumerate(hand_of_cards) if c.card_type == CardTypes.ULTIMATE]
            if live_ults:
                print("[HumanTeam] P2 last resort — releasing held ults")
                return self._play(live_ults[-1], hand_of_cards, card_ranks)

        # ── PHASE 3 ───────────────────────────────────────────────────────
        elif phase == 3:
            # ── Evasion pre-check ─────────────────────────────────────────
            # Boss applies melee or ranged evasion each turn after turn 1.
            # Ults always bypass and remove it.  If no ult is available, wait
            # to see if an ally clears it before filtering down to passable cards.
            melee_evasion_up = find(vio.melee_evasion, screenshot)
            ranged_evasion_up = find(vio.ranged_evasion, screenshot)
            has_evasion = melee_evasion_up or ranged_evasion_up
            evasion_passable_only = False  # flag for downstream filtering

            if has_evasion:
                played_ult_this_turn = any(c.card_type == CardTypes.ULTIMATE for c in picked_cards)

                if not played_ult_this_turn:
                    if ult_ids:
                        etype = "melee" if melee_evasion_up else "ranged"
                        print(f"[HumanTeam] P3 {etype} evasion — forcing ult to clear it")
                        return self._play(ult_ids[-1], hand_of_cards, card_ranks)

                    # No ult available — wait on first card pick of the turn
                    if card_turn == 0:
                        print("[HumanTeam] P3 evasion: no ult — waiting 5.5s to observe ally...")
                        time.sleep(5.5)
                        screenshot, _ = capture_window()
                        melee_evasion_up = find(vio.melee_evasion, screenshot)
                        ranged_evasion_up = find(vio.ranged_evasion, screenshot)
                        has_evasion = melee_evasion_up or ranged_evasion_up
                        if not has_evasion:
                            print("[HumanTeam] Ally cleared the evasion — proceeding normally!")
                        else:
                            print("[HumanTeam] Evasion still present after wait — filtering to passable cards")
                            evasion_passable_only = True
                    else:
                        evasion_passable_only = True

            # ── Card-seal debuff ──────────────────────────────────────────
            if find(vio.block_skill_debuf, screenshot):
                already_cleansed = [c for c in picked_cards if _is_freyr_card(c)]
                if freyr_cleanse_ids and not already_cleansed:
                    print("[HumanTeam] Card-seal debuff (P3) — using freyr cleanse")
                    return self._play(freyr_cleanse_ids[-1], hand_of_cards, card_ranks)

            # ── Turn-based priority ───────────────────────────────────────
            if phase_turn == 1:
                # Entering P3, the boss debuffs the whole team.  freyr_att
                # cleanses it for a team-wide heal — lead with it when available.
                played_freyr_att = _img_in_cards(vio.indura_freyr_att, picked_cards)
                if freyr_att_ids and not played_freyr_att:
                    print("[HumanTeam] P3 turn 1 — leading with freyr att (entry-debuff cleanse + team heal)")
                    return self._play(freyr_att_ids[-1], hand_of_cards, card_ranks)
                # Observe the teammate; hold ults; play attack cards
                for idx in ult_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            else:
                # Full-send: roxy_ult and sho_ult hit hardest
                priority_ults = sorted(
                    [
                        i
                        for i, c in enumerate(hand_of_cards)
                        if c.card_type == CardTypes.ULTIMATE
                        and (find(vio.roxy_ult, c.card_image) or find(vio.indura_sho_ult, c.card_image))
                    ],
                    key=lambda idx: card_ranks[idx],
                )
                if priority_ults:
                    print("[HumanTeam] P3 — using priority ult (roxy/sho)")
                    return self._play(priority_ults[-1], hand_of_cards, card_ranks)
                if ult_ids:
                    return self._play(ult_ids[-1], hand_of_cards, card_ranks)

            # ── Evasion fallback: restrict to passable cards ──────────────
            # freyr_att is always included regardless of evasion type: its cleanse
            # fires as a side-effect even if the attack itself is evaded/blocked.
            if evasion_passable_only and has_evasion:
                if melee_evasion_up:
                    passable = sorted(
                        [
                            i
                            for i, c in enumerate(hand_of_cards)
                            if _is_ranged_card(c) or c.card_type == CardTypes.ULTIMATE
                        ],
                        key=lambda idx: card_ranks[idx],
                    )
                    print(f"[HumanTeam] Melee evasion active — ranged/ult only ({len(passable)} options)")
                else:
                    # Ranged evasion: melee + ult passable, PLUS freyr_att for its cleanse value
                    freyr_att_through_evasion = [
                        i for i, c in enumerate(hand_of_cards) if find(vio.indura_freyr_att, c.card_image)
                    ]
                    if freyr_att_through_evasion:
                        print(
                            "[HumanTeam] Ranged evasion active — freyr att included for cleanse (attack evaded, cleanse still fires)"
                        )
                    passable = sorted(
                        [
                            i
                            for i, c in enumerate(hand_of_cards)
                            if _is_melee_card(c) or c.card_type == CardTypes.ULTIMATE
                        ]
                        + freyr_att_through_evasion,
                        key=lambda idx: card_ranks[idx],
                    )
                    print(f"[HumanTeam] Ranged evasion active — melee/ult/freyr-att ({len(passable)} options)")
                if passable:
                    return self._play(passable[-1], hand_of_cards, card_ranks)

                # Nothing passable at all — toss any freyr card to cycle the hand
                if freyr_ids:
                    print("[HumanTeam] Evasion: no passable cards — tossing freyr card to cycle hand")
                    return self._play(freyr_ids[-1], hand_of_cards, card_ranks)

        # ── Common fallback: best available attack card ───────────────────
        attack_idx = _best_attack_idx()
        if attack_idx is not None:
            return self._play(attack_idx, hand_of_cards, card_ranks)

        print("[HumanTeam] No suitable card found — delegating to SmarterBattleStrategy")
        idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        return self._play(idx, hand_of_cards, card_ranks)
