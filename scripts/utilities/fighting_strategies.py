"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import (
    capture_window,
    count_empty_card_slots,
    determine_card_merge,
    display_image,
    find,
    get_card_interior_image,
    get_hand_cards,
    is_amplify_card,
    is_hard_hitting_card,
)


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    card_turn = 0

    def pick_cards(self, **kwargs) -> tuple[list[Card], list[int]]:
        """**kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        print("Card types:", [card.card_type.name for card in hand_of_cards])
        print("Card ranks:", [card.card_rank.name for card in hand_of_cards])

        card_indices = []
        picked_cards = []
        for _ in range(4):  # Pick at most 4 cards

            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards, **kwargs)

            # Update the indices and cards lists
            card_indices.append(next_index)
            if isinstance(next_index, Integral):
                print(f"Picked index {next_index} with card {hand_of_cards[next_index].card_type.name}")
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
    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], **kwargs) -> int:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def get_next_card_index(self, *args, **kwargs) -> int:
        """Always get the rightmost 4 cards"""
        return 7


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def get_next_card_index(cls, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Apply the logic to extract the right indices."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # STANCE CARDS
        stance_idx = play_stance_card(card_types, picked_card_types)
        if stance_idx is not None:
            return stance_idx

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if (
            len(recovery_ids)
            and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
        ):
            return recovery_ids[-1]

        # CARD MERGE -- If there's a card that generates a merge (and not disabled), pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if hand_of_cards[i].card_type != CardTypes.DISABLED and determine_card_merge(
                hand_of_cards[i - 1], hand_of_cards[i + 1]
            ):
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

        print("We don't meet any of the previous criteria, defaulting to the rightmost index")
        return -1


class Floor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for FLoor 4"""

    # Static attribute that keeps track of whether we've enabled a shield on phase 2
    with_shield = False

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
            # We need to use Meli's AOE and Megelda's recovery!
            print("We have a block-skill debuff, we need to cleanse!")

            # Play Meli's AOE card if we have it
            for i, card in enumerate(hand_of_cards):
                if find(vio.meli_aoe, card.card_image):
                    print("Playing Meli's AOE at index", i)
                    return i

            # RECOVERY CARDS
            recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
            if len(recovery_ids):
                print("Playing recovery at index", recovery_ids[-1])
                return recovery_ids[-1]

        # STANCE CARDS
        stance_idx = play_stance_card(card_types, picked_card_types)
        if stance_idx is not None:
            return stance_idx

        # Click on a card if it generates a SILVER merge
        for i in range(1, len(hand_of_cards) - 1):
            if (
                determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1])
                and hand_of_cards[i].card_rank == CardRanks.BRONZE
                and hand_of_cards[i - 1].card_rank == CardRanks.BRONZE
            ):
                return i

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        ### DEFAULT
        # Get the next bronze card that doesn't correspond to a RECOVERY OR a Meli AOE OR doesn't generate a merge of silver cards
        next_idx = next(
            (
                bronze_item
                # Reverse the bronze_ids list o start searching from the right:
                for bronze_item in np.where(card_ranks != CardRanks.SILVER.value)[0][::-1]
                if hand_of_cards[bronze_item].card_type not in [CardTypes.GROUND, CardTypes.RECOVERY]
                and not find(vio.meli_aoe, hand_of_cards[bronze_item].card_image)
                and (
                    (
                        bronze_item > 0
                        and bronze_item < len(hand_of_cards) - 1
                        and (
                            not determine_card_merge(
                                hand_of_cards[bronze_item - 1],
                                hand_of_cards[bronze_item + 1],
                            )
                            or hand_of_cards[bronze_item - 1].card_rank != CardRanks.SILVER
                        )
                    )
                    or bronze_item in [0, len(hand_of_cards) - 1]
                )
            ),
            -1,
        )

        # By default, return the rightmost card
        print(f"Dafulting to: {next_idx}")
        return next_idx

    def _with_shield_phase2(self, hand_of_cards: list[Card]):
        """What to do if we have a shield? GO HAM"""

        print("We have a shield, GOING HAM ON THE BIRD!")
        # First pick ultimates, to save amplify cards for phase 3 if we can
        ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]
        if len(ult_ids):
            return ult_ids[-1]

        # First try to pick a hard-hitting card
        ham_card_ids = np.where([is_hard_hitting_card(card) for card in hand_of_cards])[0]
        return ham_card_ids[-1] if len(ham_card_ids) else None

    def _without_shield_phase2(
        self,
        hand_of_cards: list[Card],
        silver_ids: np.ndarray,
        picked_silver_cards: np.ndarray,
    ):
        """If we don't have a shield, let's get ready for it"""

        # Determine if we can generate a level 2 card by moving two cards, only if we don't have 3 high-rank cards already
        total_num_silver_cards = len(silver_ids) + len(picked_silver_cards)
        if total_num_silver_cards <= 2:
            # If we don't have a shield, move cards to try to make 3 silver cards
            for i, card in enumerate(hand_of_cards):
                for j in range(i + 2, len(hand_of_cards)):
                    if (
                        card.card_rank == CardRanks.BRONZE
                        and determine_card_merge(card, hand_of_cards[j])
                        and (
                            # If `card` at `i` would merge with `i+2`, only move the card if `i+1` is SILVER,
                            # because we wouldn't automatically play it
                            j != i + 2
                            or hand_of_cards[i + 1].card_rank == CardRanks.SILVER
                        )
                    ):
                        return [i, j]

        # Play level 2 cards or higher only if we can get the shield
        empty_slots = count_empty_card_slots(capture_window()[0])
        # We need to recompute the "total number of silver cards", since we may have moved cards and those take up slot space
        total_num_silver_cards = min(len(silver_ids), empty_slots) + len(picked_silver_cards)
        if total_num_silver_cards >= 3 and len(silver_ids) > 0 and len(picked_silver_cards) < 3:
            print("Picking a silver card...")
            return silver_ids[-1]

        return None

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 2. Here we need to distinguish between the two types of turns!"""
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # List of cards of high rank
        silver_ids = np.where(card_ranks == 1)[0].astype(int)
        picked_silver_cards = [card for card in picked_cards if card.card_rank.value == 1]

        if not Floor4BattleStrategy.with_shield:
            # If we don't have a shield, try to get it
            next_idx = self._without_shield_phase2(hand_of_cards, silver_ids, picked_silver_cards)

            # Evaluate here if we need to set the shield
            if isinstance(next_idx, Integral):
                picked_silver_cards.append(next_idx)
            if len(picked_silver_cards) == 3 and Floor4BattleStrategy.card_turn == 3:
                print("SETTING SHIELD!")
                Floor4BattleStrategy.with_shield = True
        else:
            # If we have a shield, go HAM
            next_idx = self._with_shield_phase2(hand_of_cards)

            # Evaluate if we have to remove the shield
            if Floor4BattleStrategy.card_turn == 3:
                print("REMOVING SHIELD!")
                Floor4BattleStrategy.with_shield = False

        if next_idx is not None:
            # We may not have found any card to play
            return next_idx

        ### If we cannot play HAM cards because we don't have any, just play normally BUT without clicking SILVER cards

        # CARD MERGE -- If there's a card that generates a merge (and either isn't a SILVER card, or merges two SILVER cards), pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if (
                determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1])
                and card_ranks[i - 1] != CardRanks.SILVER.value
                and card_ranks[i] != CardRanks.SILVER.value
            ):
                return i

        # Disable all silver cards
        for i in silver_ids:
            card_types[i] = CardTypes.DISABLED.value

        # ULTIMATES
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # STANCE CARDS
        stance_idx = play_stance_card(card_types, picked_card_types)
        if stance_idx is not None:
            return stance_idx

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # Now just click on a bronze card if we have one
        bronze_ids = np.where(card_ranks == CardRanks.BRONZE.value)[0]
        if 7 in bronze_ids:
            return 7
        # Get the next bronze card that doesn't correspond to a RECOVERY OR a Meli AOE
        next_idx = next(
            (
                bronze_item
                # Reverse to start searching from the right
                for bronze_item in bronze_ids[::-1]
                if not (
                    determine_card_merge(hand_of_cards[bronze_item - 1], hand_of_cards[bronze_item + 1])
                    and card_ranks[bronze_item - 1] == CardRanks.SILVER.value
                )
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

        # First of all, we may need to cure the block skill effect!
        screenshot, _ = capture_window()
        if find(vio.block_skill_debuf, screenshot):
            # We need to use Meli's AOE and Megelda's recovery!
            print("We have a block-skill debuff, we need to cleanse!")
            # Play Meli's AOE card if we have it
            for i, card in enumerate(hand_of_cards):
                if find(vio.meli_aoe, card.card_image):
                    print("Playing Meli's AOE at index", i)
                    return i

        # AMPLIFY CARDS -- Go ham on them
        amplify_ids = np.where([is_amplify_card(card) for card in hand_of_cards])[0]
        if len(amplify_ids):
            # Pick the rightmost amplify card
            print("Picking amplify card at index", amplify_ids[-1])
            return amplify_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # STANCE CARDS
        stance_idx = play_stance_card(card_types, picked_card_types)
        if stance_idx is not None:
            return stance_idx

        # CARD MERGE -- If there's a card that generates a merge, pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1]):
                return i

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=False)
        if len(attack_ids):
            return attack_ids[-1]

        # ULTIMATE CARDS, but DON'T use Meli's ultimate!
        ult_ids = np.where(
            (card_types == CardTypes.ULTIMATE.value)
            & np.array([not find(vio.meli_ult, card.card_image) for card in hand_of_cards])
        )[0]
        if len(ult_ids):
            return ult_ids[-1]

        # Default to the rightmost index, as long as it's not a Meli ult!
        default_idx = -1
        while find(vio.meli_ult, screenshot):
            print("We have to skip Meli's ultimate here!")
            default_idx -= 1
        return default_idx

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""

        # Extract card types and picked card types
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # STANCE CARDS -- Play it first since it may increase the output damage
        # If instead we have a recovery card, use it
        stance_idx = play_stance_card(card_types, picked_card_types)
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if stance_idx is not None:
            return stance_idx
        elif len(recovery_ids):
            return recovery_ids[-1]

        # We may need to ULT WITH MELI here, first thing to do after the stance
        screenshot, _ = capture_window()
        if find(vio.evasion, screenshot):
            for i in range(len(hand_of_cards)):
                if find(vio.meli_ult, hand_of_cards[i].card_image):
                    return i

        # Go HAM on the fricking bird
        ham_card_ids = np.where([is_hard_hitting_card(card) for card in hand_of_cards])[0]
        if len(ham_card_ids):
            return ham_card_ids[-1]

        # If we don't have hard-hitting cards, run the default strategy
        next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        if find(vio.meli_ult, hand_of_cards[next_idx].card_image):
            # Disable the meli ult for this round
            hand_of_cards[next_idx].card_type = CardTypes.DISABLED
            next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        return next_idx


def play_stance_card(card_types: np.ndarray, picked_card_types: np.ndarray):
    """Play a stance card if we have it and haven't played it yet"""
    screenshot, _ = capture_window()
    stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
    if (
        len(stance_ids)
        and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
        and not find(vio.stance_active, screenshot, threshold=0.5)
    ):
        print("We don't have a stance up, we need to enable it!")
        return stance_ids[-1]

    # If we don't find any stance
    return None
