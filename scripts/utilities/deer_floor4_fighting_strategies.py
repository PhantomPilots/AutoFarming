import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.deer_utilities import (
    count_cards,
    is_blue_card,
    is_Freyr_card,
    is_green_card,
    is_Hel_card,
    is_Jorm_card,
    is_red_card,
    is_Thor_card,
    reorder_buff_removal_card,
)
from utilities.fighting_strategies import (
    IBattleStrategy,
    SmarterBattleStrategy,
    play_stance_card,
)
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    count_immortality_buffs,
    determine_card_merge,
    display_image,
    find,
    get_hand_cards,
    is_amplify_card,
    is_ground_card,
)

logger = LoggerWrapper("BirdFloor4FightingStrategies", log_file="deer_floor4_AI.log")


class DeerFloor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for Floor 4"""

    # Keep track of the turn within a phase
    turn = 0

    # To keep track of what phases have been initialized
    _phase_initialized = set()

    # Did we use red or blue cards in phase 1 turn 0?
    _color_cards_used_p2t0 = None

    # Keep track of the last phase we've seen
    _last_phase_seen = None

    # What color cards we're running on phase 3
    _color_cards_picked_p3 = None

    def _initialize_static_variables(self):
        DeerFloor4BattleStrategy.turn = 0
        DeerFloor4BattleStrategy._phase_initialized = set()
        DeerFloor4BattleStrategy._color_cards_used_p2t0 = None
        DeerFloor4BattleStrategy._color_cards_picked_p3 = None

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        # If we're entering phase 1 after being in any other phase, reset
        if phase == 1 and DeerFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        # Update last seen phase
        DeerFloor4BattleStrategy._last_phase_seen = phase

        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(hand_of_cards, picked_cards)
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards)

        return card_index

    def _maybe_reset(self, phase_id: str):
        """Reset the turn counter if we're in a new phase"""
        if phase_id not in DeerFloor4BattleStrategy._phase_initialized:
            print("Resetting turn counter for phase", phase_id)
            DeerFloor4BattleStrategy.turn = 0
            DeerFloor4BattleStrategy._phase_initialized.add(phase_id)

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        # sourcery skip: merge-duplicate-blocks
        """The strategy is the following:

        Turn 1 - Freyr Cleave > Hel Att > Jorm buff removal > Thor Crit chance

        (This where the Strat deviates depending on the rng you get)

        Turn 2 (With an extra thor card) - Move thor card 2 times and use her lvl 2 (she must have 4 ult gauge )hel card once.

        Turn 2 (without a extra thor card) - Attack with thor and move hel card 3 times

        Turn 3 - (With extra thor card) - move thor once and use her card to kill, then move hel or freyr card 2 times (u want hel and freyr to be close to their ults. ideally u want Hel to have 3 ult points)
        """
        self._maybe_reset("phase_1")  # Not needed, but whatever

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        freyr_cards = sorted(
            np.where([is_Freyr_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        if DeerFloor4BattleStrategy.turn == 0:
            return self._phase1_turn0(hand_of_cards)

        elif DeerFloor4BattleStrategy.turn == 1:
            if count_cards(hand_of_cards, is_Thor_card) >= 2:
                # If we have two Thor cards...
                if IBattleStrategy.card_turn <= 1:
                    # Move a Thor card to the left
                    return [thor_cards[0], thor_cards[0] + 1]
                elif IBattleStrategy.card_turn == 2:
                    # Use a Hel card, we're guaranteed to have one
                    return hel_cards[-1]
                else:
                    # Play Thor card
                    DeerFloor4BattleStrategy.turn += 1
                    return thor_cards[-1]
            else:
                # If not...
                if IBattleStrategy.card_turn <= 2:
                    return [hel_cards[0], hel_cards[0] + 1]
                # Play Thor card
                DeerFloor4BattleStrategy.turn += 1
                return thor_cards[-1]

        elif DeerFloor4BattleStrategy.turn == 2:
            if len(thor_cards) > 0:
                if IBattleStrategy.card_turn == 0:
                    # Move Thor card first to remove freeze
                    return [thor_cards[0], thor_cards[0] + 1]
                elif IBattleStrategy.card_turn <= 2:
                    if len(hel_cards):
                        return [hel_cards[0], hel_cards[0] + 1]
                    if len(freyr_cards):
                        return [freyr_cards[0], freyr_cards[0] + 1]
                else:
                    return thor_cards[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _phase1_turn0(self, hand_of_cards):
        """The first turn of the first phase"""
        # First, try to play a Freyr stance card
        freyr_stance = np.where([find(vio.freyr_1, card.card_image) for card in hand_of_cards])[0]
        if len(freyr_stance) > 0:
            return freyr_stance[-1]

        # Then, try to play a Hel card if we haven't played one yet
        hel_cards = np.where([find(vio.hel_1, card.card_image) for card in hand_of_cards])[0]
        if len(hel_cards) > 0:
            return hel_cards[-1]

        # Then, Jorm's buff removal
        jorm_card = np.where([find(vio.jorm_2, card.card_image) for card in hand_of_cards])[0]
        if len(jorm_card) > 0:
            return jorm_card[-1]

        # Finish the turn with a Thor card
        thor_cards = np.where([find(vio.thor_1, card.card_image) for card in hand_of_cards])[0]
        DeerFloor4BattleStrategy.turn += 1
        return thor_cards[-1]

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_2")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        freyr_cards = sorted(
            np.where([is_Freyr_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        if DeerFloor4BattleStrategy.turn == 0:
            if IBattleStrategy.card_turn <= 1:
                num_blue_cards = count_cards(hand_of_cards, is_blue_card) + count_cards(picked_cards, is_blue_card)
                num_red_cards = count_cards(hand_of_cards, is_red_card) + count_cards(picked_cards, is_red_card)
                if num_red_cards >= 2 or num_blue_cards >= 2:
                    cards_to_pick = np.where(
                        [is_red_card(card) if num_red_cards >= 2 else is_blue_card(card) for card in hand_of_cards]
                    )[0]
                    DeerFloor4BattleStrategy._color_cards_used_p2t0 = "red" if num_red_cards >= 2 else "blue"
                    return cards_to_pick[-1]
            elif IBattleStrategy.card_turn >= 2:
                if IBattleStrategy.card_turn == 3:
                    # Go to next turn
                    DeerFloor4BattleStrategy.turn += 1
                if len(hel_cards):
                    return [hel_cards[0], hel_cards[0] + 1]
                return [freyr_cards[0], freyr_cards[0] + 1]

        elif DeerFloor4BattleStrategy.turn == 1:
            if IBattleStrategy.card_turn <= 1:
                # Play a green card, but prioritize the ult if we have it
                hel_ult_id = np.where([find(vio.hel_ult, card.card_image) for card in hand_of_cards])[0]
                return hel_ult_id[0] if len(hel_ult_id) > 0 else green_card_ids[-1]
            else:
                if IBattleStrategy.card_turn == 3:
                    # Go to next turn after this one
                    DeerFloor4BattleStrategy.turn += 1
                if len(freyr_cards) > 0:
                    # Try to get Freyr's ult
                    return [freyr_cards[0], freyr_cards[0] + 1]
                # Else just move an arbitrary card
                return [-2, -1]

        elif DeerFloor4BattleStrategy.turn == 2:
            if DeerFloor4BattleStrategy._color_cards_used_p2t0 == "red":
                # We used red cards, so we need to use blue here (Thor)
                if DeerFloor4BattleStrategy.turn <= 1 and len(thor_cards) > 0:
                    return thor_cards[0]
                elif DeerFloor4BattleStrategy.turn == 2 and len(thor_cards) > 0:
                    return thor_cards[-1]  # Use her ult, we should have it
                elif DeerFloor4BattleStrategy.turn == 3:
                    if len(freyr_cards) > 0:
                        return freyr_cards[-1]  # Use Freyr ult if we have it
                    elif len(thor_cards) > 0:
                        return thor_cards[-1]

            elif DeerFloor4BattleStrategy._color_cards_used_p2t0 == "blue":
                # We used blue cards, so we need to use red here (Freyr)
                if DeerFloor4BattleStrategy.turn <= 1 and len(freyr_cards) > 0:
                    return freyr_cards[-1]  # Use Freyr's ult
                elif DeerFloor4BattleStrategy.turn == 2 and len(thor_cards) > 0:
                    return thor_cards[-1]  # Use Thor's ult, we should have it?

        else:
            # We haven't killed in 3 turns... let's keep abiding by the gimmick
            card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}
            if IBattleStrategy.card_turn == 0:
                # Pick what color to play this round
                card_colors = ["red", "green", "blue"]  # or whatever order you want
                DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))

            picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
            if IBattleStrategy.card_turn < 2 and len(picked_card_ids):
                return picked_card_ids[-1]
            # Move arbitrary cards
            return [-2, -1]

        # To have a default, although this'll never happen
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_3")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        green_card_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        # Reorder green card IDs, so the buff removal is the last one we pick
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)
        # Group them by their name
        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}

        # If we have Hel ult, let's disable it!
        hel_ult_ids = np.where([find(vio.hel_ult, card.card_image) for card in hand_of_cards])[0]
        if len(hel_ult_ids):
            hand_of_cards[hel_ult_ids[0]].card_type = CardTypes.DISABLED

        # On turn 0, use green cards to try to heal with Jorm
        num_green_cards = count_cards(hand_of_cards, is_green_card) + count_cards(picked_cards, is_green_card)
        if DeerFloor4BattleStrategy.turn == 0 and IBattleStrategy.card_turn <= 2 and num_green_cards >= 3:
            DeerFloor4BattleStrategy._color_cards_picked_p3 = "green"
            return green_card_ids[-1]

        # Otherwise, use any card color
        if IBattleStrategy.card_turn == 0:
            # Pick what color to play this round
            card_colors = ["red", "green", "blue"]  # or whatever order you want
            DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))
            print(f"Setting '{DeerFloor4BattleStrategy._color_cards_picked_p3}' as the color type for this round!")

        picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
        if IBattleStrategy.card_turn <= 2 and len(picked_card_ids):
            return picked_card_ids[-1]

        if IBattleStrategy.card_turn > 2:
            # Just move cards to maybe get an ult?
            return [-2, -1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""
        self._maybe_reset("phase_4")

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        # Get all card types
        red_card_ids = sorted(
            np.where([is_red_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        green_card_ids: list[int] = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        # Let's disable Hel's ultimate until we're in round turn  3
        if DeerFloor4BattleStrategy.turn % 3 != 0 or DeerFloor4BattleStrategy.turn == 0:
            # Let's set the ults to be the last cards to use
            blue_card_ids = blue_card_ids[::-1]
            red_card_ids = red_card_ids[::-1]
            green_card_ids = green_card_ids[::-1]

        # Place buff removal card at the beginning of the list, to save it if necessary
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        # --- Regular Deer roulette ---

        # First, increment the round turn
        if IBattleStrategy.card_turn == 3:
            DeerFloor4BattleStrategy.turn += 1

        if IBattleStrategy.card_turn == 0:
            # Select the starting card
            if DeerFloor4BattleStrategy.turn % 3 == 0 and len(green_card_ids) > 1:
                print("1st turn, starting with green card")
                return green_card_ids[-1]
            if DeerFloor4BattleStrategy.turn % 3 == 1 and len(blue_card_ids) > 1:
                print("2nd turn, starting with blue card")
                return blue_card_ids[-1]
            if DeerFloor4BattleStrategy.turn % 3 == 2 and len(red_card_ids) > 1:
                print("3rd turn, starting with red card")
                return red_card_ids[-1]

        # Keep track of last picked card
        last_card = picked_cards[-1] if len(picked_cards) else Card()

        if is_green_card(last_card) and len(blue_card_ids):
            print("Last card green! Picking blue")
            # Gotta pick a blue card
            return blue_card_ids[-1]
        if is_red_card(last_card) and len(green_card_ids):
            print("Last card red! Picking green")
            # First, if it's turn 2, use Jorm's buff card if it exists
            buff_removal_ids = np.where([find(vio.jorm_2, hand_of_cards[idx].card_image) for idx in green_card_ids])[0]
            return (
                buff_removal_ids[-1]
                if len(buff_removal_ids) and DeerFloor4BattleStrategy.turn == 2
                else green_card_ids[-1]
            )
        if is_blue_card(last_card) and len(red_card_ids):
            print("Last card blue! Picking red")
            # Gotta pick a red card
            return red_card_ids[-1]

        # If the above doesn't happen...
        print("Couldn't find the right card, defaulting...")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
