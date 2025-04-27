import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, find


class InduraBattleStrategy(IBattleStrategy):
    """The logic that should pick King's debuff card only if there's a stance present"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        screenshot, _ = capture_window()

        king_debuff_card_ids: list[int] = np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0]

        # Check if stance is present
        if find(vio.stance_active, screenshot):
            # TODO play King's debuff card
            pass

        # Else, disable King's debuff card
        elif len(king_debuff_card_ids):
            print("Disabling King's debuff card")
            hand_of_cards[king_debuff_card_ids[0]].card_type = CardTypes.DISABLED

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
