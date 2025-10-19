import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, count_needle_image, crop_image, find


class DemonKingBattleStrategy(IBattleStrategy):
    """Demon King battle strategy"""

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], *, phase: int = 1, card_turn=0, dk_team=0, **kwargs
    ) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        return (
            self.get_next_card_index_phase1(hand_of_cards, picked_cards)
            if phase == 1
            else self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn, dk_team)
        )

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """We should be able to 1-turn it!"""

        if len(gelda_card_id := np.where([find(vio.gelda_card, card.card_image) for card in hand_of_cards])[0]):
            return gelda_card_id[-1]
        if len(cusack_card_id := np.where([find(vio.cusack_cleave, card.card_image) for card in hand_of_cards])[0]):
            return cusack_card_id[-1]
        if len(meli_card_id := np.where([find(vio.dk_meli_st, card.card_image) for card in hand_of_cards])[0]):
            return meli_card_id[-1]

        # Otherwise, we cannot kill it in 1 turns, so let's default to regular strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, dk_team: int
    ) -> int:
        """We should be able to 1-turn it!"""
        screenshot, _ = capture_window()

        card_ranks = np.array([card.card_rank for card in hand_of_cards])
        card_types = np.array([card.card_type for card in hand_of_cards])

        if rules_time := find(vio.dk_empty_slot, screenshot):
            print("Let's try to follow the rules!")

            # First, find the positions of each rule
            lvl_1_rect = vio.lvl_1_rule.find_all_rectangles(screenshot, threshold=0.85)[0]
            lvl_2_rect = vio.lvl_2_rule.find_all_rectangles(screenshot, threshold=0.85)[0]
            lvl_3_rect = vio.lvl_3_rule.find_all_rectangles(screenshot, threshold=0.85)[0]

            rects = [lvl_1_rect, lvl_2_rect, lvl_3_rect]

            # Filter out empty ones and ensure each has 2D shape
            valid = [r[np.newaxis, :] if r.ndim == 1 else r for r in rects if r is not None and r.size > 0]

            # Skip everything else if all are empty
            if not valid or card_turn >= len(valid):
                return -1

            # Build the matching source index list
            source_idx = np.concatenate([np.full(len(r), i + 1) for i, r in enumerate(valid)])

            # Concatenate and sort
            all_rules = np.concatenate(valid, axis=0)
            sort_idx = np.argsort(all_rules[:, 1])
            sorted_sources = source_idx[sort_idx]

            target_card_rank = CardRanks(sorted_sources[card_turn])
            print("Current rule?", target_card_rank)

            candidates = np.where([card.card_rank == target_card_rank for card in hand_of_cards])[0]
            if len(candidates):
                return candidates[-1]

        # Play a Skuld stance if we can
        stance_active = find(vio.stance, screenshot)
        stance_card_ids = np.where([find(vio.skuld_stance, card.card_image) for card in hand_of_cards])[0]
        if len(stance_card_ids) and not stance_active:
            print("Let's play a Skuld stance!")
            return stance_card_ids[-1]
        else:
            # Let's disable the card(s) such that the "Smart" strategy doesn't play them
            for idx in stance_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Otherwise, we cannot kill it in 1 turns, so let's default to regular strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
