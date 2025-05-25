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

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

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
            and not b_played_mini_king  # No friend has played a King's debuff card
            and not len(played_king_debuf_cards)  # We haven't played a King's debuff card ourselves
        ):
            print("Playing King's debuff card!")
            return king_debuf_card_ids[-1]

        # Disable all heal cards if someone has played one already
        heal_card_ids: list[int] = sorted(
            np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        if find(vio.mini_heal, six_empty_slots_image):
            # Disabled all heal cards
            for idx in heal_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

        # But if we haven't disabled a heal, use one by default
        picked_heal_ids = np.where([card.card_type.value == CardTypes.RECOVERY.value for card in picked_cards])[0]
        # We need to re-access the heal card IDs, since we may have disabled some
        heal_card_ids = sorted(
            np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        if len(heal_card_ids) and not picked_heal_ids.size:
            return heal_card_ids[-1]
        elif picked_heal_ids.size:
            print("We have an additional heal card but we've played one already")

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

        # But if EVERYTHING is disabled... re-enable everything again as a Debuff
        if np.all(
            [card.card_type == CardTypes.DISABLED or card.card_type == CardTypes.GROUND for card in hand_of_cards]
        ):
            print("All cards are DISABLED! Let's re-enable them as attack-debuffs...")
            for idx in range(len(hand_of_cards)):
                if hand_of_cards[idx].card_type == CardTypes.DISABLED:
                    # Re=enable it as a Debuff
                    hand_of_cards[idx].card_type = CardTypes.ATTACK_DEBUFF

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
