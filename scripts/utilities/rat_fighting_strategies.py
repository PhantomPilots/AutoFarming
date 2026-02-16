import time
from enum import Enum, auto

import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import (
    IBattleStrategy,
    SmarterBattleStrategy,
    play_stance_card,
)
from utilities.logging_utils import LoggerWrapper
from utilities.rat_utilities import (
    count_rat_buffs,
    is_bleed_card,
    is_buff_removal,
    is_poison_card,
    is_shock_card,
)
from utilities.utilities import (
    capture_window,
    click_im,
    count_immortality_buffs,
    determine_card_merge,
    find,
    is_amplify_card,
    is_hard_hitting_card,
    is_Thor_card,
)


class DebuffTypes(Enum):
    SHOCK = auto()
    POISON = auto()
    BLEED = auto()
    NONE = auto()


logger = LoggerWrapper("RatFightingStrategies", log_file="rat_AI.log")


class RatFightingStrategy(IBattleStrategy):
    """The logic behind Rat. It's gonna be complex, brace yourself..."""

    turns_in_f2p2 = 0

    def get_next_card_index(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        floor: int,
        phase: int,
        card_turn: int,
        current_stump: int,
        **kwargs,
    ) -> int:
        """Distinguish between floors and phases"""

        # First of all, populate useful information for each card
        for card in hand_of_cards:
            card.debuff_type = get_debuff_type(card)
        for card in picked_cards:
            card.debuff_type = get_debuff_type(card)

        print(f"We're in card turn: {card_turn}")

        if floor == 1 and phase == 1:
            return self.floor1_phase1(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 1 and phase == 2:
            return self.floor1_phase2(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 1 and phase == 3:
            return self.floor1_phase3(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 1:
            return self.floor2_phase1(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 2:
            return self.floor2_phase2(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 3:
            return self.floor2_phase3(hand_of_cards, picked_cards, phase, card_turn, current_stump)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase1(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Phase 1 logic for floor 1 — duplicated from old floor1_phase12"""

        # For bleed IDs, don't play bleeds on phase 2 (phase 1 → always allowed)
        bleed_ids, shock_ids, poison_ids = [], [], []
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type == DebuffTypes.BLEED:
                bleed_ids.append(i)
            elif card.debuff_type == DebuffTypes.SHOCK:
                shock_ids.append(i)
            elif card.debuff_type == DebuffTypes.POISON:
                poison_ids.append(i)

        # Movement logic
        if card_turn == 3:

            def enabled_ids(id_list):
                return [i for i in id_list if hand_of_cards[i].card_type not in [CardTypes.DISABLED, CardTypes.GROUND]]

            if current_stump == 0:
                opts = (enabled_ids(poison_ids), enabled_ids(bleed_ids))
            elif current_stump == 1:
                opts = (enabled_ids(bleed_ids), enabled_ids(shock_ids))
            else:
                opts = (enabled_ids(shock_ids), enabled_ids(poison_ids))

            picked_ids = max(opts, key=len)

            if picked_ids:
                return picked_ids[-1]

        # Diane AOE logic — phase 1: disable ANY debuffed card, plus disabled KDiane AOE
        strong_aoe_ids = [
            i for i, c in enumerate(hand_of_cards)
            if find(vio.kdiane_aoe, c.card_image) or find(vio.kdiane_ult, c.card_image)
        ]

        for i, card in enumerate(hand_of_cards):
            if (card.debuff_type != DebuffTypes.NONE) or (i in strong_aoe_ids and card.card_type == CardTypes.DISABLED):
                if i in strong_aoe_ids:
                    print("Fully disabling KDiane's AOE since it's disabled")
                hand_of_cards[i].card_type = CardTypes.GROUND

        # If everything is ground, return a move
        if all(card.card_type == CardTypes.GROUND for card in hand_of_cards):
            return [-1, -3]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Phase 2 logic for floor 1 — duplicated from old floor1_phase12"""

        screenshot, _ = capture_window()

        # Bleeds disabled in phase 2
        bleed_ids, shock_ids, poison_ids = [], [], []
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type == DebuffTypes.BLEED:
                bleed_ids.append(i)
            elif card.debuff_type == DebuffTypes.SHOCK:
                shock_ids.append(i)
            elif card.debuff_type == DebuffTypes.POISON:
                poison_ids.append(i)
        buff_removal_ids = [i for i, card in enumerate(hand_of_cards) if is_buff_removal(card)]
        valenti_ult_id = [i for i, card in enumerate(hand_of_cards) if find(vio.val_ult, card.card_image)]

        # Phase-2 specific disable: Valenti ult
        if len(valenti_ult_id):
            print("Disabling Valenti's ultimate...")
            hand_of_cards[valenti_ult_id[-1]].card_type = CardTypes.GROUND

        # Disable one bleed + one shock
        if len(bleed_ids):
            hand_of_cards[bleed_ids[0]].card_type = CardTypes.GROUND
            bleed_ids = bleed_ids[1:]
        if len(shock_ids):
            hand_of_cards[shock_ids[0]].card_type = CardTypes.GROUND
            shock_ids = shock_ids[1:]

        # Now disable all debuffs
        for id in bleed_ids + shock_ids + poison_ids:
            hand_of_cards[id].card_type = CardTypes.DISABLED

        # Remove buffs
        num_rat_buffs = count_rat_buffs(screenshot)
        if num_rat_buffs >= 2 and len(buff_removal_ids) and card_turn == 0:
            print("Playing a buff removal card!")
            return buff_removal_ids[-1]

        # Movement logic
        if card_turn == 3:

            if current_stump == 0:
                opts = (poison_ids, bleed_ids)
            elif current_stump == 1:
                opts = (bleed_ids, shock_ids)
            else:
                opts = (shock_ids, poison_ids)

            if len(picked_ids := max(opts, key=len)):
                return picked_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase3(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        screenshot, _ = capture_window()

        # Precompute IDs
        bleed_ids, shock_ids, poison_ids = [], [], []
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type == DebuffTypes.BLEED:
                bleed_ids.append(i)
            elif card.debuff_type == DebuffTypes.SHOCK:
                shock_ids.append(i)
            elif card.debuff_type == DebuffTypes.POISON:
                poison_ids.append(i)
        valenti_ult_id = [i for i, card in enumerate(hand_of_cards) if find(vio.val_ult, card.card_image)]

        valenti_set = set(valenti_ult_id)

        have_damage_reduction = find(vio.damage_reduction, screenshot)

        # Disable one bleed + one shock (consistent with your original logic)
        if len(bleed_ids):
            hand_of_cards[bleed_ids[0]].card_type = CardTypes.GROUND
        if len(shock_ids):
            hand_of_cards[shock_ids[0]].card_type = CardTypes.GROUND

        # ------------------
        #  STUMP-SPECIFIC LOGIC
        # ------------------
        if current_stump == 1:
            if card_turn == 3 and len(bleed_ids):
                return bleed_ids[-1]

            elif card_turn == 3 and len(shock_ids) and len(valenti_ult_id):
                return shock_ids[-1]

            if not len(bleed_ids):
                for i in shock_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND

        elif current_stump == 2:
            if card_turn == 3 and len(valenti_ult_id) and len(shock_ids):
                return shock_ids[-1]

            if not len(valenti_ult_id):
                for i in shock_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND

                if have_damage_reduction:
                    # We still need to go to the leftmost stump!
                    all_val_ids = poison_ids + shock_ids
                    if card_turn >= 2 and len(all_val_ids):
                        print("Trying to get Valenti's ult...")
                        return [all_val_ids[0], all_val_ids[0] + 1]

                    if not len(shock_ids):
                        for i in poison_ids:
                            hand_of_cards[i].card_type = CardTypes.GROUND

        elif current_stump == 0:
            if card_turn == 3 and len(valenti_ult_id):
                return valenti_ult_id[-1]
            # Disable all Diane AoE cards, since they do no damage
            for i, card in enumerate(hand_of_cards):
                if find(vio.kdiane_aoe, card.card_image):
                    hand_of_cards[i].card_type = CardTypes.DISABLED

        # ------------------
        #  GLOBAL LOGIC
        # ------------------
        any_non_ground = False
        buff_disabled = False
        for i, card in enumerate(hand_of_cards):

            if have_damage_reduction and card.card_type == CardTypes.ULTIMATE:
                hand_of_cards[i].card_type = CardTypes.DISABLED

            if not buff_disabled and current_stump > 0 and card.card_type == CardTypes.BUFF:
                print("Softly disabling a buff")
                hand_of_cards[i].card_type = CardTypes.DISABLED
                buff_disabled = True

            if i in valenti_set:
                hand_of_cards[i].card_type = CardTypes.GROUND

            if hand_of_cards[i].card_type != CardTypes.GROUND:
                any_non_ground = True

        if not any_non_ground:
            return [-1, -3]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor2_phase1(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Here, only be careful to 1) Never play a buff, and 2) Only play debuff if we can play the 3 of them"""
        # Reset static variables
        if RatFightingStrategy.turns_in_f2p2 > 0:
            print("Resetting F2P2 counter")
            RatFightingStrategy.turns_in_f2p2 = 0

        screenshot, _ = capture_window()

        bleed_ids, shock_ids, poison_ids = [], [], []
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type == DebuffTypes.BLEED:
                bleed_ids.append(i)
            elif card.debuff_type == DebuffTypes.SHOCK:
                shock_ids.append(i)
            elif card.debuff_type == DebuffTypes.POISON:
                poison_ids.append(i)
        picked_bleed_ids = [i for i, card in enumerate(picked_cards) if card.debuff_type == DebuffTypes.BLEED]
        picked_shock_ids = [i for i, card in enumerate(picked_cards) if card.debuff_type == DebuffTypes.SHOCK]

        if card_turn == 0:
            if len(bleed_ids) and len(shock_ids) and len(poison_ids):
                return bleed_ids[-1]
        elif card_turn == 1:
            if len(picked_bleed_ids) and len(shock_ids) and len(poison_ids):
                return shock_ids[-1]
        elif card_turn == 2:
            if len(picked_bleed_ids) and len(picked_shock_ids) and len(poison_ids):
                return poison_ids[-1]

        # Disable all debuffs and buffs

        immortality = find(vio.immortality_buff, screenshot)
        for i, card in enumerate(hand_of_cards):
            if immortality and card.debuff_type in [DebuffTypes.BLEED, DebuffTypes.SHOCK]:
                hand_of_cards[i].card_type = CardTypes.DISABLED
            elif card.card_type == CardTypes.BUFF or find(
                vio.val_ult, card.card_image  # Let's prevent playing Valenti's ultimate if we don't have to
            ):
                hand_of_cards[i].card_type = CardTypes.GROUND

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor2_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Floor 2 phase 2: reactive strategy using vision-based stump detection."""
        screenshot, window_location = capture_window()

        if card_turn == 3:
            RatFightingStrategy.turns_in_f2p2 += 1
            print(f"We're on turn {RatFightingStrategy.turns_in_f2p2} in F2P2")

        bleed_ids, shock_ids, poison_ids = [], [], []
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type == DebuffTypes.BLEED:
                bleed_ids.append(i)
            elif card.debuff_type == DebuffTypes.SHOCK:
                shock_ids.append(i)
            elif card.debuff_type == DebuffTypes.POISON:
                poison_ids.append(i)
        strong_aoe_ids = [
            i for i, c in enumerate(hand_of_cards)
            if find(vio.kdiane_aoe, c.card_image) or find(vio.kdiane_ult, c.card_image)
        ]

        rat_hidden = find(vio.rat_hidden, screenshot)
        has_immortality = find(vio.immortality_buff, screenshot)
        debuff_ids = shock_ids + bleed_ids

        if rat_hidden:
            # Rat is hidden — avoid damaging center, burn low-value debuffs
            if card_turn == 0:
                print("Rat hidden: clicking non-center stump to avoid wasting damage...")
                click_im(Coordinates.get_coordinates("left_log"), window_location)
                time.sleep(0.5)
                click_im(Coordinates.get_coordinates("right_log"), window_location)
                time.sleep(0.3)

            if len(debuff_ids):
                return debuff_ids[-1]

            for i in strong_aoe_ids:
                hand_of_cards[i].card_type = CardTypes.GROUND
            for i in poison_ids:
                hand_of_cards[i].card_type = CardTypes.GROUND
        else:
            # Rat is visible — react to current_stump from vision detection
            if current_stump == 1 and len(strong_aoe_ids) and has_immortality:
                return strong_aoe_ids[-1]

            if current_stump != 1:
                # Reposition to center: play poison on last card, burn debuffs to set it up
                if card_turn == 3 and len(poison_ids):
                    print("Playing poison to move Rat to center...")
                    return poison_ids[-1]
                if len(debuff_ids) and len(poison_ids):
                    return debuff_ids[-1]

                for i in strong_aoe_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND
                for i in poison_ids:
                    hand_of_cards[i].card_type = CardTypes.GROUND

        # Save Diane cards if no immortality
        if not has_immortality:
            for i in strong_aoe_ids:
                print("Saving Diane strong cards...")
                hand_of_cards[i].card_type = CardTypes.DISABLED

        # Disable all non-poison debuffs, ground poisons
        for i, card in enumerate(hand_of_cards):
            if card.debuff_type in [DebuffTypes.BLEED, DebuffTypes.SHOCK]:
                hand_of_cards[i].card_type = CardTypes.DISABLED
            elif card.debuff_type == DebuffTypes.POISON:
                hand_of_cards[i].card_type = CardTypes.GROUND

        # If at center and a debuff was played this turn, play poison to maintain position
        if card_turn == 3 and not rat_hidden:
            if any(card.debuff_type in [DebuffTypes.SHOCK, DebuffTypes.BLEED] for card in picked_cards) and len(
                poison_ids
            ):
                print("We gotta play a poison to keep Rat in the center...")
                return poison_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor2_phase3(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        phase: int,
        card_turn: int,
        current_stump: int,
    ):
        """Phase 3: Diane disables, debuff prioritization, and stump logic."""

        screenshot, _ = capture_window()

        poison_ids = [i for i, c in enumerate(hand_of_cards) if c.debuff_type == DebuffTypes.POISON]

        # Diane AOEs
        strong_aoe_ids = [
            i for i, c in enumerate(hand_of_cards)
            if find(vio.kdiane_aoe, c.card_image) or find(vio.kdiane_ult, c.card_image)
        ]

        if card_turn == 3 and current_stump != 1 and len(poison_ids):
            print("We need to move the Rat back to the middle!")
            return poison_ids[-1]

        if find(vio.immortality_buff, screenshot) and len(strong_aoe_ids) and current_stump == 1:
            return strong_aoe_ids[-1]

        for i, card in enumerate(hand_of_cards):
            if card.debuff_type in [DebuffTypes.BLEED, DebuffTypes.SHOCK]:
                hand_of_cards[i].card_type = CardTypes.GROUND

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)


def get_debuff_type(card: Card) -> DebuffTypes:
    if is_shock_card(card):
        return DebuffTypes.SHOCK
    if is_bleed_card(card):
        return DebuffTypes.BLEED
    return DebuffTypes.POISON if is_poison_card(card) else DebuffTypes.NONE
