import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, count_needle_image, crop_image, find


class InduraBattleStrategy(IBattleStrategy):
    """The logic that should pick King's debuff card only if there's a stance present"""

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int = 1, card_turn=0, **kwargs
    ) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """
        # Common code between all 3 phases
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
        heal_card_ids: list[int] = sorted(
            np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        if phase == 1:
            # Disable all heal cards if someone has played one already OR it's the first fight turn!
            if find(vio.mini_heal, six_empty_slots_image) or IBattleStrategy._fight_turn == 0:
                # Disabled all heal cards, unless it's 3rd card and not 1st turn
                for idx in heal_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Check if stance is present, and play a debuff card if present
            b_played_mini_king = find(vio.mini_king, six_empty_slots_image)
            if (
                len(king_debuf_card_ids)
                and find(vio.snake_f3p2_counter, screenshot)
                and not b_played_mini_king  # No friend has played a King's debuff card
                and not len(played_king_debuf_cards)  # We haven't played a King's debuff card ourselves
            ):
                return king_debuf_card_ids[-1]

            # Re-collection heal IDs in case we've disabled them
            heal_card_ids: list[int] = sorted(
                np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
                key=lambda idx: card_ranks[idx],
            )
            if not len(played_king_debuf_cards) and len(heal_card_ids):
                return heal_card_ids[-1]

        elif phase == 2:
            # On phase 2, evaluate if Indura has multi-tiers activated
            have_multi_tiers = False
            have_multi_tiers = count_needle_image(vio.indura_tier, screenshot) > 1

            # Check if stance is present, and play a debuff card if present. Also play it if we're on phase 2!
            b_played_mini_king = find(vio.mini_king, six_empty_slots_image)
            if (
                len(king_debuf_card_ids)
                and (
                    find(vio.melee_evasion, screenshot)
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

            # Disable all heal cards if someone has played one already
            if find(vio.mini_heal, six_empty_slots_image) or card_turn < 2 or not find(vio.oxidize_indura, screenshot):
                # Disabled all heal cards, unless it's 3rd card
                for idx in heal_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED
            # Play a heal card in the last turn, when it's not the first "fight turn"
            elif card_turn == 2 and len(heal_card_ids):
                return heal_card_ids[-1]

        elif phase == 3:
            if find(vio.mini_heal, six_empty_slots_image):
                # Disabled all heal cards
                for idx in heal_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            picked_heal_ids = np.where([card.card_type.value == CardTypes.RECOVERY.value for card in picked_cards])[0]

            # Play a heal if we can
            heal_card_ids = sorted(
                np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
                key=lambda idx: card_ranks[idx],
            )
            if len(heal_card_ids):
                return heal_card_ids[-1]

            # On phase 3, if we have Alpha ult, and haven't played a heal, play a King att card first
            king_att_card_ids: list[int] = sorted(
                np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0],
                key=lambda idx: card_ranks[idx],
            )
            if np.any([find(vio.alpha_ult, card.card_image) for card in hand_of_cards]):
                # Check if we have a King's attack card
                played_king_att_card = np.where([find(vio.king_att, card.card_image) for card in picked_cards])[0]
                if len(king_att_card_ids) and not len(played_king_att_card) and not len(picked_heal_ids):
                    # Only play a King's attack card if we haven't played one yet
                    print("Playing King's attack card to increase Alpha's ult damage...")
                    return king_att_card_ids[-1]

        # More common code

        # Try to play an ultimate
        ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]
        if len(ult_ids):
            return ult_ids[-1]

        # Try to play attack cards only if we can
        attack_card_ids = sorted(
            np.where(
                [
                    card.card_type == CardTypes.ATTACK and not find(vio.king_att, card.card_image)
                    for card in hand_of_cards
                ]
            )[0],
            key=lambda idx: card_ranks[idx],
        )
        if len(attack_card_ids):
            return attack_card_ids[-1]

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
