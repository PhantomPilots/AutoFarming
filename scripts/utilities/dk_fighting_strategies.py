import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardColors, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.pattern_match_strategies import TemplateMatchingStrategy
from utilities.utilities import capture_window, count_needle_image, crop_region, find


class DemonKingBattleStrategy(IBattleStrategy):
    """Demon King battle strategy"""

    def get_next_card_index(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        *,
        phase: int = 1,
        card_turn=0,
        color_cards_dict: dict[CardColors, list[np.ndarray]] = {},
        **kwargs,
    ) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        return (
            self.get_next_card_index_phase1(hand_of_cards, picked_cards)
            if phase == 1
            else self.get_next_card_index_phase2(hand_of_cards, picked_cards, card_turn, color_cards_dict)
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
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
        color_cards_dict: dict[CardColors, list[np.ndarray]],
    ) -> int:
        """We should be able to 1-turn it!"""
        screenshot, _ = capture_window()

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        # To try to remove a stance if needed
        picked_stance_removal_ids = sorted(
            np.where([find(vio.freyr_1, card.card_image) for card in picked_cards])[0],
            key=lambda idx: card_ranks[idx],
        )

        if its_rules_time := find(vio.dk_empty_slot, screenshot):
            print("Let's try to follow the rules!")

            rules_window = crop_region(screenshot, Coordinates.get_coordinates("rules_window_region"))
            rules_width = int(rules_window.shape[1] / 3)
            first_rule_window = rules_window[:, :rules_width, ...]
            second_rule_window = rules_window[:, rules_width : 2 * rules_width, ...]
            third_rule_window = rules_window[:, 2 * rules_width :, ...]

            # Evaluate all windows
            color_rules: list[CardColors] = []
            for rule_window in (first_rule_window, second_rule_window, third_rule_window):
                rule, _ = self._best_rule_for_window(rule_window)
                color_rules.append(rule)

            print(f"Detected color rules: {[rule.name for rule in color_rules]}")

            if card_turn <= 2:
                target_rule = color_rules[card_turn]

                # Retrieve all images corresponding to the target_rule color from the given color_cards_dict
                potential_cards = color_cards_dict[target_rule]
                # Try to find a card corresponding to this color
                for idx, card in enumerate(hand_of_cards):
                    for pot_card in potential_cards:
                        best_rect = TemplateMatchingStrategy.find(card.card_image, pot_card)
                        if best_rect is not None and best_rect.size > 0:
                            return idx

            else:
                print(f"[WARN] Card turn is {card_turn}>2, wierdly, so we cannot follow any rule.")

        elif find(vio.corrosion_stance, screenshot) and not len(picked_stance_removal_ids):
            matches = [
                (idx, card.card_rank.value)
                for idx, card in enumerate(hand_of_cards)
                if find(vio.freyr_1, card.card_image)
            ]

            # Group indices by rank value (0 → bronze, 1 → silver)
            bronze_ids = [idx for idx, rank in matches if rank == 0]
            silver_ids = [idx for idx, rank in matches if rank >= 1]

            # Sort both by card_ranks in one go
            bronze_stance_removal_ids = sorted(bronze_ids, key=lambda idx: card_ranks[idx])
            silver_stance_removal_ids = sorted(silver_ids, key=lambda idx: card_ranks[idx])

            if len(silver_stance_removal_ids):
                print("Cancelling the stance!")
                return silver_stance_removal_ids[-1]

            # If we're here, we don't have any silver and we haven't played any silver yet. Let's try to merge
            if len(bronze_stance_removal_ids) >= 2:
                print("Merging to try to cancel the stance...")
                return [bronze_stance_removal_ids[-2], bronze_stance_removal_ids[-1]]

        else:
            # Let's disable all Freyr stance-cancel cards
            freyr_ids = np.where([find(vio.freyr_1, card.card_image) for card in hand_of_cards])[0]
            if len(freyr_ids):
                print("Saving Freyr stance cancel cards, just in case!")
            for idx in freyr_ids:
                idx: int
                hand_of_cards[idx].card_type = CardTypes.DISABLED

        # Play a Skuld stance if we can
        stance_active = find(vio.stance_counter, screenshot)
        stance_card_ids = sorted(
            np.where([find(vio.skuld_stance, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        if len(stance_card_ids) and not stance_active:
            print("Let's play a Skuld stance!")
            return stance_card_ids[-1]
        else:
            # Let's disable the card(s) such that the "Smart" strategy doesn't play them
            for idx in stance_card_ids:
                hand_of_cards[idx].card_type = CardTypes.DISABLED

        # # Play a Skuld attack if possible
        # skuld_att_ids = sorted(
        #     np.where([find(vio.skuld_st, card.card_image) for card in hand_of_cards])[0],
        #     key=lambda idx: card_ranks[idx],
        # )
        # if len(skuld_att_ids):
        #     return skuld_att_ids[-1]

        # Otherwise, we cannot kill it in 1 turns, so let's default to regular strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _best_rule_for_window(self, window: np.ndarray) -> tuple[CardColors, float]:
        """Return the best (rule_level, confidence) for one rule window."""
        results = {
            CardColors(1): vio.strength_rule.find_with_confidence(window, threshold=0.8),
            CardColors(2): vio.hp_rule.find_with_confidence(window, threshold=0.8),
            CardColors(3): vio.speed_rule.find_with_confidence(window, threshold=0.8),
        }

        # Pick the rule with the highest confidence
        best_level, (_, best_conf) = max(results.items(), key=lambda kv: kv[1][1] if kv[1][1] is not None else -np.inf)

        return best_level, best_conf

    def _reorder_freyr_ids(self, hand_of_cards: list[Card], list_of_ids: list[int]):
        """Reorder the Freyr stance cancel ids such that they are at the beginning of the list"""

        # Add the buff removal ID to the beginning of the list
        freyr_ids = np.where([find(vio.freyr_1, hand_of_cards[idx].card_image) for idx in list_of_ids])[0]
        for idx in freyr_ids:
            # print("Setting lowest priority to buff removal card")
            list_of_ids = np.concatenate(([list_of_ids[idx]], np.delete(list_of_ids, idx)))

        return list_of_ids
