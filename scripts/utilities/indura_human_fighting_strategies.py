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
    Phase 1 — Burst to try to one-shot.
              Turn 0: only freyr cards and ban_aoe are restricted — everything
              else (ults, attacks) is fair game for maximum burst.
              Turn 1+ (if boss survived): check for the counter stance and play
              a silver+ freyr_att to safely absorb it.  If no counter is up,
              freyr_att stays benched and normal attacks proceed.

    Phase 2 — Boss is tanky and loses damage reduction each turn.
              Turn 0: check if Sho's potential freeze can be handled — prefer
              freyr_att (cleanses + starts Freyr passive).  If no freyr on the
              team, check whether an ally King or Freyr card is already in the
              played slots and log it; fall through to ban/attack filler.
              Turn 1+: ban falls off; switch to harder attack cards.
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
              Turn 0: hold ults, observe the teammate, play attack cards.
              Turn 1+: full-send with roxy_ult / sho_ult, then any other ult.
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

        # ── PHASE 1 ───────────────────────────────────────────────────────
        if phase == 1:
            if phase_turn == 0:
                # Hard restrictions only: freyr triggers the counter early;
                # ban_aoe wastes burst.  Everything else is fair game.
                for idx in freyr_ids + ban_aoe_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            else:
                # Turn 1+: counter stance check.
                # A silver+ freyr_att safely absorbs the boss's retaliation.
                played_freyr_att = [c for c in picked_cards if find(vio.indura_freyr_att, c.card_image)]
                if freyr_att_ids and find(vio.snake_f3p2_counter, screenshot) and not played_freyr_att:
                    preferred = [idx for idx in freyr_att_ids if card_ranks[idx] >= CardRanks.SILVER.value]
                    chosen = (preferred or freyr_att_ids)[-1]
                    print(f"[HumanTeam] Counter present — absorbing with freyr att")
                    return self._play(chosen, hand_of_cards, card_ranks)

                # No counter: bench freyr_att, leave freyr_ult/aoe available
                for idx in freyr_att_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # P1 common: ults first, then fall through to common attack logic
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

            if phase_turn == 0:
                # Check if an ally King or Freyr is already in the played slots —
                # either of those can cleanse Sho's potential freeze from P1.
                six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
                ally_has_cleanse = find(vio.mini_king, six_slots) or any(
                    find(img, six_slots) for img in (vio.indura_freyr_att, vio.freyr_ult)
                )
                if ally_has_cleanse:
                    print("[HumanTeam] P2 turn 0 — ally cleanse (King or Freyr) detected in played slots")

                # Lead with freyr_att: cleanses Sho freeze + starts passive stack
                if freyr_att_ids:
                    print("[HumanTeam] P2 turn 0 — playing freyr att (passive + Sho cleanse)")
                    return self._play(freyr_att_ids[-1], hand_of_cards, card_ranks)
                if freyr_ids:
                    print("[HumanTeam] P2 turn 0 — playing freyr card (passive + cleanse)")
                    return self._play(freyr_ids[-1], hand_of_cards, card_ranks)

                # No freyr on team
                if ally_has_cleanse:
                    print("[HumanTeam] P2 turn 0 — no freyr; ally handling Sho cleanse")
                else:
                    print("[HumanTeam] P2 turn 0 — no freyr on team; no ally cleanse detected")

                if ban_ids:
                    return self._play(ban_ids[-1], hand_of_cards, card_ranks)

            else:
                # Turn 1+: ban falls off
                for idx in ban_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Attack fallback for both P2 turns
            attack_ids = sorted(
                [i for i, c in enumerate(hand_of_cards) if c.card_type == CardTypes.ATTACK],
                key=lambda idx: card_ranks[idx],
            )
            if attack_ids:
                return self._play(attack_ids[-1], hand_of_cards, card_ranks)

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
            # Boss applies melee or ranged evasion each turn after turn 0.
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
            if phase_turn == 0:
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
        attack_ids = sorted(
            [i for i, c in enumerate(hand_of_cards) if c.card_type == CardTypes.ATTACK],
            key=lambda idx: card_ranks[idx],
        )
        if attack_ids:
            return self._play(attack_ids[-1], hand_of_cards, card_ranks)

        print("[HumanTeam] No suitable card found — delegating to SmarterBattleStrategy")
        idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        return self._play(idx, hand_of_cards, card_ranks)
