"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import (
    pick_card_type,
    process_card_move,
    process_card_play,
)
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.models import AmplifyCardPredictor
from utilities.utilities import (
    capture_window,
    count_empty_card_slots,
    determine_card_merge,
    find,
    get_hand_cards,
)


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    card_turn = 0

    def pick_cards(self, *args, **kwargs) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        card_indices = []
        picked_cards = []
        for _ in range(8):

            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards)

            # Update the indices and cards lists
            card_indices.append(next_index)
            if isinstance(next_index, Integral):
                picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards = self._update_hand_of_cards(hand_of_cards, [next_index])

            # Increment the card turn
            IBattleStrategy.card_turn += 1

        IBattleStrategy.card_turn = 0
        return original_hand_of_cards, card_indices

    def _update_hand_of_cards(self, house_of_cards: list[Card], indices: list[int]) -> list[Card]:
        """Given the selected indices, select the cards accounting for card shifts.

        Args:
            house_of_cards (list[Card]): List of the cards in hand before any is played.
            indices (list[int]): Original cards we want to play.
                                  The indices will have to be modified accounting for shifts and merges RECURSIVELY.
        """
        for idx in indices:
            if isinstance(idx, Integral):
                # We're playing a card
                process_card_play(house_of_cards, idx)

            elif isinstance(idx, (tuple, list)):
                # We're moving a card
                process_card_move(house_of_cards, idx[0], idx[1])

            else:
                raise ValueError(f"Index {idx} is neither an integer nor a list/tuple!")

        # Finally, return the new card array and indices modified
        return house_of_cards

    @abc.abstractmethod
    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Always get the rightmost 4 cards"""
        return 7


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def get_next_card_index(cls, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Apply the logic to extract the right indices.
        NOTE: Add attack-debuff cards too."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # STANCE CARDS -- Use it if there's no recovery card
        stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
        if (
            len(stance_ids)
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
            and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size
        ):
            return stance_ids[-1]

        # CARD MERGE -- If there's a card that generates a merge, pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1]):
                return i

        # FIRST ATATCK-DEBUFF CARD
        att_debuff_ids = np.where(card_types == CardTypes.ATTACK_DEBUFF.value)[0]
        # Sort them based on card ranks
        att_debuff_ids: np.ndarray = np.array(sorted(att_debuff_ids, key=lambda idx: card_ranks[idx], reverse=False))
        if att_debuff_ids.size and not np.where(picked_card_types == CardTypes.ATTACK_DEBUFF.value)[0].size:
            return att_debuff_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=False)
        if len(attack_ids):
            return attack_ids[-1]

        # CONSIDER THE REMAINING CARDS, appending all the remaining IDs together
        selected_ids = np.hstack((stance_ids, recovery_ids, att_debuff_ids))

        # Default to -1
        return selected_ids[-1] if len(selected_ids) else -1


class Floor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for FLoor 4"""

    with_shield = False

    def pick_cards(self, phase) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        print("Card types:", [card.card_type.name for card in hand_of_cards])
        print("Card ranks:", [card.card_rank.name for card in hand_of_cards])

        card_indices = []
        picked_cards = []
        for _ in range(5):
            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards, phase=phase)

            # print(f"Picked index {next_index} with card {hand_of_cards[next_index].card_type.name}")

            # Update the indices and cards lists
            card_indices.append(next_index)
            if isinstance(next_index, Integral):
                picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards = self._update_hand_of_cards(hand_of_cards, [next_index])

            # Increment card turn
            IBattleStrategy.card_turn += 1

        # Reset the card turn
        IBattleStrategy.card_turn = 0

        # raise ValueError("Debugging")

        return original_hand_of_cards, card_indices

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Extract the indices based on the list of cards and the current bird phase"""
        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(hand_of_cards, picked_cards)
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards)

        return card_index

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""
        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # First of all, we may need to cure all the debuffs!
        screenshot, _ = capture_window()
        if find(vio.block_skill_debuf, screenshot):
            print("We have a block-skill debuff, we need to cleanse!")
            # We need to use Meli's AOE and Megelda's recovery!

            # Play Meli's AOE card if we have it
            for i, card in enumerate(hand_of_cards):
                if find(vio.meli_aoe, card.card_image):
                    return i

            # RECOVERY CARDS
            recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
            if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
                return recovery_ids[-1]

        # Click on a card if it generates a SILVER merge
        for i in range(1, len(hand_of_cards) - 1):
            if (
                determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1])
                and hand_of_cards[i].card_rank == CardRanks.BRONZE
                and hand_of_cards[i - 1].card_rank == CardRanks.BRONZE
            ):
                return i

        # STANCE CARDS
        stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
        if len(stance_ids) and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size:
            return stance_ids[-1]

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # List of cards of high rank
        silver_ids = np.where(card_ranks == 1)[0]
        # Now just click on a bronze card if we have one, and we don't have enough silver cards
        bronze_ids = np.where((card_ranks == CardRanks.BRONZE.value) | (card_ranks == CardRanks.GOLD.value))[0]
        if len(bronze_ids) and len(silver_ids) <= 3:
            bronze_ids = bronze_ids[::-1]  # To start searching from the right
            # Get the next bronze card that doesn't correspond to a RECOVERY OR a Meli AOE
            return next(
                (
                    bronze_item
                    for bronze_item in bronze_ids
                    if hand_of_cards[bronze_item].card_type != CardTypes.RECOVERY
                    and not find(vio.meli_aoe, hand_of_cards[bronze_item].card_image)
                ),
                -1,  # Default
            )

        # By default, return the rightmost card
        print("Defaulting to the rightmost card...")
        return -1
        # return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _with_shield_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]):
        """What to do if we have a shield? GO HAM"""

        print("We have a shield, playing super HAM cards!")

        # TODO: Run the HAM classifier here

        # Pick ultimates if we don't have other high-hitting cards
        ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]
        if len(ult_ids):
            return ult_ids[-1]

        if Floor4BattleStrategy.card_turn == 4:
            # Account for shield removal
            Floor4BattleStrategy.with_shield = False

    def _without_shield_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card], silver_ids: np.ndarray):
        """If we don't have a shield, let's get ready for it"""
        total_num_silver_cards = len(silver_ids) + len([card for card in picked_cards if card.card_rank.value == 1])

        # Determine if we can generate a level 2 card by moving two cards, only if we don't have 3 high-rank cards already
        if total_num_silver_cards == 2:
            # Do it only if it's our first card move
            for i, card in enumerate(hand_of_cards):
                for j in range(i + 1, len(hand_of_cards)):
                    if card.card_rank == CardRanks.BRONZE and determine_card_merge(card, hand_of_cards[j]):
                        return [i, j]

        # Play level 2 cards or higher if we can
        if total_num_silver_cards >= 3 and len(silver_ids) > 0:
            print("Picking a silver card!")
            # And we have a shield!
            Floor4BattleStrategy.with_shield = True
            return silver_ids[-1]

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 2. Here we need to distinguish between the two types of turns!"""
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # List of cards of high rank
        silver_ids = np.where(card_ranks == 1)[0].astype(int)

        if not Floor4BattleStrategy.with_shield:
            # If we don't have a shield, try to get it
            next_idx = self._without_shield_phase2(hand_of_cards, picked_cards, silver_ids)
        else:
            # If we have a shield, go HAM
            next_idx = self._with_shield_phase2(hand_of_cards, picked_cards)
        if next_idx is not None:
            # We may not have found any card to play
            return next_idx

        ### If we cannot play HAM cards because we don't have any, just play normally BUT without clicking SILVER cards

        for i in silver_ids:
            card_types[i] = CardTypes.DISABLED.value

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # STANCE CARDS
        stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
        if len(stance_ids) and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size:
            return stance_ids[-1]

        # ULTIMATES
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # Now just click on a bronze card if we have one, and we don't have enough silver cards
        bronze_ids = np.where(card_ranks == CardRanks.BRONZE.value)[0]
        if 7 in bronze_ids:
            return 7
        bronze_ids = bronze_ids[::-1]  # To start searching from the right
        # Get the next bronze card that doesn't correspond to a RECOVERY OR a Meli AOE
        next_idx = next(
            (
                bronze_item
                for bronze_item in bronze_ids
                if not determine_card_merge(hand_of_cards[bronze_item - 1], hand_of_cards[bronze_item + 1])
            ),
            -1,  # Default
        )

        print("Defaulting to:", next_idx)
        return next_idx

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase3. We need to use as many attack cards as possible.
        NOTE: For these phase, we need to distinguis between Thor/amplify cards and the rest. Using simple template matching
        """

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # Keep track of all the indices
        all_indices = np.arange(len(hand_of_cards))

        # AMPLIFY CARDS -- first and foremost
        amplify_ids = np.where([AmplifyCardPredictor.is_amplify_card(card.card_image) for card in hand_of_cards])[0]
        if len(amplify_ids):
            # Pick the rightmost amplify card
            print("Picking amplify card at index", amplify_ids[-1])
            return amplify_ids[-1]

        # STANCE CARDS
        stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
        if len(stance_ids) and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size:
            return stance_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if (
            len(recovery_ids)
            and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
        ):
            return recovery_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=False)
        if len(attack_ids):
            return attack_ids[-1]

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # ATTACK-DEBUFF CARDs
        att_debuff_ids = np.where(card_types == CardTypes.ATTACK_DEBUFF.value)[0]
        # Sort them based on card ranks
        att_debuff_ids: np.ndarray = np.array(sorted(att_debuff_ids, key=lambda idx: card_ranks[idx], reverse=False))

        # CONSIDER THE REMAINING CARDS
        # Append the rest together: Ultimates, 1 recovery, 1 stance, 1 attack-debuff, all attacks, all attack-debuffs, the rest
        selected_ids = np.hstack((stance_ids, recovery_ids, att_debuff_ids))

        # Let's extract the DISABLED and GROUND cards too, to append them at the very end
        disabled_ids = sorted(np.where(card_types == CardTypes.DISABLED.value)[0])
        ground_ids = np.where(card_types == CardTypes.GROUND.value)[0]

        # Find the remaining cards (without considering the disabled/ground cards), and append them at the end
        remaining_indices = np.setdiff1d(all_indices, np.hstack((ground_ids, disabled_ids, selected_ids)))

        # Concatenate the selected IDs, with the remaining IDs, and at the very end, the disabled IDs.
        final_indices = np.hstack((ground_ids, disabled_ids, remaining_indices, selected_ids)).astype(int)

        # Return the next index!
        return final_indices[-1]

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""

        # We may need to ult with Meli here
        screenshot, _ = capture_window()
        if find(vio.evasion, screenshot):
            for i in range(len(hand_of_cards)):
                if find(vio.meli_ult, hand_of_cards[i].card_image):
                    return i

        # Go ham on it
        next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        while find(vio.meli_ult, hand_of_cards[next_idx].card_image):
            # Disable the meli ult for this round
            hand_of_cards[next_idx].card_type = CardTypes.DISABLED
            next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        return next_idx
