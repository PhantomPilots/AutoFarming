import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, count_needle_image, crop_image, find


class InduraBattleStrategy(IBattleStrategy):
    """The logic that should pick King's debuff card only if there's a stance present"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int = 1, **kwargs) -> int:
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

        # Identify all King attack cards
        king_att_card_ids: list[int] = sorted(
            np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        six_empty_slots_image = crop_image(
            screenshot,
            Coordinates.get_coordinates("6_cards_top_left"),
            Coordinates.get_coordinates("6_cards_bottom_right"),
        )

        # On phase 2, evaluate if Indura has multi-tiers activated
        have_multi_tiers = False
        if phase == 2:
            have_multi_tiers = count_needle_image(vio.indura_tier, screenshot) > 1

        # Check if stance is present, and play a debuff card if present. Also play it if we're on phase 2!
        # But NOT if we're on phase 3
        b_played_mini_king = find(vio.mini_king, six_empty_slots_image)
        if (
            phase != 3  # Not on phase 3
            and len(king_debuf_card_ids)
            and (
                find(vio.snake_f3p2_counter, screenshot)
                or find(vio.melee_evasion, screenshot)
                or find(vio.ranged_evasion, screenshot)
                or have_multi_tiers  # For phase 2
                or find(vio.oxidize_indura, screenshot)  # For phase 2
            )
            and not b_played_mini_king  # No friend has played a King's debuff card
            and not len(played_king_debuf_cards)  # We haven't played a King's debuff card ourselves
        ):
            if have_multi_tiers:
                print("Seeing multiple tiers! Playing King's debuff card!")
            return king_debuf_card_ids[-1]

        # Disable all heal cards if someone has played one already OR it's the first fight turn!
        heal_card_ids: list[int] = sorted(
            np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        if find(vio.mini_heal, six_empty_slots_image) or self._fight_turn == 0:
            # Disabled all heal cards
            for idx in heal_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED
        # Also disable all heal rank 1 cards if we're on phase 2. Use them only for healing
        elif phase == 2:
            for idx in heal_card_ids:
                if hand_of_cards[idx].card_rank.value == CardRanks.BRONZE.value:
                    # Disable the heal rank 1 card
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

        # On phase 3, if we have Alpha ult, and haven't played a heal, play a King att card if we haven't played a heal yet
        if phase == 3 and np.any([find(vio.alpha_ult, card.card_image) for card in hand_of_cards]):
            # Check if we have a King's attack card
            played_king_att_card = np.where([find(vio.king_att, card.card_image) for card in picked_cards])[0]
            if len(king_att_card_ids) and not len(played_king_att_card) and not len(picked_heal_ids):
                # Only play a King's attack card if we haven't played one yet
                print("Playing King's attack card to increase Alpha's ult damage...")
                return king_att_card_ids[-1]

        # Disable all King's attack cards
        for idx in king_att_card_ids:
            hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Disable all debuff cards (since we don't want to play Alpha's debuff)
        debuff_card_ids: list[int] = np.where(
            [card.card_type.value == CardTypes.ATTACK_DEBUFF.value for card in hand_of_cards]
        )[0]
        for idx in debuff_card_ids:
            hand_of_cards[idx].card_type = CardTypes.DISABLED

        # But if EVERYTHING is disabled... re-enable everything again as a Debuff
        if np.all([card.card_type in [CardTypes.DISABLED, CardTypes.GROUND] for card in hand_of_cards]):
            # print("All cards are DISABLED! Let's re-enable them as attack-debuffs...")
            for idx in range(len(hand_of_cards)):
                if hand_of_cards[idx].card_type == CardTypes.DISABLED:
                    # Re=enable it as a Debuff
                    hand_of_cards[idx].card_type = CardTypes.ATTACK_DEBUFF

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
