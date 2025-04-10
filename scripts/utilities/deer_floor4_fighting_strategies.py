import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.deer_utilities import (
    count_cards,
    has_ult,
    is_blue_card,
    is_buff_removal_card,
    is_Freyr_card,
    is_green_card,
    is_Hel_card,
    is_Jorm_card,
    is_red_card,
    is_Thor_card,
    reorder_buff_removal_card,
    reorder_jorms_heal,
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
    screenshot_testing,
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

        if IBattleStrategy.card_turn == 3:
            # Increment the next round!
            DeerFloor4BattleStrategy.turn += 1

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

        if IBattleStrategy.card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        thor_cards = sorted(
            np.where([is_Thor_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        jorm_cards = sorted(
            np.where([is_Jorm_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        if DeerFloor4BattleStrategy.turn == 0:
            if IBattleStrategy.card_turn == 0:
                return hel_cards[-1]  # Hel debuf
            elif IBattleStrategy.card_turn == 1:
                return jorm_cards[0]  # Jorm heal
            elif IBattleStrategy.card_turn == 2:
                return thor_cards[0]  # Thor crit chance

            return hel_cards[-1]  # Hel attack

        elif DeerFloor4BattleStrategy.turn == 1:
            if IBattleStrategy.card_turn <= 2:
                return [thor_cards[0], thor_cards[0] + 1]

            return thor_cards[-1]

        elif DeerFloor4BattleStrategy.turn == 2:
            cards_to_move = hel_cards if len(hel_cards) else jorm_cards
            if IBattleStrategy.card_turn <= 2:
                return [cards_to_move[0], cards_to_move[0] + 1]

            return thor_cards[0]  # Better to NOT play the ult, in case we can do the double hit

        print("[WARN] We couldn't finish in 3 turns...")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        # sourcery skip: extract-method
        """Extract the indices based on the list of cards and the current phase"""

        self._maybe_reset("phase_2")

        if IBattleStrategy.card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        # All unit cards sorted
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        jorm_cards = sorted(
            np.where([is_Jorm_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
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
        # Reorder heal cards
        green_card_ids = reorder_jorms_heal(hand_of_cards, green_card_ids)

        # Turn 1, use 2 Freyr cards
        num_red_cards = count_cards(hand_of_cards + picked_cards, is_red_card)
        if DeerFloor4BattleStrategy.turn == 0 and num_red_cards > 1:
            if IBattleStrategy.card_turn == 0:
                # First play one card to avoid accidentally merging
                return red_card_ids[0]

            if IBattleStrategy.card_turn <= 2:
                # Move Freyr cards
                return [red_card_ids[0], red_card_ids[0] + 1]

            return red_card_ids[0]

        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}
        if IBattleStrategy.card_turn == 0:
            # Pick what color to play this round
            card_colors = ["green", "blue"]  # Priority order
            # Roll the colors to change the priority
            n = DeerFloor4BattleStrategy.turn - 1
            rolled_colors = card_colors[-n % len(card_colors) :] + card_colors[: -n % len(card_colors)]
            # Set 'red' as the last color, since it's not guaranteed we can use it
            rolled_colors.append("red")
            print("Current priority order:", rolled_colors)
            for color in rolled_colors:
                if len(card_groups[color]) >= 3:
                    DeerFloor4BattleStrategy._color_cards_picked_p3 = color
                    break
            else:
                # Fallback if none have 3 or more cards — Get the group with the max number of cards
                DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))

        print(f"Setting '{DeerFloor4BattleStrategy._color_cards_picked_p3}' as the color type for this round!")
        picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
        if IBattleStrategy.card_turn <= 2 and len(picked_card_ids):
            if IBattleStrategy.card_turn == 2 and DeerFloor4BattleStrategy._color_cards_picked_p3 == "green":
                # Check if we have a heal
                heal_ids = sorted(
                    np.where([find(vio.jorm_1, card.card_image) for card in hand_of_cards])[0],
                    key=lambda idx: card_ranks[idx],
                )
                if len(heal_ids):
                    print("Picking HEAL card!")
                    return heal_ids[-1]

            return picked_card_ids[-1]

        # Move a card of someone that doesn't have an ult
        return self._move_card_for_ult(
            hand_of_cards + picked_cards,
            hel_cards=hel_cards,
            freyr_cards=red_card_ids,
            jorm_cards=jorm_cards,
            thor_cards=blue_card_ids,
        )

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        self._maybe_reset("phase_3")

        if IBattleStrategy.card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        green_card_ids = sorted(
            np.where([is_green_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(  # Disable Freyr's ult, to have it for phase 4!
            np.where([is_red_card(card) and not find(vio.freyr_ult, card.card_image) for card in hand_of_cards])[0],
            key=lambda idx: card_ranks[idx],
        )
        blue_card_ids = sorted(
            np.where([is_blue_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )
        # Reorder green card IDs, so the buff removal is the last one we pick
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        # Group them by their name
        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}

        # On turn 0, use green cards to try to heal with Jorm
        num_green_cards = count_cards(hand_of_cards + picked_cards, is_green_card)
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
            # Let's pick a card from the color that has the most
            picked_color_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
            idx = -1
            if not len(picked_color_ids):
                return idx
            if find(vio.freyr_ult, hand_of_cards[picked_color_ids[idx]].card_image):
                print(f"We found Freyr's ult on the picked id {picked_color_ids[idx]}! Saving it for phase 4")
                idx -= 1
            return picked_color_ids[idx]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        self._maybe_reset("phase_4")

        if IBattleStrategy.card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        screenshot, _ = capture_window()

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
        hel_cards = sorted(np.where([is_Hel_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx])
        jorm_cards = sorted(
            np.where([is_Jorm_card(card) for card in hand_of_cards])[0], key=lambda idx: card_ranks[idx]
        )

        # Let's disable Hel's ultimate until we're in round turn  3
        if DeerFloor4BattleStrategy.turn % 3 != 0 or DeerFloor4BattleStrategy.turn == 0:
            # Let's set the ults to be the last cards to use
            print("DISABLING ULTS!")
            blue_card_ids = blue_card_ids[::-1]
            green_card_ids = green_card_ids[::-1]
            if DeerFloor4BattleStrategy.turn < 2:
                # Only disable red up to turn 2
                red_card_ids = red_card_ids[::-1]

        # Place buff removal card at the beginning of the list, to save it if necessary
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        if DeerFloor4BattleStrategy.turn < 3 and IBattleStrategy.card_turn == 3:
            # Move a card of someone that doesn't have an ult
            return self._move_card_for_ult(
                hand_of_cards + picked_cards,
                hel_cards=hel_cards,
                freyr_cards=red_card_ids,
                jorm_cards=jorm_cards,
                thor_cards=blue_card_ids,
            )

        # --- Regular Deer roulette ---

        if IBattleStrategy.card_turn == 0 and DeerFloor4BattleStrategy.turn == 0:
            # Select the starting card
            if len(red_card_ids):
                print("Initializing with red card!")
                return red_card_ids[-1]
            if len(green_card_ids):
                print("Initializing with green card!")
                return green_card_ids[-1]
            if len(blue_card_ids):
                print("Initializing with blue card!")
                return blue_card_ids[-1]
        elif IBattleStrategy.card_turn == 0:
            if find(vio.blue_buff, screenshot) and len(blue_card_ids):
                # Pick blue card
                print("We're starting the round with a BLUE card!")
                return blue_card_ids[-1]
            if find(vio.red_buff, screenshot) and len(red_card_ids):
                # Pick red card
                print("We're starting the round with a RED card!")
                return red_card_ids[-1]
            if find(vio.green_buff, screenshot) and len(green_card_ids):
                print("We're starting the round with a GREEN card!")
                return green_card_ids[-1]

        # Keep track of last picked card
        last_card = picked_cards[-1] if len(picked_cards) else Card()

        if is_green_card(last_card) and len(blue_card_ids):
            print("Last card green! Picking blue")
            # Gotta pick a blue card
            return blue_card_ids[-1]
        if is_red_card(last_card) and len(green_card_ids):
            print("Last card red! Picking green")
            # First, if it's turn 2, use Jorm's buff card if it exists
            if DeerFloor4BattleStrategy.turn == 2:
                print("Can we use a Jorm buff removal??")
            buff_removal_ids = np.where([is_buff_removal_card(card) for card in hand_of_cards])[0]
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
        print("Couldn't find the right card, defaulting while avoiding ultimates...")
        # But let's disable the ults, just in case
        ult_ids: list[int] = np.where([card.card_type.value == CardTypes.ULTIMATE.value for card in hand_of_cards])[0]
        for id in ult_ids:
            hand_of_cards[id].card_type = CardTypes.DISABLED
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _move_card_for_ult(
        self,
        list_of_cards: list[Card],
        hel_cards: list[Card],
        freyr_cards: list[Card],
        jorm_cards: list[Card],
        thor_cards: list[Card],
    ):
        """Move a card of someone that doesn't have an ult"""
        unit_to_cards = {
            "hel": hel_cards,
            "freyr": freyr_cards,
            "jorm": jorm_cards,
            "thor": thor_cards,
        }
        for unit in ["hel", "freyr", "jorm", "thor"]:
            if not has_ult(unit, list_of_cards):
                print(f"Unit {unit} doesn't have an ult yet!")
                cards = unit_to_cards[unit]
                if len(cards):
                    return [cards[0], cards[0] + 1]

        return [-2, -1]
