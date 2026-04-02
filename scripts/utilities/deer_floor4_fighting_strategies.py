import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.deer_utilities import (
    count_cards,
    has_ult,
    is_blue_card,
    is_buff_removal_card,
    is_Freyr_card,
    is_green_card,
    is_Hel_card,
    is_Jorm_card,
    is_red_card,
    is_Skuld_card,
    is_skuld_stance_card,
    is_Thor_card,
    is_Tyr_card,
    reorder_buff_removal_card,
    reorder_jorms_heal,
)
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, find

logger = LoggerWrapper("DeerFloor4FightingStrategies", log_file="deer_floor4_AI.log")


class DeerFloor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for Floor 4"""

    # Keep track of the turn within a phase
    turn = 0

    # To keep track of what phases have been initialized
    _phase_initialized = set()

    # Keep track of the last phase we've seen
    _last_phase_seen = None

    # What color cards we're running on the current phase
    _color_cards_picked = None

    # Track if skuld_stance was used on previous turn in phase 3
    _skuld_stance_used_prev_turn_p3 = False

    # Signal to the fighter that Phase 4 can't follow R > G > B and should forfeit
    _phase4_should_forfeit = False

    def _initialize_static_variables(self):
        DeerFloor4BattleStrategy.turn = 0
        DeerFloor4BattleStrategy._phase_initialized = set()
        DeerFloor4BattleStrategy._color_cards_picked = None
        DeerFloor4BattleStrategy._skuld_stance_used_prev_turn_p3 = False
        DeerFloor4BattleStrategy._phase4_should_forfeit = False

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        # If we're entering phase 1 after being in any other phase, reset
        if phase == 1 and DeerFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        # Update last seen phase
        DeerFloor4BattleStrategy._last_phase_seen = phase

        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards, card_turn=card_turn)

        if card_turn == 3:
            # Increment the next round!
            DeerFloor4BattleStrategy.turn += 1

        return card_index

    def _maybe_reset(self, phase_id: str):
        """Reset the turn counter if we're in a new phase"""
        if phase_id not in DeerFloor4BattleStrategy._phase_initialized:
            print("Resetting turn counter for phase", phase_id)
            DeerFloor4BattleStrategy.turn = 0
            DeerFloor4BattleStrategy._phase_initialized.add(phase_id)

    # ======================== PHASE 1 ========================
    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Phase 1 strategy:
        Turn 1: Skuld atk > Hel 1 > Thor 1 > Thor 2 (thunderstorm). Should kill.
        Turn 2+: Use 4 random cards, but keep at least 1 skuld_stance and 2 freyr cards.
        """

        self._maybe_reset("phase_1")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]

        # Find specific cards
        skuld_atk_ids = sorted(
            np.where([find(vio.skuld_atk, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        hel_cards = sorted(
            np.where([is_Hel_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_1_ids = sorted(
            np.where([find(vio.thor_1, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_2_ids = sorted(
            np.where([find(vio.thor_2, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        if DeerFloor4BattleStrategy.turn == 0:
            if card_turn == 0:
                # Skuld atk
                if len(skuld_atk_ids):
                    print("Playing Skuld ATK!")
                    return skuld_atk_ids[-1]
                print("[WARN] No Skuld atk card found, falling back to any green card.")
                green_ids = np.where([is_green_card(card) and not is_skuld_stance_card(card) for card in hand_of_cards])[0]
                if len(green_ids):
                    return green_ids[-1]

            elif card_turn == 1:
                # Hel 1
                if len(hel_cards):
                    print("Playing Hel card!")
                    return hel_cards[0]
                print("[WARN] No Hel card found.")

            elif card_turn == 2:
                # Thor 1 (not thunderstorm)
                if len(thor_1_ids):
                    print("Playing Thor 1!")
                    return thor_1_ids[0]
                elif len(thor_cards):
                    print("Playing any Thor card instead of Thor 1!")
                    return thor_cards[0]

            elif card_turn == 3:
                # Thor 2 (thunderstorm)
                if len(thor_2_ids):
                    print("Playing Thor 2 (Thunderstorm)!")
                    return thor_2_ids[-1]
                elif len(thor_cards):
                    print("Playing any Thor card instead of Thor 2!")
                    return thor_cards[-1]

            # Fallback for turn 0
            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        # Turn 1+: Use random cards, but keep at least 1 skuld_stance and 2 freyr cards
        print("Turn 2+ in Phase 1: playing random cards while preserving skuld_stance and freyr cards.")

        skuld_stance_ids = sorted(
            np.where([is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        freyr_ids = sorted(
            np.where([is_Freyr_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        # Build set of card indices to protect
        cards_to_keep = set()
        # Keep 1 skuld_stance (highest rarity)
        if len(skuld_stance_ids) >= 1:
            cards_to_keep.add(skuld_stance_ids[-1])
        # Keep 2 freyr cards (highest rarity)
        freyr_to_keep = freyr_ids[-2:] if len(freyr_ids) >= 2 else freyr_ids
        cards_to_keep.update(freyr_to_keep)

        # Available cards to play (not in protected set, not disabled)
        available = sorted(
            [i for i in range(len(hand_of_cards))
             if i not in cards_to_keep and hand_of_cards[i].card_type != CardTypes.DISABLED
             and hand_of_cards[i].card_type != CardTypes.NONE
             and hand_of_cards[i].card_type != CardTypes.GROUND],
            key=lambda idx: card_ranks[idx],
        )

        if len(available):
            return available[-1]

        # If nothing else available, just use any card
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================== PHASE 2 ========================
    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Phase 2 Gimmick: Boss has 3 buffs (-1000% damage per color). 2 attacks of a color
        removes the NEXT color's debuff and turns it into +100% damage.
        Color wheel: red > green > blue (2 reds unlock green, 2 greens unlock blue, 2 blues unlock red).
        Attacking with a locked color = attack disabled + killed.

        Turn 0: freyr1 > freyr2 > (move skuld_atk once OR merge same-rarity skuld_stances) > skuld_stance
        Turn 1: If 3+ green: 3 green + 1 thor. If only 2 green: move Hel, move Thor, 2 green. If <2 green: move/merge.
        Turn 2+: Use green/blue cards freely (no red). Follow buff rules.
        """

        self._maybe_reset("phase_2")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]

        # All unit cards sorted
        freyr_ids = sorted(
            np.where([is_Freyr_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        skuld_atk_ids = sorted(
            np.where([find(vio.skuld_atk, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        skuld_stance_ids = sorted(
            np.where([is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        skuld_ids = sorted(
            np.where([is_Skuld_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        green_card_ids = sorted(
            np.where([is_green_card(card) and not is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        green_card_ids_with_stance = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(
            np.where([is_Hel_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        # ---- TURN 0: 2 Freyr > move/merge skuld > skuld_stance ----
        if DeerFloor4BattleStrategy.turn == 0:
            if card_turn == 0:
                # Play first freyr card
                if len(freyr_ids):
                    print("Playing Freyr card 1!")
                    return freyr_ids[0]
                print("[WARN] No Freyr card for turn 0 slot 0!")

            elif card_turn == 1:
                # Play second freyr card
                if len(freyr_ids):
                    print("Playing Freyr card 2!")
                    return freyr_ids[-1]
                print("[WARN] No second Freyr card!")

            elif card_turn == 2:
                # Check if we have 2+ same-rarity skuld_stance cards → merge them
                if len(skuld_stance_ids) >= 2:
                    # Group by rarity
                    stance_by_rarity = {}
                    for sid in skuld_stance_ids:
                        rank = hand_of_cards[sid].card_rank
                        if rank not in stance_by_rarity:
                            stance_by_rarity[rank] = []
                        stance_by_rarity[rank].append(sid)

                    for rank, ids in stance_by_rarity.items():
                        if len(ids) >= 2:
                            print(f"Merging 2 skuld_stance {rank.name} cards! idx {ids[0]} -> {ids[1]}")
                            return [ids[0], ids[1]]

                # Otherwise, move skuld_atk once
                if len(skuld_atk_ids):
                    print("Moving Skuld ATK card once.")
                    return [skuld_atk_ids[0], skuld_atk_ids[0] + 1]

                # Fallback: move any skuld card
                if len(skuld_ids):
                    non_stance_skuld = [s for s in skuld_ids if s not in skuld_stance_ids]
                    if len(non_stance_skuld):
                        print("Moving a Skuld card once (fallback).")
                        return [non_stance_skuld[0], non_stance_skuld[0] + 1]

                # Last fallback: move any green card that isn't skuld_stance
                if len(green_card_ids):
                    print("Moving a green card once (fallback).")
                    return [green_card_ids[0], green_card_ids[0] + 1]

            elif card_turn == 3:
                # Play skuld_stance
                if len(skuld_stance_ids):
                    print("Playing Skuld Stance!")
                    return skuld_stance_ids[-1]  # Highest rarity (may be merged)
                # Fallback: play any available green card
                if len(green_card_ids_with_stance):
                    print("[WARN] No skuld_stance found, playing any green card.")
                    return green_card_ids_with_stance[-1]

            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        # ---- TURN 1: Green is now unlocked (+100% damage) ----
        if DeerFloor4BattleStrategy.turn == 1:
            # Play as many green cards as possible (slots 0-2), Thor for nuke on slot 3 if available.
            # NOTE: Don't branch on green count — the hand shrinks between card_turn calls,
            # so the count changes. Just always try green first.
            if card_turn <= 2:
                if len(green_card_ids_with_stance):
                    print(f"Turn 1 slot {card_turn}: Playing green card")
                    return green_card_ids_with_stance[-1]
                # No green left for this slot — move a non-green card to preserve hand
                non_green_movable = [i for i in range(len(hand_of_cards))
                                     if hand_of_cards[i].card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)
                                     and not is_green_card(hand_of_cards[i])]
                if len(non_green_movable) >= 2:
                    print(f"No green for slot {card_turn}, moving a non-green card.")
                    return [non_green_movable[0], non_green_movable[0] + 1]
            elif card_turn == 3:
                # Prefer Thor for the big nuke
                if len(thor_cards):
                    print("Turn 1 slot 3: Playing Thor card to nuke!")
                    return thor_cards[-1]
                # Otherwise play another green if available
                if len(green_card_ids_with_stance):
                    print("No Thor card, playing 4th green card.")
                    return green_card_ids_with_stance[-1]
                # Otherwise move/skip
                all_card_ids = list(range(len(hand_of_cards)))
                movable = [i for i in all_card_ids
                           if hand_of_cards[i].card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)]
                if len(movable) >= 2:
                    print("No Thor or green for slot 3, moving a card.")
                    return [movable[0], movable[0] + 1]

            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        # ---- TURN 2+: Green and Blue are unlocked. NO RED. ----
        print(f"Phase 2 Turn {DeerFloor4BattleStrategy.turn}: Green/Blue are safe, avoiding red.")

        # Combine green and blue cards as available
        safe_card_ids = sorted(
            np.where([
                (is_green_card(card) or is_blue_card(card)) and not is_skuld_stance_card(card)
                for card in hand_of_cards
            ])[0],
            key=lambda idx: card_ranks[idx],
        )

        # For proper sequencing: if starting with green, keep green or do 3G+1B or 2G+1B+move
        if card_turn == 0:
            # Prefer green cards (they have +100%)
            if len(green_card_ids):
                print("Starting with green card!")
                return green_card_ids[-1]
            elif len(blue_card_ids):
                print("Starting with blue card!")
                return blue_card_ids[-1]

        # Follow color from previous card
        last_card = picked_cards[card_turn - 1] if card_turn > 0 else Card()

        if is_green_card(last_card):
            # Can continue with green or switch to blue
            if card_turn <= 2 and len(green_card_ids):
                return green_card_ids[-1]
            elif len(blue_card_ids):
                print("Switching from green to blue.")
                return blue_card_ids[-1]
            elif len(green_card_ids):
                return green_card_ids[-1]

        if is_blue_card(last_card):
            # Continue with blue (DON'T go to red!)
            if len(blue_card_ids):
                return blue_card_ids[-1]
            # Can move instead
            if len(safe_card_ids):
                return [safe_card_ids[0], safe_card_ids[0] + 1]

        if len(safe_card_ids):
            return safe_card_ids[-1]

        # Last resort: move a card
        all_ids = list(range(len(hand_of_cards)))
        playable = [i for i in all_ids
                    if hand_of_cards[i].card_type not in (CardTypes.DISABLED, CardTypes.NONE, CardTypes.GROUND)]
        if len(playable) >= 2:
            return [playable[0], playable[0] + 1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================== PHASE 3 ========================
    def _card_damage_score(self, card: Card) -> int:
        """Composite damage score: higher = more damage.
        Damage priority (high to low):
          ults > thor cards > skuld_atk > hel_1 > hel_2 > freyr_2 > freyr_1 > skuld_stance
        Rarity is factored in (gold > silver > bronze).
        """
        base = card.card_rank.value * 100  # 0 (bronze), 100 (silver), 200 (gold)

        if card.card_type == CardTypes.ULTIMATE:
            bonus = 90
        elif find(vio.thor_2, card.card_image) or find(vio.thor_1, card.card_image):
            bonus = 80
        elif find(vio.skuld_atk, card.card_image):
            bonus = 70
        elif find(vio.hel_1, card.card_image):
            bonus = 60
        elif find(vio.hel_2, card.card_image):
            bonus = 50
        elif find(vio.freyr_2, card.card_image):
            bonus = 40
        elif find(vio.freyr_1, card.card_image):
            bonus = 30
        elif is_skuld_stance_card(card):
            bonus = 5
        else:
            bonus = 20

        return base + bonus

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Phase 3 Gimmick: Every ODD turn (user turn 1, 3, 5 = code turn 0, 2, 4) boss uses Fierce Rush
        (instakill). Counter: 3 cards of same color → triggers shield.

        Skuld_stance counts towards ticks but shield doesn't activate until we manually attack.
        If skuld_stance was used on previous turn, enemy attacks generate ticks, so we only
        need 1 green card to enable the shield on the next dangerous turn.

        Dangerous turns: use WEAKEST cards for shield (save strong ones for safe turns).
        Safe turns: use STRONGEST cards for maximum damage.
        KEEP Freyr ult for Phase 4!
        """

        self._maybe_reset("phase_3")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        # --- Card pools sorted by damage score (ascending: [0]=weakest, [-1]=strongest) ---
        # Exclude Freyr ult from red cards to save it for phase 4
        green_card_ids = sorted(
            np.where([is_green_card(card) and not is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
        )
        green_with_stance_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0],
            key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
        )
        red_card_ids = sorted(
            np.where([is_red_card(card) and not find(vio.freyr_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0],
            key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
        )
        skuld_stance_ids = sorted(
            np.where([is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
        )

        # Group by color
        card_groups = {"green": green_with_stance_ids, "red": red_card_ids, "blue": blue_card_ids}

        # Is this a dangerous turn? (code 0, 2, 4 = user's turn 1, 3, 5 = odd)
        is_dangerous_turn = (DeerFloor4BattleStrategy.turn % 2 == 0)

        if is_dangerous_turn:
            print("DANGEROUS TURN — need 3 same-color cards for shield!")

            # Check if skuld_stance was used on previous turn — only need 1 green to trigger shield
            if DeerFloor4BattleStrategy._skuld_stance_used_prev_turn_p3:
                print("Skuld stance was active! Only need 1 green card to trigger shield.")
                if card_turn == 0 and len(green_with_stance_ids):
                    # Use WEAKEST green to trigger shield
                    return green_with_stance_ids[0]
                # After shield triggered, use STRONGEST remaining cards
                if card_turn > 0:
                    all_cards = sorted(
                        list(set(green_with_stance_ids) | set(blue_card_ids) | set(red_card_ids)),
                        key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
                    )
                    if len(all_cards):
                        return all_cards[-1]  # Strongest

            # Normal dangerous turn: need 3 same-color cards for shield
            if card_turn == 0:
                card_colors = ["green", "blue", "red"]
                DeerFloor4BattleStrategy._color_cards_picked = max(
                    card_colors, key=lambda k: len(card_groups[k])
                )
                if len(card_groups[DeerFloor4BattleStrategy._color_cards_picked]) < 3:
                    if len(green_with_stance_ids) >= 3:
                        DeerFloor4BattleStrategy._color_cards_picked = "green"
                    else:
                        print("[WARN] No color has 3+ cards for shield! Picking best available.")
                print(f"Shield color: {DeerFloor4BattleStrategy._color_cards_picked}")

            picked_ids = card_groups.get(DeerFloor4BattleStrategy._color_cards_picked, [])
            if card_turn <= 2 and len(picked_ids):
                # Play strongest available same-color card for shield (no need to save weak ones)
                print(f"Picking {DeerFloor4BattleStrategy._color_cards_picked} card for shield.")
                return picked_ids[-1]  # [-1] = strongest (sorted ascending by damage score)

            # 4th card: use STRONGEST available (shield already secured)
            if card_turn == 3:
                all_remaining = sorted(
                    list(set(green_with_stance_ids) | set(red_card_ids) | set(blue_card_ids)),
                    key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
                )
                if len(all_remaining):
                    for idx in reversed(all_remaining):
                        if not find(vio.freyr_ult, hand_of_cards[idx].card_image):
                            return idx
                    return all_remaining[-1]

                # Reset skuld_stance tracking at end of dangerous turn
                DeerFloor4BattleStrategy._skuld_stance_used_prev_turn_p3 = False

        else:
            # Safe turn (code 1, 3, 5 = user's turn 2, 4, 6)
            print("Safe turn — maximize damage!")

            if card_turn == 0:
                card_colors = ["green", "red", "blue"]
                DeerFloor4BattleStrategy._color_cards_picked = max(
                    card_colors, key=lambda k: len(card_groups[k])
                )
                print(f"Playing {DeerFloor4BattleStrategy._color_cards_picked} cards this turn.")

            picked_ids = card_groups.get(DeerFloor4BattleStrategy._color_cards_picked, [])

            if card_turn <= 2 and len(picked_ids):
                # Use STRONGEST cards for max damage
                return picked_ids[-1]  # [-1] = strongest (sorted ascending by damage score)

            if card_turn == 3:
                # Use skuld_stance to stack ticks for next dangerous turn
                if len(skuld_stance_ids):
                    print("Playing Skuld Stance on safe turn to stack ticks for next dangerous turn!")
                    DeerFloor4BattleStrategy._skuld_stance_used_prev_turn_p3 = True
                    return skuld_stance_ids[-1]

                # Otherwise use strongest remaining card (avoid freyr ult)
                all_remaining = sorted(
                    list(set(green_with_stance_ids) | set(red_card_ids) | set(blue_card_ids)),
                    key=lambda idx: self._card_damage_score(hand_of_cards[idx]),
                )
                for idx in reversed(all_remaining):
                    if not find(vio.freyr_ult, hand_of_cards[idx].card_image):
                        return idx
                if len(all_remaining):
                    return all_remaining[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================== PHASE 4 ========================
    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Phase 4 Gimmick: MUST follow exact color pattern Red > Green > Blue every turn,
        for at minimum 3 turns. Boss has immortality stacks for first 3 turns.
        Turn 0-1: Immortal, no damage. Save ults (especially Freyr/Thor).
        Turn 2: Starts taking damage, min 100k HP.
        Turn 3+: Can kill. Use Freyr ult (2x damage).

        CRITICAL: NEVER USE SKULD STANCE ON TURNS 0 AND 1. Only merge/move them.
        Turn 2+: Skuld stance OK to use.
        """

        self._maybe_reset("phase_4")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        # Get all card IDs by color
        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = sorted(
            np.where([is_green_card(card) and not is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        green_with_stance_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        skuld_stance_ids = sorted(
            np.where([is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        # Separate ult cards
        freyr_ult_ids = sorted(
            np.where([find(vio.freyr_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_ult_ids = sorted(
            np.where([find(vio.thor_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        freyr_non_ult = sorted(
            np.where([is_Freyr_card(card) and not find(vio.freyr_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        thor_non_ult = sorted(
            np.where([is_Thor_card(card) and not find(vio.thor_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        # Green ults are OK to use since we have 2 green units (Hel + Skuld)
        hel_cards = sorted(
            np.where([is_Hel_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        skuld_cards = sorted(
            np.where([is_Skuld_card(card) and not is_skuld_stance_card(card) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        # === FAIL DETECTION: On turns 0-2, we MUST have R + G (non-stance) + B for the cycle ===
        if DeerFloor4BattleStrategy.turn <= 2 and card_turn == 0:
            if not (len(red_card_ids) >= 1 and len(green_card_ids) >= 1 and len(blue_card_ids) >= 1):
                logger.warning(
                    f"Phase 4 Turn {DeerFloor4BattleStrategy.turn}: Cannot follow R > G > B cycle! "
                    f"Red: {len(red_card_ids)}, Green (non-stance): {len(green_card_ids)}, Blue: {len(blue_card_ids)}"
                )
                print(
                    f"[FAIL] Phase 4 Turn {DeerFloor4BattleStrategy.turn}: Cannot follow R > G > B! "
                    f"(R={len(red_card_ids)}, G={len(green_card_ids)}, B={len(blue_card_ids)}) Signaling forfeit."
                )
                DeerFloor4BattleStrategy._phase4_should_forfeit = True

        # === TURN 0 and 1: Boss is IMMORTAL. Follow R > G > B. Save ults. NO SKULD STANCE. ===
        if DeerFloor4BattleStrategy.turn <= 1:
            print(f"Phase 4 Turn {DeerFloor4BattleStrategy.turn}: Boss is immortal. R > G > B. NO SKULD STANCE!")

            if card_turn == 0:
                # RED card — prefer non-ult freyr, only use freyr_ult as last resort
                if len(freyr_non_ult):
                    print("Playing Freyr (non-ult) as red card.")
                    return freyr_non_ult[-1]
                elif len(red_card_ids):
                    # Has red cards but they're all ults — check if that's our only option
                    non_ult_red = [i for i in red_card_ids if i not in freyr_ult_ids]
                    if len(non_ult_red):
                        return non_ult_red[-1]
                    # Last resort: use freyr ult
                    print("[WARN] Only Freyr ult available as red card. Using it reluctantly.")
                    return freyr_ult_ids[-1]
                print("[WARN] No red card at all!")

            elif card_turn == 1:
                # GREEN card — green ults OK (2 green units). Exclude skuld_stance!
                if len(green_card_ids):
                    print("Playing green card (non-stance).")
                    return green_card_ids[-1]
                print("[WARN] No green card (non-stance) available!")

            elif card_turn == 2:
                # BLUE card — prefer non-ult thor
                if len(thor_non_ult):
                    print("Playing Thor (non-ult) as blue card.")
                    return thor_non_ult[-1]
                elif len(blue_card_ids):
                    non_ult_blue = [i for i in blue_card_ids if i not in thor_ult_ids]
                    if len(non_ult_blue):
                        return non_ult_blue[-1]
                    print("[WARN] Only Thor ult available as blue card. Using it reluctantly.")
                    return thor_ult_ids[-1]
                print("[WARN] No blue card at all!")

            elif card_turn == 3:
                # 4th action: Move or merge. NEVER use skuld_stance.
                # If we have 2+ same-rarity skuld_stance → merge them
                if len(skuld_stance_ids) >= 2:
                    stance_by_rarity = {}
                    for sid in skuld_stance_ids:
                        rank = hand_of_cards[sid].card_rank
                        if rank not in stance_by_rarity:
                            stance_by_rarity[rank] = []
                        stance_by_rarity[rank].append(sid)

                    for rank, ids in stance_by_rarity.items():
                        if len(ids) >= 2:
                            print(f"Merging 2 skuld_stance {rank.name} cards! idx {ids[0]} -> {ids[1]}")
                            return [ids[0], ids[1]]

                # Move skuld_stance to try to get it to merge with adjacent cards
                if len(skuld_stance_ids):
                    print("Moving skuld_stance to merge it into higher rarity.")
                    return [skuld_stance_ids[0], skuld_stance_ids[0] + 1]

                # Otherwise move a card of someone that doesn't have an ult
                return self._move_card_for_ult(
                    hand_of_cards + picked_cards,
                    hel_cards=hel_cards,
                    skuld_cards=skuld_cards,
                    freyr_cards=freyr_non_ult if len(freyr_non_ult) else red_card_ids,
                    thor_cards=thor_non_ult if len(thor_non_ult) else blue_card_ids,
                )

            # Fallback
            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        # === TURN 2: Starts taking damage. R > G > B. Freyr ult if available for red. ===
        if DeerFloor4BattleStrategy.turn == 2:
            print("Phase 4 Turn 2: Boss starts taking damage! R > G > B. Use Freyr ult if available!")

            if card_turn == 0:
                # RED — Freyr ult preferred (2x damage!)
                if len(freyr_ult_ids):
                    print("Playing FREYR ULT for 2x damage!")
                    return freyr_ult_ids[-1]
                elif len(red_card_ids):
                    print("Playing red card.")
                    return red_card_ids[-1]

            elif card_turn == 1:
                # GREEN card or ult
                if len(green_card_ids):
                    print("Playing green card.")
                    return green_card_ids[-1]

            elif card_turn == 2:
                # BLUE card
                if len(blue_card_ids):
                    print("Playing blue card.")
                    return blue_card_ids[-1]

            elif card_turn == 3:
                # NOW skuld_stance is OK to use!
                if len(skuld_stance_ids):
                    print("Playing Skuld Stance! (now allowed)")
                    return skuld_stance_ids[-1]
                # Otherwise move for ult
                return self._move_card_for_ult(
                    hand_of_cards + picked_cards,
                    hel_cards=hel_cards,
                    skuld_cards=skuld_cards,
                    freyr_cards=freyr_non_ult if len(freyr_non_ult) else red_card_ids,
                    thor_cards=thor_non_ult if len(thor_non_ult) else blue_card_ids,
                )

            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        # === TURN 3+: Still R > G > B. Boss should die. Skuld stance OK. ===
        print(f"Phase 4 Turn {DeerFloor4BattleStrategy.turn}: R > G > B. Boss should be killable!")

        if card_turn == 0:
            # RED card (use best available)
            if len(freyr_ult_ids):
                print("Playing FREYR ULT!")
                return freyr_ult_ids[-1]
            elif len(red_card_ids):
                return red_card_ids[-1]
            print("[WARN] No red card!")

        elif card_turn == 1:
            # GREEN card — skuld_stance does NOT count for the cycle, use real green only
            if len(green_card_ids):
                return green_card_ids[-1]
            print("[WARN] No green card (non-stance)!")

        elif card_turn == 2:
            # BLUE card
            if len(blue_card_ids):
                return blue_card_ids[-1]
            print("[WARN] No blue card!")

        elif card_turn == 3:
            # Skuld stance OK as 4th card (doesn't need to follow cycle), or move
            if len(skuld_stance_ids):
                print("Playing Skuld Stance!")
                return skuld_stance_ids[-1]
            return self._move_card_for_ult(
                hand_of_cards + picked_cards,
                hel_cards=hel_cards,
                skuld_cards=skuld_cards,
                freyr_cards=freyr_non_ult if len(freyr_non_ult) else red_card_ids,
                thor_cards=thor_non_ult if len(thor_non_ult) else blue_card_ids,
            )

        # Absolute fallback
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _move_card_for_ult(
        self,
        list_of_cards: list[Card],
        hel_cards: list = None,
        skuld_cards: list = None,
        freyr_cards: list = None,
        thor_cards: list = None,
        # Legacy params for compatibility
        tyr_hel_cards: list = None,
        jorm_cards: list = None,
    ):
        """Move a card of someone that doesn't have an ult"""
        unit_to_cards = {}
        if hel_cards is not None:
            unit_to_cards["hel"] = hel_cards
        if skuld_cards is not None:
            unit_to_cards["skuld"] = skuld_cards
        if freyr_cards is not None:
            unit_to_cards["freyr"] = freyr_cards
        if thor_cards is not None:
            unit_to_cards["thor"] = thor_cards
        # Legacy support
        if tyr_hel_cards is not None:
            unit_to_cards.setdefault("hel", tyr_hel_cards)
            unit_to_cards.setdefault("tyr", tyr_hel_cards)
        if jorm_cards is not None:
            unit_to_cards.setdefault("jorm", jorm_cards)

        for unit, cards in unit_to_cards.items():
            if not has_ult(unit, list_of_cards):
                if len(cards):
                    print(f"Unit {unit} doesn't have an ult yet!")
                    return [cards[0], cards[0] + 1]

        return [-2, -1]
