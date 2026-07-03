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
    (vio.indura_jin_st,        "jinwoo st",      "melee"),
    (vio.indura_jin_aoe,       "jinwoo aoe",     "ranged"),
    (vio.indura_jin_ult,       "jinwoo ult",     "ult"),
    (vio.indura_roxy_att,      "roxy att",       "melee"),
    (vio.indura_roxy_aoe,      "roxy aoe",       "ranged"),
    (vio.indura_roxy_ult,      "roxy ult",       "ult"),
    (vio.indura_sho_att,       "sho att",        "melee"),
    (vio.indura_sho_aoe,       "sho aoe",        "ranged"),
    (vio.indura_sho_ult,       "sho ult",        "ult"),
    (vio.indura_freyr_att,     "freyr att",      "ranged"),
    (vio.indura_freyr_aoe,     "freyr aoe",      "ranged"),
    (vio.indura_freyr_ult,     "freyr ult",      "ult"),
    (vio.indura_ban_att,       "ban att",        "ranged"),
    (vio.indura_ban_aoe,       "ban aoe",        "ranged"),
    (vio.indura_ban_ult,       "ban ult",        "ult"),
    (vio.indura_mikasa_att,    "mikasa att",     "melee"),
    (vio.indura_mikasa_debuff, "mikasa debuff",  "melee"),
    (vio.indura_mikasa_ult,    "mikasa ult",     "ult"),
    (vio.indura_enjin_att,     "enjin att",      "melee"),
    (vio.indura_enjin_aoe,     "enjin aoe",      "melee"),
    (vio.indura_enjin_ult,     "enjin ult",      "ult"),
]

_RANK_LABEL = {
    CardRanks.BRONZE.value:   "bronze",
    CardRanks.SILVER.value:   "silver",
    CardRanks.GOLD.value:     "gold",
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
    return any(find(img, card.card_image) for img in (
        vio.indura_freyr_att, vio.indura_freyr_aoe, vio.indura_freyr_ult,
    ))


def _is_ban_card(card: Card) -> bool:
    return any(find(img, card.card_image) for img in (
        vio.indura_ban_att, vio.indura_ban_aoe, vio.indura_ban_ult,
    ))


def _is_enjin_card(card: Card) -> bool:
    return any(find(img, card.card_image) for img in (
        vio.indura_enjin_att, vio.indura_enjin_aoe, vio.indura_enjin_ult,
    ))


def _is_enjin_attack_card(card: Card) -> bool:
    """Enjin's two damage cards (st + aoe), excluding his ultimate."""
    return any(find(img, card.card_image) for img in (
        vio.indura_enjin_att, vio.indura_enjin_aoe,
    ))


def _is_melee_card(card: Card) -> bool:
    return any(
        atype == "melee" and find(img, card.card_image)
        for img, _, atype in _CARD_INFO
    )


def _is_ranged_card(card: Card) -> bool:
    return any(
        atype == "ranged" and find(img, card.card_image)
        for img, _, atype in _CARD_INFO
    )


# ─── Strategy ─────────────────────────────────────────────────────────────────

class InduraHumanBattleStrategy(IBattleStrategy):
    """Battle strategy for the Human-team Indura Death Match.

    Front line : Enjin / Jin / Roxy (+ Sho / Freyr / Ban on legacy rosters)
    Sub unit   : Mikasa (or another flex unit; enters when a front unit falls)

    Enjin note
    ──────────
    Enjin is the current best DPS and replaces Ban on the meta team
    (Enjin / Roxy / Jinwoo + Mikasa-or-flex).  He is squishy but reliably
    hits the damage caps.  His overheat passive gains a stack each time ANY
    ally (himself included) plays a card; when he plays a card while already
    holding 2 stacks, that play takes him to 3 and detonates the overheat.
    We exploit this on the Phase-2 opening turn (see below).  On the later
    turns we still favour his attack cards, but cap him at two cards per turn
    (ENJIN_CARDS_PER_TURN) so Jinwoo/Roxy keep getting the skill uses that
    charge their ult gauges.
    The logic stays roster-flexible: at the start of each match the team
    composition is deduced once from the cards we see — priority Enjin > Ban >
    Freyr — and cached for the whole fight (see `_detect_composition`).  The
    three supported rosters are Enjin/Roxy/Jin, Ban/Roxy/Jin, and the legacy
    Freyr/Roxy/Sho team; only the Enjin branches change behaviour, so the older
    teams play exactly as they did before.

    Phase overview
    ──────────────
    Phase 1 — Burst to try to one-shot, with a fixed damage-optimal opening.
              Opening (turn 0, no boss stance up — i.e. we move first):
                play a fixed sequence that supersedes the default logic.
                  · Default team : roxy_att -> sho_att -> sho_aoe
                    (sho_att before sho_aoe makes the AoE hit harder; the two
                     Sho cards self-freeze him, cleansed next turn by freyr_att)
                  · Jinwoo team  : jin_st -> jin_aoe -> roxy_att
                    (auto-selected when any Jinwoo card is seen on the team)
              Stance up (turn 1+, or turn 0 if we moved second):
                · Freyr comp: play a silver+ freyr_att to nullify the counter
                  (also cleanses Sho's freeze), then press damage in the order
                  sho_att, roxy_att, sho_aoe, roxy_aoe to clear the phase ASAP.
                · Enjin/Ban comp (no freyr_att self-cancel): we can't nullify the
                  counter ourselves, so on the first card of the turn we POLL up
                  to 8s, breaking early the moment the boss stance clears or an
                  ally stance-cancel lands in the played slots (mini_king /
                  mini_freyr_cancel — a Fairy-comp ally usually carries one).
                  Ally cancelled → press damage through it; nothing after 8s —
                  the worst-case "moved second" opening — spread one single-target
                  per unit (enjin_st -> jin_st -> roxy_st) to lifesteal through
                  the counter instead of feeding it AoEs.
                · Freyr comp: if an ally already cancelled, we bench our freyr_att
                  this turn so it carries to the P2-turn-0 freyr priority.
              No stance on a later turn: freyr_att benched, same damage order.
              Ults remain a fallback after the prioritized cards in every case.

    Phase 2 — Boss is tanky and loses damage reduction each turn.  The opening
              turn is normally redundant to attack into, but Enjin changes that.
              Turn 0 (Enjin team): lead with enjin_st to trigger his overheat
              (he carries 2-3 stacks in from Phase 1, so his first attack
              detonates it), then press single-target damage in a hierarchy —
              roxy_att, then any other single-target hit — to punch through the
              otherwise-tanky opening.
              Turn 0 (legacy team / no Enjin cards): check if Sho's potential
              freeze can be handled — prefer freyr_att (cleanses + starts Freyr
              passive).  If no freyr on the team, check whether an ally King or
              Freyr card is already in the played slots and log it; fall through
              to ban/attack filler.
              Turn 1+ (cleanup): the priority is ending the phase fast, so lead
              with Enjin's (squishy, cap-hitting) attack cards — up to two per
              turn — then replicate the fixed opening damage burst (an emergency
              card-seal cleanse still fires; ban/freyr are benched).
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
              Turn 0: the boss debuffs the whole team on entry — lead with
              freyr_att when available to cleanse it (team-wide heal), then
              hold ults, observe the teammate, and play attack cards.  But if an
              ally already dropped a heal in the slots (mini_heal), the team is
              covered, so we skip our own support and press damage instead.
              Turn 1+: full-send with roxy_ult / sho_ult, then any other ult.
              Freyr's att and ult carry a built-in cleanse for both the boss's
              card-seal debuff and Sho's freeze.

    Attack types
    ────────────
    Melee : jinwoo st, roxy att, sho att, mikasa att, mikasa debuff,
            enjin att, enjin aoe
    Ranged: jinwoo aoe, roxy aoe, sho aoe, freyr att, freyr aoe, ban att, ban aoe
    Ult   : all ultimates (always bypass evasion)

    Sho freeze note
    ───────────────
    If Sho uses two cards in one turn he freezes himself until cleansed.
    Freyr (att or ult), ally King, or ally Freyr cards all provide the cleanse.
    The script checks ally played cards in the 6-slot region for King/Freyr and
    logs what it finds.

    Ally support note
    ─────────────────
    Each turn we read the 6 played-card slots (6_cards_region) once and flag what
    an ALLY has committed, using slot-size mini templates (mini_heal, mini_king,
    mini_freyr_cancel) so detection survives the smaller played-card art:
      · ally_played_heal          → an ally healed/cleansed the team
      · ally_played_stance_cancel → an ally King/Freyr broke the boss stance
    We carry no King/heal ourselves, so any mini_king/mini_heal hit is the ally's;
    for the Freyr cancel we subtract our own freyr_att (we_played_freyr_cancel) so
    we don't read our own card back.  These let us avoid doubling up on support
    and instead shift to damage (P3 heal), confirm the P1 stance is handled, or
    save our own Freyr cancel for P2 — mirroring the fairy InduraBattleStrategy.
    """

    # ── Team-composition memory ────────────────────────────────────────────────
    # Detected once at the start of each match and cached for the whole fight.
    # The supported rosters share Roxy but differ on their signature unit, so we
    # deduce which one we're running from the cards we see, with priority
    # Enjin > Ban > Freyr (per the meta: Enjin replaced Ban, Ban replaced the
    # original Freyr/Sho core).  We ACCUMULATE sightings from the first pick
    # onward rather than trusting a single opening hand — one hand may not show
    # every unit's cards — and the label locks in well before Phase 2, which is
    # the first turn any composition-dependent decision is made.
    COMP_ENJIN  = "Enjin/Roxy/Jin"
    COMP_BAN    = "Ban/Roxy/Jin"
    COMP_LEGACY = "Freyr/Roxy/Sho (legacy)"

    _composition: str | None = None
    _seen_enjin: bool = False
    _seen_ban:   bool = False
    _seen_freyr: bool = False

    # Optional user override (set from the --indura-variant CLI choice).  When
    # None we auto-detect from the cards; when set to a COMP_* label we skip
    # detection and run that variant deterministically.
    _forced_composition: str | None = None

    # Maps the CLI variant token to a composition label ("auto" -> no override).
    _VARIANT_TOKENS = {
        "enjin": COMP_ENJIN,
        "ban":   COMP_BAN,
        "freyr": COMP_LEGACY,
    }

    @classmethod
    def set_forced_composition(cls, variant: str | None) -> None:
        """Pin the team composition from the CLI ('auto' / None clears it).

        'enjin' | 'ban' | 'freyr' force the matching roster and bypass the
        card-based auto-detection; 'auto' (or None) restores auto-detection.
        """
        if variant in (None, "auto"):
            cls._forced_composition = None
            print("[HumanTeam] Indura variant: auto-detect")
        elif variant in cls._VARIANT_TOKENS:
            cls._forced_composition = cls._VARIANT_TOKENS[variant]
            print(f"[HumanTeam] Indura variant forced: {cls._forced_composition}")
        else:
            raise ValueError(f"Unknown Indura human variant: {variant!r}")

    # ── Logging helper ────────────────────────────────────────────────────────

    def _play(self, idx: int, hand_of_cards: list[Card], card_ranks: np.ndarray) -> int:
        """Log the identified card and return idx unchanged."""
        label = _card_label(hand_of_cards[idx], int(card_ranks[idx]))
        print(f"[HumanTeam] >> Playing {label}")
        return idx

    def _detect_composition(
        self, phase: int, card_turn: int,
        enjin_seen: bool, ban_seen: bool, freyr_seen: bool,
    ) -> str | None:
        """Update and return the cached team composition for this fight.

        Called every pick.  On the very first pick of a fresh match (phase 1,
        fight turn 0, card turn 0) the accumulated sightings are cleared, so the
        deduction restarts cleanly for the new team.  Thereafter a unit that has
        been seen once stays "seen" for the rest of the fight, and the label is
        re-derived by priority Enjin > Ban > Freyr.
        """
        cls = InduraHumanBattleStrategy

        # User pinned a variant on the CLI — honour it and skip detection.
        if cls._forced_composition is not None:
            if cls._composition != cls._forced_composition:
                cls._composition = cls._forced_composition
                print(f"[HumanTeam] Team composition forced: {cls._forced_composition}")
            return cls._composition

        if phase == 1 and IBattleStrategy.phase_turn == 1 and card_turn == 0:
            cls._seen_enjin = cls._seen_ban = cls._seen_freyr = False
            cls._composition = None
            print("[HumanTeam] New match — deducing team composition from cards...")

        cls._seen_enjin |= enjin_seen
        cls._seen_ban   |= ban_seen
        cls._seen_freyr |= freyr_seen

        composition = (
            cls.COMP_ENJIN  if cls._seen_enjin
            else cls.COMP_BAN    if cls._seen_ban
            else cls.COMP_LEGACY if cls._seen_freyr
            else None
        )
        if composition != cls._composition:
            cls._composition = composition
            if composition is not None:
                print(f"[HumanTeam] Team composition detected: {composition}")
        return cls._composition

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

        # Turn number within the current phase, 0-indexed (first started turn = 0).
        # The fighter increments IBattleStrategy.phase_turn once per started turn
        # (so the first started turn of each phase is 1) and resets it to 0 on every
        # phase change, so the per-phase turn we want is just that counter minus one.
        phase_turn = max(0, IBattleStrategy.phase_turn - 1)

        print(f"[HumanTeam] phase={phase}  phase_turn={phase_turn}  card_turn={card_turn}")

        # ── Reusable card-index lists (sorted ascending by rank, so [-1] = best) ─
        def ids_where(pred):
            return sorted(
                [i for i, c in enumerate(hand_of_cards) if pred(c)],
                key=lambda idx: card_ranks[idx],
            )

        freyr_ids         = ids_where(_is_freyr_card)
        freyr_att_ids     = ids_where(lambda c: find(vio.indura_freyr_att, c.card_image))
        freyr_cleanse_ids = ids_where(  # freyr_att + freyr_ult both cleanse
            lambda c: find(vio.indura_freyr_att, c.card_image)
                   or find(vio.indura_freyr_ult, c.card_image)
        )
        ban_ids     = ids_where(_is_ban_card)
        ban_aoe_ids = ids_where(lambda c: find(vio.indura_ban_aoe, c.card_image))
        ult_ids     = ids_where(lambda c: c.card_type == CardTypes.ULTIMATE)
        enjin_attack_ids = ids_where(_is_enjin_attack_card)  # enjin st + aoe (no ult)

        # How many Enjin cards we've already committed THIS turn.  We cap him at
        # two per turn on the later phases: his damage is great, but spending all
        # three of his cards starves Jinwoo/Roxy of the skill uses that charge
        # their ult gauges, so we leave the third slot for them.
        ENJIN_CARDS_PER_TURN = 2
        enjin_cards_played = sum(1 for c in picked_cards if _is_enjin_card(c))
        enjin_budget_left = enjin_cards_played < ENJIN_CARDS_PER_TURN

        def _best_attack_idx():
            """Best available ATTACK card by rank, with Enjin weighting.
            Enjin is the squishy, cap-hitting DPS, so while we still have budget
            this turn we spend his damage cards first.  Once two Enjin cards are
            down we flip to preferring NON-Enjin attacks, feeding Jinwoo/Roxy the
            skill uses that build their ults.  Returns None if the hand holds no
            attack card.
            """
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

        # ── Team-composition deduction (cached for the whole fight) ─────────
        # Feed this pick's sightings (hand or already played) into the detector
        # and read back the locked-in composition.  enjin_on_team then gates his
        # Phase-2 overheat opening and the enjin-first attack bias on later turns.
        def _present(imgs) -> bool:
            return any(
                _img_in_cards(img, hand_of_cards) or _img_in_cards(img, picked_cards)
                for img in imgs
            )

        composition = self._detect_composition(
            phase, card_turn,
            enjin_seen=_present((vio.indura_enjin_att, vio.indura_enjin_aoe, vio.indura_enjin_ult)),
            ban_seen=_present((vio.indura_ban_att, vio.indura_ban_aoe, vio.indura_ban_ult)),
            freyr_seen=_present((vio.indura_freyr_att, vio.indura_freyr_aoe, vio.indura_freyr_ult)),
        )
        enjin_on_team = composition == InduraHumanBattleStrategy.COMP_ENJIN

        # Fixed damage-optimal opening burst, shared by the Phase-1 opening turn
        # and the Phase-2 cleanup turn (turn 1+).  Jinwoo team leads with his combo.
        opening_seq = (
            [vio.indura_jin_st, vio.indura_jin_aoe, vio.indura_roxy_att]
            if jin_on_team
            else [vio.indura_roxy_att, vio.indura_sho_att, vio.indura_sho_aoe]
        )

        # ── Ally support read (shared by P1/P3) ─────────────────────────────
        # Read the 6 played-card slots once and note what an ALLY has committed
        # this turn — same idea as the fairy InduraBattleStrategy.  A teammate's
        # heal or stance-cancel lets us skip our own support and shift to damage.
        # We carry no King/heal ourselves, so any mini_king / mini_heal hit is an
        # ally's; for the Freyr cancel we subtract our own freyr_att so we don't
        # read our own played card back as the ally's.
        six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
        we_played_freyr_cancel = _img_in_cards(vio.indura_freyr_att, picked_cards)
        ally_played_heal = find(vio.mini_heal, six_slots)
        ally_played_stance_cancel = bool(
            find(vio.mini_king, six_slots)
            or (find(vio.mini_freyr_cancel, six_slots) and not we_played_freyr_cancel)
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
                vio.indura_sho_att, vio.indura_roxy_att,
                vio.indura_sho_aoe, vio.indura_roxy_aoe,
            ]

            # ── Stance with no self-cancel: lean on the ally's stance cancel ──
            # The Enjin/Ban cores lack Freyr's built-in lvl-2 stance cancel, so a
            # stance can stick — either because we moved second, or because turn-0
            # damage was short.  When we hold no freyr_att to nullify it ourselves,
            # we watch (first card of the turn) for the ally to drop their cancel;
            # most short-damage games are alongside a Fairy comp carrying one.
            # Poll up to 8s and break the instant the boss stance clears OR an
            # ally stance-cancel lands in the played slots, so we don't burn the
            # full timer when the ally was quick.
            if stance_up and not freyr_att_ids and card_turn == 0:
                print("[HumanTeam] P1 stance up, no freyr counter — watching up to 8s for an ally stance cancel...")
                deadline = time.time() + 8
                while time.time() < deadline:
                    screenshot, _ = capture_window()
                    six_slots = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
                    stance_up = bool(find(vio.snake_f3p2_counter, screenshot))
                    ally_played_stance_cancel = bool(
                        find(vio.mini_king, six_slots)
                        or (find(vio.mini_freyr_cancel, six_slots) and not we_played_freyr_cancel)
                    )
                    if not stance_up or ally_played_stance_cancel:
                        break
                    time.sleep(1)
                if not stance_up:
                    print("[HumanTeam] Boss stance cleared — proceeding!")
                elif ally_played_stance_cancel:
                    print("[HumanTeam] Ally stance cancel detected in the slots — pressing damage through it")
                else:
                    print("[HumanTeam] No ally cancel after 8s — single-target lifesteal to tank the counter")

            # ── Opening burst: we move first (turn 0, no stance up) ─────────
            # Fixed sequence, supersedes the default ult/attack logic.
            #   Jinwoo team : jin_st  -> jin_aoe -> roxy_att
            #   Default     : roxy_att -> sho_att -> sho_aoe
            # (Default deliberately uses two Sho cards; the resulting self-freeze
            #  is cleansed next turn by the freyr_att stance-nullify.)
            if phase_turn == 0 and not stance_up:
                seq_name = ("Jinwoo: jin_st -> jin_aoe -> roxy_att" if jin_on_team
                            else "roxy_att -> sho_att -> sho_aoe")
                print(f"[HumanTeam] P1 opening ({seq_name})")
                seq_idx = _next_in_sequence(opening_seq)
                if seq_idx is not None:
                    return self._play(seq_idx, hand_of_cards, card_ranks)
                # Requested card not in hand this pick — fall back to defaults.
                for idx in freyr_ids + ban_aoe_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # ── Stance up (turn 1+, or turn 0 if we moved second) ───────────
            elif stance_up:
                # A silver+ freyr_att safely absorbs the counter and cleanses
                # Sho's freeze.  Play it once per turn before pressing damage —
                # BUT if an ally already dropped a stance cancel, we don't need
                # ours: bench it this turn so it carries to the P2-turn-0 freyr
                # priority instead of being wasted here.
                played_freyr_att = _img_in_cards(vio.indura_freyr_att, picked_cards)
                if freyr_att_ids and not played_freyr_att:
                    if ally_played_stance_cancel:
                        print("[HumanTeam] P1 stance up — ally already cancelled; saving our freyr att for P2")
                        for idx in freyr_att_ids:
                            hand_of_cards[idx].card_type = CardTypes.DISABLED
                    else:
                        preferred = [idx for idx in freyr_att_ids if card_ranks[idx] >= CardRanks.SILVER.value]
                        chosen = (preferred or freyr_att_ids)[-1]
                        print("[HumanTeam] P1 stance up — nullifying with freyr att")
                        return self._play(chosen, hand_of_cards, card_ranks)

                # No freyr_att to nullify the counter (Enjin/Ban core) and the
                # stance survived with no ally cancel — e.g. the worst-case "we
                # moved second" opening.  Don't feed the counter with AoEs: spread
                # one single-target per unit (enjin_st -> jin_st -> roxy_st) so
                # every unit lifesteals through the counter while we still chip.
                # If an ally DID cancel, we skip this and press damage below.
                if not freyr_att_ids and not ally_played_stance_cancel:
                    LIFESTEAL_SINGLES = [
                        vio.indura_enjin_att, vio.indura_jin_st, vio.indura_roxy_att,
                    ]
                    ls_idx = _next_in_sequence(LIFESTEAL_SINGLES)
                    if ls_idx is not None:
                        print("[HumanTeam] P1 stance persists — single-target lifesteal (enjin/jin/roxy st)")
                        return self._play(ls_idx, hand_of_cards, card_ranks)

                # Stance handled (or no single-targets left): clear phase 1 ASAP.
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

            if phase_turn == 0:
                # ── Enjin overheat opening ──────────────────────────────────
                # The P2 opening turn is normally too tanky to be worth hitting,
                # but Enjin walks in holding 3 overheat stacks (built from allies'
                # P1 cards).  Throwing his single-target attack first detonates the
                # overheat and punches through the wall, after which we pile on
                # single-target damage — roxy_att, then any other ST hit.  This
                # supersedes the legacy freyr/ban opening whenever Enjin is rostered.
                if enjin_on_team:
                    P2T0_SINGLE_TARGET = [
                        vio.indura_enjin_att,   # 1) detonate the overheat
                        vio.indura_roxy_att,    # 2) roxy single target
                        vio.indura_jin_st,      # 3) other single-target hits
                        vio.indura_sho_att,
                        vio.indura_mikasa_att,
                    ]
                    st_idx = _next_in_sequence(P2T0_SINGLE_TARGET)
                    if st_idx is not None:
                        print("[HumanTeam] P2 turn 0 — Enjin overheat opening "
                              "(enjin_st -> single-target burst)")
                        return self._play(st_idx, hand_of_cards, card_ranks)
                    # No ST card in hand this pick — fall through to legacy filler.

                # An ally King or Freyr stance-cancel already in the played slots
                # can cleanse Sho's potential freeze from P1.  Reuse the shared,
                # reliable mini-template read (mini_king / mini_freyr_cancel)
                # instead of the old hand-size templates that under-matched here.
                ally_has_cleanse = ally_played_stance_cancel
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
                # Turn 1+ (cleanup): ban falls off and freyr is avoided — the
                # priority is clearing the phase ASAP, so replicate the opening
                # damage burst (an emergency card-seal cleanse above still fires
                # if our skills are sealed).
                for idx in ban_ids + freyr_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED
                # Enjin is squishy and hits the caps — spend his attack cards now
                # rather than risk losing him before they go off, but stop at two
                # per turn so Jinwoo/Roxy still build their ults.
                if enjin_attack_ids and enjin_budget_left:
                    print("[HumanTeam] P2 cleanup turn — leading with enjin attack")
                    return self._play(enjin_attack_ids[-1], hand_of_cards, card_ranks)
                seq_idx = _next_in_sequence(opening_seq)
                if seq_idx is not None:
                    print("[HumanTeam] P2 cleanup turn — opening-style damage burst")
                    return self._play(seq_idx, hand_of_cards, card_ranks)

            # Attack fallback for both P2 turns (Enjin's attacks come first)
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
                        melee_evasion_up  = find(vio.melee_evasion, screenshot)
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
                # Entering P3, the boss debuffs the whole team.  freyr_att
                # cleanses it for a team-wide heal — lead with it when available.
                # But if an ally already dropped a heal in the slots, the team is
                # covered: don't spend our card on support, shift straight to
                # damage to make up for the slot they sank into it.
                played_freyr_att = _img_in_cards(vio.indura_freyr_att, picked_cards)
                if ally_played_heal:
                    print("[HumanTeam] P3 turn 0 — ally already healed; skipping our support, pressing damage")
                elif freyr_att_ids and not played_freyr_att:
                    print("[HumanTeam] P3 turn 0 — leading with freyr att (entry-debuff cleanse + team heal)")
                    return self._play(freyr_att_ids[-1], hand_of_cards, card_ranks)
                # Observe the teammate; hold ults; play attack cards
                for idx in ult_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            else:
                # Full-send: roxy_ult and sho_ult hit hardest
                priority_ults = sorted(
                    [
                        i for i, c in enumerate(hand_of_cards)
                        if c.card_type == CardTypes.ULTIMATE
                        and (
                            find(vio.indura_roxy_ult, c.card_image)
                            or find(vio.indura_sho_ult, c.card_image)
                        )
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
                        [i for i, c in enumerate(hand_of_cards)
                         if _is_ranged_card(c) or c.card_type == CardTypes.ULTIMATE],
                        key=lambda idx: card_ranks[idx],
                    )
                    print(f"[HumanTeam] Melee evasion active — ranged/ult only ({len(passable)} options)")
                else:
                    # Ranged evasion: melee + ult passable, PLUS freyr_att for its cleanse value
                    freyr_att_through_evasion = [
                        i for i, c in enumerate(hand_of_cards)
                        if find(vio.indura_freyr_att, c.card_image)
                    ]
                    if freyr_att_through_evasion:
                        print("[HumanTeam] Ranged evasion active — freyr att included for cleanse (attack evaded, cleanse still fires)")
                    passable = sorted(
                        [i for i, c in enumerate(hand_of_cards)
                         if _is_melee_card(c) or c.card_type == CardTypes.ULTIMATE]
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

        # ── Common fallback: best available attack card (Enjin's first) ───
        attack_idx = _best_attack_idx()
        if attack_idx is not None:
            return self._play(attack_idx, hand_of_cards, card_ranks)

        print("[HumanTeam] No suitable card found — delegating to SmarterBattleStrategy")
        idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        return self._play(idx, hand_of_cards, card_ranks)
