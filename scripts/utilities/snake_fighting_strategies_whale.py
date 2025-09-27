import numpy as np
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, determine_card_merge, find
import utilities.vision_images as vio


class SnakeBattleStrategy(IBattleStrategy):
    """Dedicated Snake strategy handling Floor 1 and Floor 2 with clean turn logic."""

    def __init__(self):
        # For tracking turns in F1P3
        self.f1p3_turn_counter = None
        self.f1p3_card_counter = None
        # For tracking turns in F2P3
        self.f2p3_turn_counter = None
        self.f2p3_card_counter = None

    # ======================================================================
    # Main entry point
    # ======================================================================
    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int, card_turn=0, **kwargs
    ) -> int:
        # Floor 1 logic
        if floor == 1:
            return self.floor_1_strategy(hand_of_cards, picked_cards, phase, card_turn)

        # Floor 2 logic
        if floor == 2:
            return self.floor_2_strategy(hand_of_cards, picked_cards, phase, card_turn)

        # Floor 3 logic
        if floor == 3:
            return self.floor_3_strategy(hand_of_cards, picked_cards, phase, card_turn)

        # Fallback for other floors
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================================================================
    # Shared Helpers
    # ======================================================================
    def _card_matches_templates(self, card, keys) -> bool:
        """Check if a card matches any of the given template keys."""
        for k in keys:
            tmpl = getattr(vio, k, None)
            if tmpl and find(tmpl, card.card_image):
                return True
            if isinstance(card.card_image, str) and k in card.card_image.lower():
                return True
        return False

    def find_cards(self, hand_of_cards, keys, include_silver_only=False, ranks=None):
        """Find all card indices matching given keys, optionally filtered by ranks."""
        matches = []
        for idx, card in enumerate(hand_of_cards):
            if card.card_type == CardTypes.DISABLED:
                continue
            if include_silver_only:
                if not hasattr(card, "card_rank") or card.card_rank != CardRanks.SILVER:
                    continue
            if ranks and card.card_rank not in ranks:
                continue
            if self._card_matches_templates(card, keys):
                matches.append(idx)
        return matches

    def played_any(self, picked_cards, keys):
        """Check if any of these keys have already been played this turn."""
        return any(self._card_matches_templates(c, keys) for c in picked_cards)

    def try_non_nasi_merge(self, hand_of_cards):
        """Detect merge opportunity between two adjacent non-Nasi bronze cards."""
        for i in range(len(hand_of_cards) - 2, 0, -1):
            left = hand_of_cards[i - 1]
            right = hand_of_cards[i + 1]
            if determine_card_merge(left, right) and not self._card_matches_templates(left, ["nasi_heal", "nasi_stun", "nasi_ult"]):
                return i
        return None

    def try_nasi_merge(self, hand_of_cards):
        """Detect merge opportunity specifically for Nasi cards."""
        for i in range(len(hand_of_cards) - 2, 0, -1):
            left = hand_of_cards[i - 1]
            right = hand_of_cards[i + 1]
            if determine_card_merge(left, right) and self._card_matches_templates(left, ["nasi_heal", "nasi_stun", "nasi_ult"]):
                return i
        return None

    def try_specific_merge(self, hand_of_cards, keys, rank=None):
        """Detect merge opportunity for specific card type and optional rank."""
        for i in range(len(hand_of_cards) - 2, 0, -1):
            left = hand_of_cards[i - 1]
            right = hand_of_cards[i + 1]
            if determine_card_merge(left, right) and self._card_matches_templates(left, keys):
                if rank is None or (left.card_rank == rank and right.card_rank == rank):
                    return i
        return None

    def play_dps_priority(self, hand_of_cards, include_nasi_ult=True, include_ults=True, order='urek_cha_jin'):
        """Play from DPS priority: ults first, then normal damage, customizable."""
        if include_ults:
            ult_groups = []
            if include_nasi_ult:
                ult_groups.append("nasi_ult")
            if 'urek' in order:
                ult_groups.append("urek_ult")
            if 'cha' in order:
                ult_groups.append("cha_ult")
            if 'jin' in order:
                ult_groups.append("jin_ult")
            for group in ult_groups:
                ids = self.find_cards(hand_of_cards, [group])
                if ids:
                    return ids[-1]

        damage_groups = []
        if 'urek' in order:
            damage_groups.extend(["urek_atk", "urek_deb"])
        if 'cha' in order:
            damage_groups.extend(["cha_atk", "cha_bufrem"])
        if 'jin' in order:
            damage_groups.extend(["jin_st", "jin_aoe"])
        for group in damage_groups:
            ids = self.find_cards(hand_of_cards, [group])
            if ids:
                return ids[-1]
        return None

    def handle_nasi_card(self, hand_of_cards):
        """Handle Nasien logic for last slot: merge if possible, else play one."""
        # Check for Nasi-specific merge
        merge_idx = self.try_nasi_merge(hand_of_cards)
        if merge_idx is not None:
            return merge_idx

        # Otherwise play any Nasien card
        nasi_groups = ["nasi_heal", "nasi_stun", "nasi_ult"]
        for group in nasi_groups:
            ids = self.find_cards(hand_of_cards, [group])
            if ids:
                return ids[-1]
        return None

    # ======================================================================
    # FLOOR 1 STRATEGY
    # ======================================================================
    def floor_1_strategy(self, hand_of_cards, picked_cards, phase, card_turn) -> int:

        # -----------------------
        # Phase 1: Setup
        # -----------------------
        if phase == 1:
            for group in (["nasi_heal"], ["jin_aoe"], ["jin_st"], ["cha_bufrem"]):
                ids = self.find_cards(hand_of_cards, group)
                if ids:
                    return ids[-1]

        # -----------------------
        # Phase 2: DPS while keeping 1 silver nasi_stun
        # -----------------------
        elif phase == 2:
            nasi_stun_silver = self.find_cards(hand_of_cards, ["nasi_stun"], include_silver_only=True)

            priority_groups = [
                ["nasi_ult"], ["urek_ult"], ["cha_ult"], ["jin_ult"],
                ["urek_atk"],
                ["urek_deb"],
                ["cha_atk"],
                ["cha_bufrem"],
                ["jin_st"],
                ["jin_aoe"],
                ["nasi_heal"],
                ["nasi_stun"],
            ]

            for group in priority_groups:
                ids = self.find_cards(hand_of_cards, group)
                if not ids:
                    continue
                if group == ["nasi_stun"] and len(nasi_stun_silver) <= 1:
                    continue  # never consume the last silver stun
                return ids[-1]

        # -----------------------
        # Phase 3: Merge + bar break + nuking
        # -----------------------
        elif phase == 3:
            # Initialize counters on first entry into Phase 3
            if self.f1p3_turn_counter is None:
                self.f1p3_turn_counter = 1
                self.f1p3_card_counter = 0

            # Increment card counter each play
            self.f1p3_card_counter += 1
            if self.f1p3_card_counter >= 4:
                self.f1p3_card_counter = 0
                self.f1p3_turn_counter += 1

            merge_i = self.try_non_nasi_merge(hand_of_cards)
            if merge_i is not None:
                return merge_i

            played_heals = sum(1 for c in picked_cards if self._card_matches_templates(c, ["nasi_heal"]))

            if self.f1p3_turn_counter > 1 and played_heals < 2:
                heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
                if heal_ids:
                    return heal_ids[-1]

            if self.f1p3_turn_counter == 1:
                # Assume bar up: break mode
                # Play silver nasi_stun as first card if not played
                if len(picked_cards) == 0 and not self.played_any(picked_cards, ["nasi_stun"]):
                    silver_nasi = self.find_cards(hand_of_cards, ["nasi_stun"], include_silver_only=True)
                    if silver_nasi:
                        return silver_nasi[-1]

                # Then highest rarity breaker (excluding heals)
                breaker_ids = [
                    idx
                    for idx, card in enumerate(hand_of_cards)
                    if card.card_type in [CardTypes.ATTACK, CardTypes.ATTACK_DEBUFF, CardTypes.DEBUFF, CardTypes.ULTIMATE]
                    and not self._card_matches_templates(card, ["nasi_heal"])
                ]
                breaker_ids = sorted(breaker_ids, key=lambda idx: -hand_of_cards[idx].card_rank.value)
                if breaker_ids:
                    return breaker_ids[0]
            else:
                # Assume bar down: nuke mode
                nuke_idx = self.play_dps_priority(hand_of_cards, order='urek_cha_jin')
                if nuke_idx is not None:
                    return nuke_idx

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================================================================
    # FLOOR 2 STRATEGY
    # ======================================================================
    def floor_2_strategy(self, hand_of_cards, picked_cards, phase, card_turn) -> int:
        """Handles Floor 2 all phases including controlled DPS + Nasien logic and Phase 3 turn rules."""

        if phase in [1, 2]:
            # Disable all ult cards for F2P1 and F2P2
            for card in hand_of_cards:
                if self._card_matches_templates(card, ["nasi_ult", "urek_ult", "cha_ult", "jin_ult"]):
                    card.card_type = CardTypes.DISABLED

        if phase == 1:
            for group in (["nasi_heal"], ["jin_aoe"], ["jin_st"], ["cha_bufrem"]):
                ids = self.find_cards(hand_of_cards, group)
                if ids:
                    return ids[-1]

        elif phase == 2:
            played_stun = self.played_any(picked_cards, ["nasi_stun"])
            if played_stun:
                for card in hand_of_cards:
                    if self._card_matches_templates(card, ["nasi_stun"]):
                        card.card_type = CardTypes.DISABLED

            if len(picked_cards) == 0 and not played_stun:
                silver_stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"], include_silver_only=True)
                if silver_stun_ids:
                    return silver_stun_ids[-1]

            # DPS preference for F2P2
            urek_ids = self.find_cards(hand_of_cards, ["urek_atk", "urek_deb"])
            if urek_ids:
                return urek_ids[-1]

            cha_ids = self.find_cards(hand_of_cards, ["cha_atk", "cha_bufrem"])
            if cha_ids:
                return cha_ids[-1]

            jin_st_ids = self.find_cards(hand_of_cards, ["jin_st"])
            if jin_st_ids:
                return jin_st_ids[-1]

            jin_aoe_ids = self.find_cards(hand_of_cards, ["jin_aoe"])
            if jin_aoe_ids:
                return jin_aoe_ids[-1]

            stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"])
            if stun_ids:
                return stun_ids[-1]

            heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
            if heal_ids:
                return heal_ids[-1]

        elif phase == 3:
            screenshot, _ = capture_window()

            turn_number = 0
            if find(vio.f2p3_t1, screenshot):
                turn_number = 1

            played_nasi_ult = self.played_any(picked_cards, ["nasi_ult"])
            played_urek_ult = self.played_any(picked_cards, ["urek_ult"])
            played_high_ult = played_nasi_ult or played_urek_ult
            played_heal = sum(1 for c in picked_cards if self._card_matches_templates(c, ["nasi_heal"]))

            merge_i = self.try_non_nasi_merge(hand_of_cards)
            if merge_i is not None:
                return merge_i

            if turn_number == 1:
                nasi_ult_ids = self.find_cards(hand_of_cards, ["nasi_ult"])
                if nasi_ult_ids:
                    return nasi_ult_ids[-1]

                urek_ult_ids = self.find_cards(hand_of_cards, ["urek_ult"])
                if urek_ult_ids:
                    return urek_ult_ids[-1]

                dps_idx = self.play_dps_priority(hand_of_cards, include_nasi_ult=False, include_ults=False)
                if dps_idx is not None:
                    return dps_idx

                cha_ult_ids = self.find_cards(hand_of_cards, ["cha_ult"])
                if cha_ult_ids:
                    return cha_ult_ids[-1]

                jin_ult_ids = self.find_cards(hand_of_cards, ["jin_ult"])
                if jin_ult_ids:
                    return jin_ult_ids[-1]

                stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"])
                if stun_ids:
                    return stun_ids[-1]

                heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
                if heal_ids:
                    return heal_ids[-1]

            else:
                nasi_ult_ids = self.find_cards(hand_of_cards, ["nasi_ult"])
                if nasi_ult_ids:
                    return nasi_ult_ids[-1]

                heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
                if heal_ids:
                    return heal_ids[-1]

                urek_ult_ids = self.find_cards(hand_of_cards, ["urek_ult"])
                if urek_ult_ids:
                    return urek_ult_ids[-1]

                dps_idx = self.play_dps_priority(hand_of_cards, include_nasi_ult=False, include_ults=False)
                if dps_idx is not None:
                    return dps_idx

                cha_ult_ids = self.find_cards(hand_of_cards, ["cha_ult"])
                if cha_ult_ids:
                    return cha_ult_ids[-1]

                jin_ult_ids = self.find_cards(hand_of_cards, ["jin_ult"])
                if jin_ult_ids:
                    return jin_ult_ids[-1]

                stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"])
                if stun_ids:
                    return stun_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # ======================================================================
    # FLOOR 3 STRATEGY
    # ======================================================================
    def floor_3_strategy(self, hand_of_cards, picked_cards, phase, card_turn) -> int:
        """Handles Floor 3 all phases."""

        # -----------------------
        # Phase 1: Exact sequence
        # -----------------------
        if phase == 1:
            sequence = ["nasi_heal", "jin_aoe", "jin_st", "cha_bufrem"]
            group = [sequence[card_turn]]
            ids = self.find_cards(hand_of_cards, group)
            if ids:
                return ids[-1]

        # -----------------------
        # Phase 2: Nuke DPS, avoid Nasi unless nothing else
        # -----------------------
        elif phase == 2:
            dps_idx = self.play_dps_priority(hand_of_cards, include_nasi_ult=False, include_ults=True, order='urek_cha_jin')
            if dps_idx is not None:
                return dps_idx
            # If nothing else, fallback to Nasi
            nasi_idx = self.handle_nasi_card(hand_of_cards)
            if nasi_idx is not None:
                return nasi_idx

        # -----------------------
        # Phase 3: Complex logic with stance check
        # -----------------------
        elif phase == 3:
            screenshot, _ = capture_window()
            has_stance = find(vio.snake_stance, screenshot, threshold=0.8)
            has_suppress = find(vio.snek_suppress, screenshot, threshold=0.8)

            use_stun = has_stance and has_suppress

            # Disable nasi_stun cards unless use_stun
            if not use_stun:
                for card in hand_of_cards:
                    if self._card_matches_templates(card, ["nasi_stun"]):
                        card.card_type = CardTypes.DISABLED
            else:
                # Ensure they are not disabled when needed
                for card in hand_of_cards:
                    if self._card_matches_templates(card, ["nasi_stun"]):
                        if card.card_type == CardTypes.DISABLED:
                            card.card_type = CardTypes.DEBUFF  # Assuming stun is debuff

            played_stun = sum(1 for c in picked_cards if self._card_matches_templates(c, ["nasi_stun"]))
            played_nasi_ult = self.played_any(picked_cards, ["nasi_ult"])
            played_urek_ult = self.played_any(picked_cards, ["urek_ult"])
            played_high_ult = played_nasi_ult or played_urek_ult
            played_group_ult = self.played_any(picked_cards, ["urek_ult", "cha_ult", "jin_ult"])
            played_nasi_heal = sum(1 for c in picked_cards if self._card_matches_templates(c, ["nasi_heal"]))
            played_nasi_recovery = played_nasi_ult + played_nasi_heal

            if use_stun:
                # SILVER OR GOLD nasi_stun (1 only)
                if played_stun == 0:
                    stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"], ranks=[CardRanks.SILVER, CardRanks.GOLD])
                    if stun_ids:
                        return stun_ids[-1]

                    # If no ready stun, merge bronze nasi_stun if possible
                    stun_merge_i = self.try_specific_merge(hand_of_cards, ["nasi_stun"], rank=CardRanks.BRONZE)
                    if stun_merge_i is not None:
                        return stun_merge_i

                # nasi_ult or nasi_heal (max 1, prefer ult)
                if played_nasi_recovery < 1:
                    ult_ids = self.find_cards(hand_of_cards, ["nasi_ult"])
                    if ult_ids:
                        return ult_ids[-1]
                    heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
                    if heal_ids:
                        return heal_ids[-1]

            # Try non-Nasi merge
            merge_i = self.try_non_nasi_merge(hand_of_cards)
            if merge_i is not None:
                return merge_i

            # nasi_ult
            nasi_ult_ids = self.find_cards(hand_of_cards, ["nasi_ult"])
            if nasi_ult_ids:
                return nasi_ult_ids[-1]

            # urek_ult (if not played_group_ult)
            if not played_group_ult:
                urek_ult_ids = self.find_cards(hand_of_cards, ["urek_ult"])
                if urek_ult_ids:
                    return urek_ult_ids[-1]

            # nasi_heal
            max_heal = 1 if played_high_ult else 2
            if played_nasi_heal < max_heal:
                heal_ids = self.find_cards(hand_of_cards, ["nasi_heal"])
                if heal_ids:
                    return heal_ids[-1]

            # cha_ult or jin_ult (only if not played_group_ult)
            if not played_group_ult:
                cha_ult_ids = self.find_cards(hand_of_cards, ["cha_ult"])
                if cha_ult_ids:
                    return cha_ult_ids[-1]

                jin_ult_ids = self.find_cards(hand_of_cards, ["jin_ult"])
                if jin_ult_ids:
                    return jin_ult_ids[-1]

            # dps cards (no ults)
            dps_idx = self.play_dps_priority(hand_of_cards, include_nasi_ult=False, include_ults=False, order='urek_cha_jin')
            if dps_idx is not None:
                return dps_idx

            # nasi_stun only if use_stun and not played
            if use_stun and played_stun == 0:
                stun_ids = self.find_cards(hand_of_cards, ["nasi_stun"])
                if stun_ids:
                    return stun_ids[-1]

            # If nasi_stun left, let them merge
            stun_merge_i = self.try_nasi_merge(hand_of_cards)
            if stun_merge_i is not None:
                return stun_merge_i

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)