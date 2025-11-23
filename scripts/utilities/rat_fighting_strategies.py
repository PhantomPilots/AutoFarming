from enum import Enum, auto
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
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

    def get_next_card_index(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        floor: int,
        phase: int,
        card_turn: int,
        current_stump: int,
        **kwargs
    ) -> int:
        """Distinguish between floors and phases"""

        # First of all, populate useful information for each card
        for card in hand_of_cards:
            card.debuff_type = get_debuff_type(card)
        for card in picked_cards:
            card.debuff_type = get_debuff_type(card)

        if floor == 1 and phase in {1, 2}:
            return self.floor1_phase12(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 1 and phase == 3:
            return self.floor1_phase3(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 1:
            return self.floor2_phase1(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 2:
            return self.floor2_phase2(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 2 and phase == 3:
            return self.floor2_phase3(hand_of_cards, picked_cards, phase, card_turn, current_stump)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase12(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Make sure we're always rotating the Rat... And *always* save one bleed card if possible"""
        screenshot, _ = capture_window()

        # For bleed IDs, don't play bleeds on phase 2
        bleed_ids = np.where(
            [
                card.debuff_type == DebuffTypes.BLEED and card.card_type != CardTypes.DISABLED and phase != 2
                for card in hand_of_cards
            ]
        )[0]
        shock_ids = np.where(
            [card.debuff_type == DebuffTypes.SHOCK and card.card_type != CardTypes.DISABLED for card in hand_of_cards]
        )[0]
        poison_ids = np.where(
            [card.debuff_type == DebuffTypes.POISON and card.card_type != CardTypes.DISABLED for card in hand_of_cards]
        )[0]
        buff_removal_ids = np.where([is_buff_removal(card) for card in hand_of_cards])[0]

        # First, if we see too many buffs on the Rat, let's try to remove them
        num_rat_buffs = count_rat_buffs(screenshot)
        if num_rat_buffs >= 2 and len(buff_removal_ids) and card_turn == 0:
            # Play a buff removal card
            print("Playing a buff removal card!")
            return buff_removal_ids[-1]

        if card_turn == 3:
            # Let's try to move the Rat
            picked_ids = []
            if current_stump == 0:
                picked_ids = max(poison_ids, bleed_ids, key=len)
            elif current_stump == 1:
                picked_ids = max(bleed_ids, shock_ids, key=len)
            elif current_stump == 2:
                picked_ids = max(shock_ids, poison_ids, key=len)
            if len(picked_ids):
                return picked_ids[-1]

        for card in hand_of_cards:
            if card.debuff_type != DebuffTypes.NONE:
                card.card_type = CardTypes.GROUND

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase3(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Phase 3, the hardcore one..."""
        screenshot, _ = capture_window()

        # For bleed IDs, don't play bleeds on phase 2
        bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED and phase != 2 for card in hand_of_cards])[0]
        shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in hand_of_cards])[0]
        poison_ids = np.where([card.debuff_type == DebuffTypes.POISON for card in hand_of_cards])[0]
        valenti_ult_id = np.where([find(vio.val_ult, card.card_image) for card in hand_of_cards])[0]

        if find(vio.damage_reduction, screenshot):
            print("We gotta disable all ults except Valenti's!")
            for i, card in enumerate(hand_of_cards):
                if i not in valenti_ult_id and card.card_type == CardTypes.ULTIMATE:
                    card.card_type = CardTypes.DISABLED

        if card_turn == 3:
            # Let's try to move the Rat
            picked_ids = []
            if current_stump == 0 and len(valenti_ult_id):
                picked_ids = valenti_ult_id
            elif current_stump == 1:
                picked_ids = bleed_ids if len(bleed_ids) else shock_ids if len(shock_ids) else []
            elif current_stump == 2:
                picked_ids = shock_ids if len(shock_ids) else poison_ids if len(poison_ids) else []
            if len(picked_ids):
                return picked_ids[-1]

        for card in hand_of_cards:
            if card.debuff_type != DebuffTypes.NONE:
                card.card_type = CardTypes.GROUND

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor2_phase1(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Here, only be careful to 1) Never play a buff, and 2) Only play debuff if we can play the 3 of them"""
        bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED for card in hand_of_cards])[0]
        shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in hand_of_cards])[0]
        poison_ids = np.where([card.debuff_type == DebuffTypes.POISON for card in hand_of_cards])[0]
        picked_bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED for card in picked_cards])[0]
        picked_shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in picked_cards])[0]

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
        for card in hand_of_cards:
            if card.debuff_type != DebuffTypes.NONE or card.card_type == CardTypes.BUFF:
                card.card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor2_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Here, we should only"""
        screenshot, _ = capture_window()

        bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED for card in hand_of_cards])[0]
        shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in hand_of_cards])[0]
        poison_ids = np.where([card.debuff_type == DebuffTypes.POISON for card in hand_of_cards])[0]

        # Diane AOEs
        diane_aoe_ids = np.where(
            [find(vio.kdiane_aoe, c.card_image) or find(vio.kdiane_ult, c.card_image) for c in hand_of_cards]
        )[0]

        # If no immortality anymore, let's save all good KDiane cards
        if not find(vio.immortality_buff, screenshot):
            for i in diane_aoe_ids:
                print("Saving Diane strong cards for phase 3...")
                hand_of_cards[i].card_type = CardTypes.DISABLED

        if card_turn == 3 and find(vio.rat_hidden, screenshot):
            if len(poison_ids):
                return poison_ids[-1]
            elif len(bleed_ids) or len(shock_ids):
                # We cannot make the rat go back to the middle stump, but we *must* make it go somewhere deterministically
                return max(bleed_ids, shock_ids, key=len)[-1]

        # Disable all debuffs
        for card in hand_of_cards:
            if card.debuff_type != DebuffTypes.NONE:
                card.card_type = CardTypes.DISABLED

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

        poison_ids = np.where([c.debuff_type == DebuffTypes.POISON for c in hand_of_cards])[0]

        # Diane AOEs
        diane_aoe_ids = np.where(
            [find(vio.kdiane_aoe, c.card_image) or find(vio.kdiane_ult, c.card_image) for c in hand_of_cards]
        )[0]

        if card_turn == 3 and current_stump != 1 and len(poison_ids):
            print("We need to move the Rat back to the middle!")
            return poison_ids[-1]

        if find(vio.immortality_buff, screenshot) and len(diane_aoe_ids) and current_stump == 1:
            return diane_aoe_ids[-1]

        for card in hand_of_cards:
            if card.debuff_type != DebuffTypes.NONE:
                card.card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)


def get_debuff_type(card: Card) -> DebuffTypes:
    if is_shock_card(card):
        return DebuffTypes.SHOCK
    if is_bleed_card(card):
        return DebuffTypes.BLEED
    return DebuffTypes.POISON if is_poison_card(card) else DebuffTypes.NONE
