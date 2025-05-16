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

        six_empty_slots_image = crop_image(
            screenshot,
            Coordinates.get_coordinates("6_cards_top_left"),
            Coordinates.get_coordinates("6_cards_bottom_right"),
        )
        # Evaluate if the other party has played a King's debuff card
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

        # Disable all heal cards if someone has played one already
        if find(vio.mini_heal, six_empty_slots_image):
            # Disabled all heal cards
            heal_card_ids: list[int] = np.where([find(vio.king_heal, card.card_image) for card in hand_of_cards])[0]
            for idx in heal_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Disable all King's attack cards
        king_att_card_ids: list[int] = np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0]
        for idx in king_att_card_ids:
            hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Disable all debuff cards (since we don't want to play Alpha's debuff)
        debuff_card_ids: list[int] = np.where(
            [card.card_type.value == CardTypes.ATTACK_DEBUFF.value for card in hand_of_cards]
        )[0]
        for idx in debuff_card_ids:
            hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
