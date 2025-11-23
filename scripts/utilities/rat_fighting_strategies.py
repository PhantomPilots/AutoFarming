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

        if floor == 1 and phase in {1, 2}:
            return self.floor1_phase12(hand_of_cards, picked_cards, phase, card_turn, current_stump)
        if floor == 1 and phase == 3:
            return self.floor1_phase3(hand_of_cards, picked_cards, phase, card_turn, current_stump)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase12(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Make sure we're always rotating the Rat... And *always* save one bleed card if possible"""
        screenshot, _ = capture_window()

        # For bleed IDs, don't play bleeds on phase 2
        bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED and phase != 2 for card in hand_of_cards])[0]
        shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in hand_of_cards])[0]
        poison_ids = np.where([card.debuff_type == DebuffTypes.POISON for card in hand_of_cards])[0]
        buff_removal_ids = np.where([is_buff_removal(card) for card in hand_of_cards])[0]

        # First, if we see too many buffs on the Rat, let's try to remove them
        num_rat_buffs = count_rat_buffs(screenshot)
        if num_rat_buffs >= 2 and len(buff_removal_ids) and card_turn == 0:
            # Play a buff removal card
            print("Playing a buff removal card!")
            return buff_removal_ids[-1]

        if card_turn == 3:
            # Let's try to move the Rat
            if current_stump == 0:
                picked_ids = max(poison_ids, bleed_ids, key=len)
            elif current_stump == 1:
                picked_ids = max(bleed_ids, shock_ids, key=len)
            elif current_stump == 2:
                picked_ids = max(shock_ids, poison_ids, key=len)
            if len(picked_ids):
                return picked_ids[-1]

        else:
            for card in hand_of_cards:
                if card.debuff_type != DebuffTypes.NONE or (phase == 2 and find(vio.val_ult, card.card_image)):
                    card.card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor1_phase3(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn: int, current_stump: int
    ):
        """Phase 3, the hardcore one..."""

        # For bleed IDs, don't play bleeds on phase 2
        bleed_ids = np.where([card.debuff_type == DebuffTypes.BLEED and phase != 2 for card in hand_of_cards])[0]
        shock_ids = np.where([card.debuff_type == DebuffTypes.SHOCK for card in hand_of_cards])[0]
        poison_ids = np.where([card.debuff_type == DebuffTypes.POISON for card in hand_of_cards])[0]
        valenti_ult_id = np.where([find(vio.val_ult, card.card_image) for card in hand_of_cards])[0]

        if card_turn == 3:
            # Let's try to move the Rat
            if current_stump == 0 and len(valenti_ult_id):
                picked_ids = valenti_ult_id
            elif current_stump == 1:
                picked_ids = bleed_ids if len(bleed_ids) else shock_ids if len(shock_ids) else []
            elif current_stump == 2:
                picked_ids = shock_ids if len(shock_ids) else poison_ids if len(poison_ids) else []
            if len(picked_ids):
                return picked_ids[-1]

        else:
            for card in hand_of_cards:
                if card.debuff_type != DebuffTypes.NONE or find(vio.val_ult, card.card_image):
                    card.card_type = CardTypes.DISABLED

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)


def get_debuff_type(card: Card) -> DebuffTypes:
    if is_shock_card(card):
        return DebuffTypes.SHOCK
    if is_bleed_card(card):
        return DebuffTypes.BLEED
    return DebuffTypes.POISON if is_poison_card(card) else DebuffTypes.NONE
