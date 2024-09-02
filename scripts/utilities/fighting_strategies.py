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
    count_immortality_buffs,
    determine_card_merge,
    display_image,
    find,
    get_card_interior_image,
    get_hand_cards,
    is_amplify_card,
    is_hard_hitting_card,
    is_Meli_card,
    is_Thor_card,
)


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    card_turn = 0
    cards_to_play = 0

    def pick_cards(self, **kwargs) -> tuple[list[Card], list[int]]:
        """**kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        print("Card types:", [card.card_type.name for card in hand_of_cards])
        print("Card ranks:", [card.card_rank.name for card in hand_of_cards])

        card_indices = []
        picked_cards = []

        # Extract how many cards we have to play
        screenshot, _ = capture_window()
        IBattleStrategy.cards_to_play = count_empty_card_slots(screenshot)

        # TODO: For now we need to hardcode the '4', otherwise code may break on line 82 of general_figher_interface.py...
        for _ in range(4):

            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards, **kwargs)

            # Update the indices and cards lists
            card_indices.append(next_index)
            if isinstance(next_index, Integral):
                print(f"Picked index {next_index} with card {hand_of_cards[next_index].card_type.name}")
                picked_cards.append(hand_of_cards[next_index])
            elif isinstance(next_index, (tuple, list)):
                print(f"Moving cards: {next_index}")

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
        """Always get the rightmost card"""
        return 7


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def get_next_card_index(cls, hand_of_cards: list[Card], picked_cards: list[Card], **kwargs) -> int:
        """Apply the logic to extract the right indices."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # STANCE CARDS
        if (stance_idx := play_stance_card(card_types, picked_card_types)) is not None:
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
    """The logic behind the battle for Floor 4"""

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

        # We may need to cure all the debuffs!
        screenshot, _ = capture_window()
        if find(vio.block_skill_debuf, screenshot):
            # We need to use Meli's AOE and Megelda's recovery!
            print("We have a block-skill debuff, we need to cleanse!")

            # Play Meli's AOE card if we have it
            if not np.any([find(vio.meli_aoe, card.card_image) for card in picked_cards]):
                meli_aoe_ids = np.where([find(vio.meli_aoe, card.card_image) for card in hand_of_cards])[0]
                if len(meli_aoe_ids):
                    print("Playing Meli's AOE")
                    return sorted(meli_aoe_ids, reverse=True, key=lambda idx: card_ranks[idx])[-1]

            # RECOVERY CARDS
            recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
            if len(recovery_ids) and not np.any([picked_card_types == CardTypes.RECOVERY.value]):
                print("Playing recovery at index", recovery_ids[-1])
                # Sort them in descending order of card ranks, and pick a bronze one if possible
                return sorted(recovery_ids, key=lambda idx: card_ranks[idx], reverse=True)[-1]
        else:
            # If we don't cure block-skill debuff, check if we can do a card merge
            silver_cards = np.where(card_ranks == CardRanks.SILVER.value)[0]
            if len(silver_cards) < 3 and IBattleStrategy.card_turn == 0:
                # Only do a manual card merge if it's the first card of the turn
                if (potential_idx := self._make_silver_merge(hand_of_cards)) is not None:
                    return potential_idx

        # STANCE CARDS -- non-silver
        screenshot, _ = capture_window()
        stance_ids = np.where((card_types == CardTypes.STANCE.value) & (card_ranks != CardRanks.SILVER.value))[0]
        if (
            len(stance_ids)
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
            and not find(vio.stance_active, screenshot, threshold=0.5)
        ):
            print("We don't have a stance up, we need to enable it!")
            return stance_ids[-1]

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
        # Get the next non-silver card that doesn't correspond to a RECOVERY OR a Meli AOE OR doesn't generate a merge of silver cards

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
            None,
        )

        if next_idx is None:
            # There's no bronze card to play! Simply move the rightmost two cards
            print("We can't play any bronze card! Defaulting to arbitrary moving cards")
            # Move cards until a merge of silver cards is NOT generated
            origin_idx = -1
            target_idx = -2
            while (
                determine_card_merge(hand_of_cards[target_idx], hand_of_cards[origin_idx])
                and card_ranks[origin_idx] == CardRanks.SILVER.value
            ):
                print(f"Index {origin_idx} will generate an unwanted merge with idx {target_idx}, skipping this move.")
                target_idx -= 1
            return [origin_idx, target_idx]

        # If we've found a non-silver card to play
        return next_idx

    def _with_shield_phase2(self, hand_of_cards: list[Card]):
        """What to do if we have a shield? GO HAM"""
        card_ranks = [card.card_rank.value for card in hand_of_cards]

        print("We have a shield, GOING HAM ON THE BIRD!")
        # First pick ultimates, to save amplify cards for phase 3 if we can
        ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]
        if len(ult_ids):
            return ult_ids[-1]

        # First try to pick a hard-hitting card
        ham_card_ids = np.where([is_hard_hitting_card(card) for card in hand_of_cards])[0]
        # Use bronze cards first
        ham_card_ids = sorted(ham_card_ids, key=lambda idx: card_ranks[idx], reverse=True)
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
            if (potential_idx := self._make_silver_merge(hand_of_cards)) is not None:
                return potential_idx

        # Play level 2 cards or higher only if we can get the shield
        empty_slots = IBattleStrategy.cards_to_play - IBattleStrategy.card_turn
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

        ### DISABLED
        # If we have any disabled card here but also recoveries available...
        if (
            np.any([card_types == CardTypes.DISABLED.value])
            and len(recovery_ids := np.where(card_types == CardTypes.RECOVERY.value)[0]) > 0
        ):
            print("We're fully disabled but re-enabling cards")
            # Change all DISABLED to ATTACK
            for i in range(len(hand_of_cards)):
                if card_types[i] == CardTypes.DISABLED.value:
                    print(f"Re-enabling card at idx {i}!")
                    hand_of_cards[i].card_type = CardTypes.ATTACK
            # Return the recovery
            return recovery_ids[-1]

        ### WITH/WITHOUT SHIELD DEFAULT STRATEGIES
        if Floor4BattleStrategy.with_shield:
            # If we have a shield, go HAM
            next_idx = self._with_shield_phase2(hand_of_cards)

            # Evaluate if we have to remove the shield
            if IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1:
                print("REMOVING SHIELD!")
                Floor4BattleStrategy.with_shield = False
        else:
            # If we don't have a shield, try to get it
            next_idx = self._without_shield_phase2(hand_of_cards, silver_ids, picked_silver_cards)

            # Evaluate here if we need to set the shield
            if isinstance(next_idx, Integral):
                picked_silver_cards.append(next_idx)
            if len(picked_silver_cards) == 3 and IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1:
                print("SETTING SHIELD!")
                Floor4BattleStrategy.with_shield = True

        if next_idx is not None:
            # If we've found a card to play for the specific strategy...
            return next_idx
        else:
            print("Index is 'None', defaulting to default strategy.")

        ### If we cannot play HAM cards because we don't have any, just play normally BUT without clicking SILVER cards

        # CARD MERGE -- If there's a card that generates a merge (and either isn't a SILVER card, or merges two SILVER cards), pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if (
                determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1])
                and card_ranks[i - 1] != CardRanks.SILVER.value
                and card_ranks[i] != CardRanks.SILVER.value
            ):
                print("Manually generating a merge on index", i)
                return i

        # Disable all silver cards
        for i in silver_ids:
            card_types[i] = CardTypes.DISABLED.value

        # ULTIMATES
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # STANCE CARDS
        if (stance_idx := play_stance_card(card_types, picked_card_types)) is not None:
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
        if find(vio.block_skill_debuf, screenshot, threshold=0.6):
            # We need to use Meli's AOE and Megelda's recovery!
            print("We have a block-skill debuff, we need to cleanse!")

            # RECOVERY CARDS
            recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
            if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
                print("Playing recovery at index", recovery_ids[-1])
                return recovery_ids[-1]

            # Play Meli's AOE card if we don't have a cleanse, AND if we haven't played a Meli AOE yet
            elif not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size and not np.any(
                [find(vio.meli_aoe, card.card_image) for card in picked_cards]
            ):
                for i, card in enumerate(hand_of_cards):
                    if find(vio.meli_aoe, card.card_image):
                        print("Playing Meli's AOE at index", i)
                        return i

        # STANCE CARDS -- First, since they get disabled immediately!
        if (stance_idx := play_stance_card(card_types, picked_card_types)) is not None:
            return stance_idx

        # AMPLIFY CARDS -- Use them if the bird still has immortality buffs
        if (amplify_id := self._pick_amplify_cards(screenshot, hand_of_cards, picked_cards)) is not None:
            print("Picking amplify card at ID:", amplify_id)
            return amplify_id

        # CARD MERGE -- If there's a card that generates a merge, pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1]) and not find(
                vio.meli_ult, hand_of_cards[i].card_image
            ):
                print(f"Index {i} generates a merge, picking it")
                return i

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if len(recovery_ids) and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # # Lets sort the attack cards based on their rank
        # attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=True)
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
        while find(vio.meli_ult, hand_of_cards[default_idx].card_image):
            print("We have to skip Meli's ultimate here!")
            default_idx -= 1
        return default_idx

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""

        # Extract card types and picked card types
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # STANCE -- first thing, since it increases damage
        if (stance_idx := play_stance_card(card_types, picked_card_types)) is not None:
            return stance_idx

        # If we don't have Meli's ult ready, play/move a card if we can generate a Meli merge
        if IBattleStrategy.card_turn == 0 and not np.any(
            [find(vio.meli_ult, card.card_image, threshold=0.6) for card in hand_of_cards]
        ):
            print("We don't have Meli's ult, let's force playing a Meli card")
            meli_cards = np.where([is_Meli_card(card) for card in hand_of_cards])[0]
            if len(meli_cards):
                return meli_cards[-1]

        # We may need to ULT WITH MELI here, first thing to do after the stance
        screenshot, _ = capture_window()
        if find(vio.evasion, screenshot):
            for i in range(len(hand_of_cards)):
                if find(vio.meli_ult, hand_of_cards[i].card_image, threshold=0.6):
                    return i

            # Now, if we DON'T HAVE meli's ult, we should NOT play HAM cards
            if not np.any([find(vio.meli_ult, card.card_image) for card in picked_cards]):
                print("We cannot remove evasion, playing non-HAM cards...")
                # RECOVERY: Play as many as we have!
                if len(recovery_ids := np.where(card_types == CardTypes.RECOVERY.value)[0]):
                    return recovery_ids[-1]

                # ULTS
                elif len(ult_ids := np.where(card_types == CardTypes.ULTIMATE.value)[0]):
                    return ult_ids[-1]

                # Regular non-HAM cards:
                elif len(non_ham_ids := np.where([not is_hard_hitting_card(card) for card in hand_of_cards])[0]):
                    return non_ham_ids[-1]

        # RECOVERY
        if len(recovery_ids := np.where(card_types == CardTypes.RECOVERY.value)[0]) and not np.any(
            [card.card_type == CardTypes.RECOVERY for card in picked_cards]
        ):
            return recovery_ids[-1]

        # Go HAM on the fricking bird
        # TODO: Rather than doing this, ensure that one Thor card is picked last... but most of them first too!
        ham_card_ids = np.where([is_hard_hitting_card(card) for card in hand_of_cards])[0]
        if len(ham_card_ids):
            thor_ids = np.where([is_Thor_card(card) for card in hand_of_cards])[0]
            non_thor_ham_ids = np.setdiff1d(ham_card_ids, thor_ids)
            # Re-order the array of HAM IDs, with the thor_ids in the last position
            ham_card_ids = np.concatenate([thor_ids[-1:], non_thor_ham_ids, thor_ids[:-1]])
            return (
                thor_ids[-1]
                if len(thor_ids) and IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1
                else ham_card_ids[-1]
            )

        # If we don't have hard-hitting cards, run the default strategy
        next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        if find(vio.meli_ult, hand_of_cards[next_idx].card_image):
            # Disable the meli ult for this round
            hand_of_cards[next_idx].card_type = CardTypes.DISABLED
            next_idx = SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

        return next_idx

    def _pick_amplify_cards(
        self, screenshot: np.ndarray, hand_of_cards: list[Card], picked_cards: list[Card]
    ) -> int | None:
        """Pick an amplify/Thor/powerstrike card if necessary"""
        num_immortalities = count_immortality_buffs(screenshot)
        picked_amplify_cards = sum(is_amplify_card(card) for card in picked_cards)
        print("These many immortalities:", num_immortalities - picked_amplify_cards)
        if num_immortalities - picked_amplify_cards > 0 and len(
            amplify_ids := np.where([is_amplify_card(card) for card in hand_of_cards])[0]
        ):
            print("Amplify IDs:", np.where([is_amplify_card(card) for card in hand_of_cards])[0])
            # thor_ids = np.where([is_Thor_card(card) for card in hand_of_cards])[0]
            # non_thor_amplify_ids = np.setdiff1d(amplify_ids, thor_ids)
            # # Re-order the array of HAM IDs, with the thor_ids in the last position
            # amplify_ids = np.concatenate([thor_ids, non_thor_amplify_ids])
            # return (
            #     thor_ids[-1]
            #     if len(thor_ids) and IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1
            #     else amplify_ids[-1]
            # )
            return amplify_ids[-1]
        elif num_immortalities - picked_amplify_cards <= 0:
            print("No need to select more amplify cards!")

        return None

    def _make_silver_merge(self, hand_of_cards: list[Card]):
        """See if we can make a silver merge"""
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
        return None


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
