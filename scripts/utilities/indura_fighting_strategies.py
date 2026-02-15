import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, count_needle_image, crop_region, find


class InduraBattleStrategy(IBattleStrategy):
    """The logic that should pick King's debuff card only if there's a stance present"""

    oxidize_count = 0

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
        six_empty_slots_image = crop_region(screenshot, Coordinates.get_coordinates("6_cards_region"))
        heal_card_ids: list[int] = sorted(
            np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        if phase == 1:
            # Reset the oxidize count
            InduraBattleStrategy.oxidize_count = 0

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
            # Disable King's debuffs so that we don't play them by mistake
            elif len(king_debuf_card_ids):
                for idx in king_debuf_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Re-collection heal IDs in case we've disabled them
            heal_card_ids: list[int] = sorted(
                np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
                key=lambda idx: card_ranks[idx],
            )
            if not len(played_king_debuf_cards) and len(heal_card_ids):
                return heal_card_ids[-1]

            # If it's the first turn literally, play a debuff card first and foremost
            if IBattleStrategy._fight_turn == 0:
                debuff_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type == CardTypes.ATTACK_DEBUFF]
                if debuff_ids:
                    return debuff_ids[-1]

        elif phase == 2:
            # On phase 2, evaluate if Indura has multi-tiers activated
            have_multi_tiers = count_needle_image(vio.indura_tier, screenshot) > 1

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

                picked_card_id = king_debuf_card_ids[-1]
                if find(vio.oxidize_indura, screenshot):
                    # Make sure to increase the oxidize count accordingly!
                    if hand_of_cards[picked_card_id].card_rank == CardRanks.SILVER:
                        InduraBattleStrategy.oxidize_count += 1
                    elif hand_of_cards[picked_card_id].card_rank == CardRanks.GOLD:
                        InduraBattleStrategy.oxidize_count += 1.5
                    print(f"Increasing oxidize count to {InduraBattleStrategy.oxidize_count}")
                return picked_card_id

            # If we see an oxidize, we need to play level 2 or 3 cards
            if find(vio.oxidize_indura, screenshot):
                lvl2_cards = np.where((card_ranks == 1))[0]
                lvl3_cards = np.where((card_ranks == 2))[0]
                remaining_points = 3 - InduraBattleStrategy.oxidize_count
                if (len(lvl2_cards) or len(lvl3_cards)) and remaining_points > 0:
                    print(f"Trying to remove oxidize! {remaining_points} points remaining")

                    if remaining_points > 1 and len(lvl3_cards):
                        InduraBattleStrategy.oxidize_count += 1.5
                        return lvl3_cards[-1]

                    # Here, let's try to use silver cards if we can
                    InduraBattleStrategy.oxidize_count += 1
                    return sorted(
                        np.concatenate([lvl2_cards, lvl3_cards]), key=lambda idx: card_ranks[idx], reverse=True
                    )[-1]

            # Disable King's debuffs so that we don't play them by mistake
            for idx in king_debuf_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Disable all heal cards if we're not seeing an oxidize
            if card_turn < 2 or not find(vio.oxidize_indura, screenshot):
                # Disabled all heal cards, unless it's 3rd card
                for idx in heal_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

        elif phase == 3:
            print(f"We're on turn {InduraBattleStrategy._fight_turn} of phase 3")

            if InduraBattleStrategy._fight_turn == 0:
                ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]
                print("Disabling all Ultimates for first turn!")
                for id in ult_ids:
                    hand_of_cards[id].card_type = CardTypes.DISABLED

            if find(vio.mini_heal, six_empty_slots_image):
                # Disabled all heal cards
                for idx in heal_card_ids:
                    hand_of_cards[idx].card_type = CardTypes.DISABLED

            # Play a heal if we can, only on odd turns!
            heal_card_ids = sorted(
                np.where([card.card_type.value == CardTypes.RECOVERY.value for card in hand_of_cards])[0],
                key=lambda idx: card_ranks[idx],
            )
            if len(heal_card_ids):  # and InduraBattleStrategy._fight_turn % 2 == 0:
                return heal_card_ids[-1]

            # On phase 3, if we have Alpha ult, and haven't played a heal, play a King att card first
            if np.any([find(vio.alpha_ult, card.card_image) for card in hand_of_cards]):
                # Check if we have a King's attack card
                king_att_card_ids: list[int] = sorted(
                    np.where([find(vio.king_att, card.card_image) for card in hand_of_cards])[0],
                    key=lambda idx: card_ranks[idx],
                )
                played_heal_ids = np.where([card.card_type.value == CardTypes.RECOVERY.value for card in picked_cards])[
                    0
                ]
                played_king_att_card = np.where([find(vio.king_att, card.card_image) for card in picked_cards])[0]
                num_alpha_buffs = self._count_alpha_buffs(screenshot)
                if (
                    num_alpha_buffs < 2
                    and len(king_att_card_ids)
                    and not len(played_king_att_card)
                    and not len(played_heal_ids)
                ):
                    # Only play a King's attack card if we haven't played one yet
                    print("Playing King's attack card to increase Alpha's ult damage...")
                    return king_att_card_ids[-1]

        # More common code

        # Before proceeding, check if we need to disable Alpha att cards
        self._disable_alpha_att_cards(screenshot, hand_of_cards, picked_cards)

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

    def _disable_alpha_att_cards(self, screenshot: np.ndarray, hand_of_cards: list[Card], picked_cards: list[Card]):
        """Check if we need to disable Alpha attack cards based on the buffs we have"""

        num_buffs = self._count_alpha_buffs(screenshot)

        played_single_targets = np.where(
            [find(vio.king_att, card.card_image) or find(vio.lance_att, card.card_image) for card in picked_cards]
        )[0]
        played_alpha_att = np.where([find(vio.alpha_att, card.card_image) for card in picked_cards])[0]

        num_buffs += len(played_single_targets)
        num_buffs = max(0, min(3, num_buffs))
        num_buffs -= len(played_alpha_att)

        if num_buffs < 2:
            for item in hand_of_cards:
                if find(vio.alpha_att, item.card_image):
                    print("We can't play an Alpha card yet!")
                    item.card_type = CardTypes.DISABLED

        # No need to return anything since we modify the hand of card "in place"
        return hand_of_cards

    def _count_alpha_buffs(self, screenshot: np.ndarray):
        """Count how manny Alpha buffs we have currently. Doesn't consider played ST cards in the same turn"""
        half_screenshot = crop_region(screenshot, Coordinates.get_coordinates("half_screen_region"))
        return count_needle_image(vio.alpha_buff, half_screenshot, threshold=0.6)
