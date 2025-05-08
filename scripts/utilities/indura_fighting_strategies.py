import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, crop_image, find


class InduraBattleStrategy(IBattleStrategy):
    """The logic that should pick King's debuff card only if there's a stance present"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        screenshot, _ = capture_window()

        king_debuf_card_ids: list[int] = np.where(
            [
                find(vio.king_att, card.card_image) and card.card_rank.value != CardRanks.BRONZE.value
                for card in hand_of_cards
            ]
        )[0]
        played_king_debuf_cards: list[int] = np.where(
            [
                find(vio.king_att, card.card_image) and card.card_rank.value != CardRanks.BRONZE.value
                for card in picked_cards
            ]
        )[0]

        # Evaluate if the other party has played a King's debuff card
        six_empty_slots_image = crop_image(
            screenshot,
            Coordinates.get_coordinates("6_cards_top_left"),
            Coordinates.get_coordinates("6_cards_bottom_right"),
        )
        b_played_mini_king = find(vio.mini_king, six_empty_slots_image)
        if b_played_mini_king:
            print("The other party has played a King's debuff card!")

        # Check if stance is present, and play a debuff card if present. Also play it if we're on phase 2!
        if (
            len(king_debuf_card_ids)
            and (
                find(vio.snake_f3p2_counter, screenshot)
                or find(vio.melee_evasion, screenshot)
                or find(vio.ranged_evasion, screenshot)
                or find(vio.oxidize_indura, screenshot)
            )
            and not b_played_mini_king
            and not len(played_king_debuf_cards)
        ):
            # Play King's debuff card if we haven't played it already
            print("Playing King's debuff card!")
            return king_debuf_card_ids[-1]

        king_att_card_ids: list[int] = np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0]
        # Disable all King's attack cards if:
        # # - We have a counter (must disable), OR
        # # - We don't have melee evasion AND we haven't picked an ultimate
        # picked_ult_ids = np.where([card.card_type.value == CardTypes.ULTIMATE.value for card in picked_cards])[0]
        # if (
        #     find(vio.snake_f3p2_counter, screenshot)
        #     or find(vio.melee_evasion, screenshot)
        #     or find(vio.ranged_evasion, screenshot)
        #     or find(vio.oxidize_indura, screenshot)
        # ) or (not find(vio.melee_evasion, screenshot, threshold=0.8) and not len(picked_ult_ids)):
        for idx in king_att_card_ids:
            hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
