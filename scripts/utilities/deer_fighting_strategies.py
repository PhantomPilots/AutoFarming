import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardColors, CardTypes
from utilities.card_color_mapper import CardColorMapper
from utilities.deer_utilities import reorder_debuff_cards_to_front
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, find

ADVANCING_TYPES = {CardTypes.ATTACK, CardTypes.ATTACK_DEBUFF, CardTypes.ULTIMATE}
DEBUFF_TYPES = {CardTypes.DEBUFF, CardTypes.ATTACK_DEBUFF}

_COLOR_WHEEL = {
    CardColors.GREEN: CardColors.BLUE,
    CardColors.BLUE: CardColors.RED,
    CardColors.RED: CardColors.GREEN,
}


class DeerBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Deer"""

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        color_mapper: CardColorMapper | None = kwargs.get("color_mapper")
        if color_mapper is None or not color_mapper.is_calibrated:
            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        if phase in {2, 4}:
            return self.phase_2_4(hand_of_cards, picked_cards, card_turn=card_turn, color_mapper=color_mapper)

        return self.default_strategy(hand_of_cards, picked_cards, color_mapper=color_mapper)

    def phase_2_4(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, color_mapper: CardColorMapper
    ) -> int:
        """Take into account the roulette"""

        screenshot, _ = capture_window()

        red_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.RED)
        blue_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.BLUE)
        green_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.GREEN)

        green_card_ids = reorder_debuff_cards_to_front(hand_of_cards, green_card_ids)

        # Handle evasion: play a debuff card to remove it
        debuff_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type in DEBUFF_TYPES]
        if find(vio.evasion, screenshot, threshold=0.7) and (
            len(debuff_ids) and not any(card.card_type in DEBUFF_TYPES for card in picked_cards)
        ):
            return debuff_ids[-1]

        # Find the last card that actually advanced the roulette
        last_advancing_card = Card()
        for i in range(card_turn - 1, -1, -1):
            if picked_cards[i].card_type in ADVANCING_TYPES:
                last_advancing_card = picked_cards[i]
                break

        last_color = color_mapper.get_card_color(last_advancing_card)
        color_groups = {CardColors.RED: red_card_ids, CardColors.BLUE: blue_card_ids, CardColors.GREEN: green_card_ids}

        if last_color in _COLOR_WHEEL:
            next_color = _COLOR_WHEEL[last_color]
            if len(color_groups[next_color]):
                return color_groups[next_color][-1]

        # First card of turn or no advancing card played yet — check on-screen buff
        if last_advancing_card.card_image is None:
            if find(vio.red_buff, screenshot) and len(red_card_ids):
                return red_card_ids[-1]
            if find(vio.blue_buff, screenshot) and len(blue_card_ids):
                return blue_card_ids[-1]
            if find(vio.green_buff, screenshot) and len(green_card_ids):
                return green_card_ids[-1]

            max_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
            if len(max_ids):
                return max_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def default_strategy(
        self, hand_of_cards: list[Card], picked_cards: list[Card], color_mapper: CardColorMapper
    ) -> int:
        """Default strategy: play buff first, then pick the most abundant color group."""

        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        buff_ids = sorted(np.where(card_types == CardTypes.BUFF.value)[0], key=lambda idx: card_ranks[idx])
        if len(buff_ids) and not any(v == CardTypes.BUFF.value for v in picked_card_types):
            return buff_ids[-1]

        red_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.RED)
        blue_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.BLUE)
        green_card_ids = color_mapper.get_color_card_ids(hand_of_cards, CardColors.GREEN)

        green_card_ids = reorder_debuff_cards_to_front(hand_of_cards, green_card_ids)

        max_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
        if len(max_ids):
            return max_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
