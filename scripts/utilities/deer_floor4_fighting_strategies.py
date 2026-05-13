import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
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
    is_Tyr_card,
    reorder_buff_removal_card,
    reorder_jorms_heal,
)
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, find

logger = LoggerWrapper("DeerFloor4FightingStrategies", log_file="deer_floor4_AI.log")


class DeerFloor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for Floor 4"""

    # Did we use red or blue cards in phase 1 turn 1?
    _color_cards_used_p2t1 = None

    # Keep track of the last phase we've seen
    _last_phase_seen = None

    # What color cards we're running on phase 3
    _color_cards_picked_p3 = None

    # Whale phase-2: prospective double-red sequence (one-shot via flag)
    _phase2_double_red_used = False

    def _initialize_static_variables(self):
        DeerFloor4BattleStrategy._color_cards_used_p2t1 = None
        DeerFloor4BattleStrategy._color_cards_picked_p3 = None
        DeerFloor4BattleStrategy._phase2_double_red_used = False

    @staticmethod
    def _pick_or_fallback(
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        indices: list[int],
        *,
        prefer: str = "last",
        warn_reason: str | None = None,
    ) -> int:
        """Return an index from ``indices`` or delegate to SmarterBattleStrategy if empty."""
        if not indices:
            if warn_reason:
                print(f"[WARN] {warn_reason}; falling back to SmarterBattleStrategy.")
            return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
        return indices[-1] if prefer == "last" else indices[0]

    @staticmethod
    def _phase_turn_index(phase_id: str) -> int:
        """1-based started-turn index within this phase."""
        return IBattleStrategy.phase_turn

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        # If we're entering phase 1 after being in any other phase, reset
        if phase == 1 and DeerFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        # Update last seen phase
        DeerFloor4BattleStrategy._last_phase_seen = phase

        if phase == 1:
            card_index = self.get_next_card_index_phase1(
                hand_of_cards, picked_cards, card_turn=card_turn, whale=bool(kwargs.get("whale", False))
            )
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(
                hand_of_cards, picked_cards, card_turn=card_turn, whale=bool(kwargs.get("whale", False))
            )
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards, card_turn=card_turn)

        return card_index

    def _phase1_round0_standard(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
        thor_cards: list[int],
        tyr_hel_cards: list[int],
        jorm_cards: list[int],
        freyr_cards: list[int],
        red_card_ids: list[int],
    ) -> int:
        """Legacy phase-1 opener (default): Tyr/Hel low, Jorm buff removal, Thor crit, Tyr/Hel high."""
        if card_turn == 0:
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                tyr_hel_cards,
                prefer="first",
                warn_reason="No Tyr/Hel cards detected in hand (resize window or check vision)",
            )
        if card_turn == 1:
            if jorm_cards:
                return jorm_cards[-1]
            if freyr_cards:
                return freyr_cards[-1]
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                red_card_ids,
                prefer="last",
                warn_reason="No Jorm/Freyr/red card for phase 1 slot 1 (standard)",
            )
        if card_turn == 2:
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                thor_cards,
                prefer="first",
                warn_reason="No Thor card for phase 1 slot 2",
            )
        return self._pick_or_fallback(
            hand_of_cards,
            picked_cards,
            tyr_hel_cards,
            prefer="last",
            warn_reason="No Tyr/Hel for phase 1 slot 3 (standard)",
        )

    def _phase1_round0_whale(
        self,
        hand_of_cards: list[Card],
        picked_cards: list[Card],
        card_turn: int,
        thor_cards: list[int],
        tyr_hel_cards: list[int],
        jorm_cards: list[int],
        freyr_cards: list[int],
        red_card_ids: list[int],
    ) -> int:
        """Aggressive opener (whale / high gear): Tyr/Hel high, Freyr, Thor low, Thor high."""
        if card_turn == 0:
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                tyr_hel_cards,
                prefer="last",
                warn_reason="No Tyr/Hel cards detected in hand (resize window or check vision)",
            )
        if card_turn == 1:
            if freyr_cards:
                return freyr_cards[-1]
            if jorm_cards:
                return jorm_cards[-1]
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                red_card_ids,
                prefer="last",
                warn_reason="No Freyr/Jorm/red card for phase 1 slot 1 (whale)",
            )
        if card_turn == 2:
            return self._pick_or_fallback(
                hand_of_cards,
                picked_cards,
                thor_cards,
                prefer="first",
                warn_reason="No Thor card for phase 1 slot 2",
            )
        if thor_cards:
            return thor_cards[-1]
        return self._pick_or_fallback(
            hand_of_cards,
            picked_cards,
            tyr_hel_cards,
            prefer="last",
            warn_reason="No Thor for phase 1 slot 3; trying Tyr/Hel (whale)",
        )

    def get_next_card_index_phase1(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, *, whale: bool = False
    ) -> int:
        # sourcery skip: merge-duplicate-blocks
        """Phase 1 strategy.

        First player round: the game gives 2 cards per unit (8 cards); vision can still fail to classify them.

        Round 0 (first four picks): controlled by ``whale``. This is **not** the separate Deer Whale *team*
        used by ``DeerFarmer --whale``; it only toggles the floor-4 phase-1 opener.

        - **Standard** (``whale=False``): lowest Tyr/Hel, Jorm (else Freyr/red), lowest Thor, highest Tyr/Hel.
        - **Whale** (``whale=True``): highest Tyr/Hel, Freyr (else Jorm/red), lowest Thor, highest Thor (else Tyr/Hel).

        Later phase-1 rounds: same for both; Thor moves / plays and Tyr/Hel/Jorm moves as before.
        """

        if card_turn == 0:
            print(f"TURN {self._phase_turn_index('phase_1')}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        thor_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Thor_card(card)], key=lambda idx: card_ranks[idx]
        )
        tyr_hel_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Tyr_card(card) or is_Hel_card(card)],
            key=lambda idx: card_ranks[idx],
        )
        jorm_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Jorm_card(card)], key=lambda idx: card_ranks[idx]
        )
        freyr_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Freyr_card(card)], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_red_card(card)], key=lambda idx: card_ranks[idx]
        )

        if self._phase_turn_index("phase_1") == 1:
            if whale:
                return self._phase1_round0_whale(
                    hand_of_cards,
                    picked_cards,
                    card_turn,
                    thor_cards,
                    tyr_hel_cards,
                    jorm_cards,
                    freyr_cards,
                    red_card_ids,
                )
            return self._phase1_round0_standard(
                hand_of_cards,
                picked_cards,
                card_turn,
                thor_cards,
                tyr_hel_cards,
                jorm_cards,
                freyr_cards,
                red_card_ids,
            )

        elif self._phase_turn_index("phase_1") == 2 and len(thor_cards):
            if card_turn <= 2:
                return [thor_cards[0], thor_cards[0] + 1]
            return thor_cards[-1]

        elif self._phase_turn_index("phase_1") == 3:
            cards_to_move = tyr_hel_cards if len(tyr_hel_cards) else jorm_cards
            if not cards_to_move:
                print("[WARN] No Tyr/Hel/Jorm card to move in phase 1 turn 3.")
                return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
            if card_turn < 2:
                return [cards_to_move[0], cards_to_move[0] + 1]
            if card_turn == 2:
                if len(thor_cards) > 1:
                    return thor_cards[0]
                return [cards_to_move[0], cards_to_move[0] + 1]
            if len(thor_cards):
                return thor_cards[0]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, *, whale: bool = False
    ) -> int:
        # sourcery skip: extract-method
        """Extract the indices based on the list of cards and the current phase"""

        if card_turn == 0:
            print(f"TURN {self._phase_turn_index('phase_2')}:")

        # Set ultimates as last to use
        card_ranks = [
            card.card_rank.value if card.card_type != CardTypes.ULTIMATE else -card.card_rank.value
            for card in hand_of_cards
        ]

        # All unit cards sorted (Tyr/Hel separate — they never share a team)
        tyr_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Tyr_card(card)], key=lambda idx: card_ranks[idx]
        )
        hel_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Hel_card(card)], key=lambda idx: card_ranks[idx]
        )
        jorm_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Jorm_card(card)], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_green_card(card)], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_red_card(card)], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_blue_card(card)], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = reorder_jorms_heal(hand_of_cards, green_card_ids)

        num_red_cards = count_cards(hand_of_cards + picked_cards, is_red_card)
        t = self._phase_turn_index("phase_2")
        double_red = (
            num_red_cards > 1
            and len(red_card_ids)
            and (
                (not whale and t == 1)
                or (whale and not DeerFloor4BattleStrategy._phase2_double_red_used and t in (1, 2, 3))
            )
        )
        if double_red:
            if card_turn == 0:
                return red_card_ids[0]
            if card_turn <= 2:
                return [red_card_ids[0], red_card_ids[0] + 1]
            if whale:
                DeerFloor4BattleStrategy._phase2_double_red_used = True
            return red_card_ids[0]

        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}
        if card_turn == 0 or DeerFloor4BattleStrategy._color_cards_picked_p3 is None:
            # Pick what color to play this round
            card_colors = ["green", "blue"]  # Priority order
            # Roll the colors to change the priority
            n = self._phase_turn_index("phase_2") - 2
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
        if card_turn <= 2 and len(picked_card_ids):
            if card_turn == 2 and DeerFloor4BattleStrategy._color_cards_picked_p3 == "green":
                # Check if we have a heal
                heal_ids = sorted(
                    [i for i, card in enumerate(hand_of_cards) if find(vio.jorm_1, card.card_image)],
                    key=lambda idx: card_ranks[idx],
                )
                if len(heal_ids):
                    print("Picking HEAL card!")
                    return heal_ids[-1]

            return picked_card_ids[-1]

        # Move a card of someone that doesn't have an ult
        return self._move_card_for_ult(
            hand_of_cards + picked_cards,
            tyr_card_ids=tyr_card_ids,
            hel_card_ids=hel_card_ids,
            freyr_cards=red_card_ids,
            jorm_cards=jorm_cards,
            thor_cards=blue_card_ids,
        )

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        if card_turn == 0:
            print(f"TURN {self._phase_turn_index('phase_3')}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        green_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_green_card(card)], key=lambda idx: card_ranks[idx]
        )
        red_card_ids = sorted(  # Disable Freyr's ult, to have it for phase 4!
            [
                i
                for i, card in enumerate(hand_of_cards)
                if is_red_card(card) and not find(vio.freyr_ult, card.card_image)
            ],
            key=lambda idx: card_ranks[idx],
        )
        blue_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_blue_card(card)], key=lambda idx: card_ranks[idx]
        )
        # Reorder green card IDs, so the buff removal is the last one we pick
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        # Group them by their name
        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}

        # Phase-3 turn 1: enough greens (hand + picked) → prefer green; len() not `if green_card_ids` (ndarray-safe).
        num_green_cards = count_cards(hand_of_cards + picked_cards, is_green_card)
        if self._phase_turn_index("phase_3") == 1 and card_turn <= 2 and num_green_cards >= 3 and len(green_card_ids):
            DeerFloor4BattleStrategy._color_cards_picked_p3 = "green"
            return green_card_ids[-1]

        # Otherwise, use any card color
        if card_turn == 0:
            # Pick what color to play this round
            card_colors = ["red", "green", "blue"]  # or whatever order you want
            DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))
            print(f"Setting '{DeerFloor4BattleStrategy._color_cards_picked_p3}' as the color type for this round!")

        picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
        if card_turn <= 2 and len(picked_card_ids):
            return picked_card_ids[-1]

        if card_turn > 2:
            picked_color_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
            if not len(picked_color_ids):
                return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
            idx = -1
            if find(vio.freyr_ult, hand_of_cards[picked_color_ids[idx]].card_image):
                print(f"We found Freyr's ult on the picked id {picked_color_ids[idx]}! Saving it for phase 4")
                idx -= 1
            if idx < -len(picked_color_ids):
                return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
            return picked_color_ids[idx]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        """Extract the indices based on the list of cards and the current phase"""

        if card_turn == 0:
            print(f"TURN {self._phase_turn_index('phase_4')}:")

        screenshot, _ = capture_window()

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        # Get all card types
        red_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_red_card(card)], key=lambda idx: card_ranks[idx]
        )
        blue_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_blue_card(card)], key=lambda idx: card_ranks[idx]
        )
        green_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_green_card(card)], key=lambda idx: card_ranks[idx]
        )
        tyr_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Tyr_card(card)], key=lambda idx: card_ranks[idx]
        )
        hel_card_ids = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Hel_card(card)], key=lambda idx: card_ranks[idx]
        )
        jorm_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Jorm_card(card)], key=lambda idx: card_ranks[idx]
        )

        # First of all, if Deer has a counter, use Hel ult if we have it
        if find(vio.snake_f3p2_counter, screenshot):
            if len(hel_ult_ids := [i for i, card in enumerate(hand_of_cards) if find(vio.hel_ult, card.card_image)]):
                return hel_ult_ids[-1]

        if self._phase_turn_index("phase_4") <= 3:
            # Let's set the ults to be the last cards to use
            print("DISABLING ULTS!")
            blue_card_ids = blue_card_ids[::-1]
            green_card_ids = green_card_ids[::-1]
            if self._phase_turn_index("phase_4") <= 2:
                # Only disable red up to turn 2
                red_card_ids = red_card_ids[::-1]

            first_picked = picked_cards[0] if picked_cards else Card()
            if card_turn == 3 and not find(vio.hel_ult, first_picked.card_image):
                # Move a card of someone that doesn't have an ult AND if we haven't played a Hel's ult at the beginning
                return self._move_card_for_ult(
                    hand_of_cards + picked_cards,
                    tyr_card_ids=tyr_card_ids,
                    hel_card_ids=hel_card_ids,
                    freyr_cards=red_card_ids,
                    jorm_cards=jorm_cards,
                    thor_cards=blue_card_ids,
                )

        # Place buff removal card at the beginning of the list, to save it if necessary
        green_card_ids = reorder_buff_removal_card(hand_of_cards, green_card_ids)

        # --- Regular Deer roulette ---

        if card_turn == 0 and self._phase_turn_index("phase_4") == 1:
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
        elif card_turn == 0:
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

        # Get the last picked card (from previous turn)
        last_card = picked_cards[card_turn - 1] if card_turn > 0 else Card()

        # Special case: If we played Hel's ult as the previous card but no green buff appeared,
        # reset the last_card to restart the color wheel
        if card_turn == 1 and find(vio.hel_ult, last_card.card_image) and not find(vio.green_buff, screenshot):
            print("Last card is Hel's ult, but no green buff! Re-starting the wheel.")
            last_card = Card()

        if is_green_card(last_card) and len(blue_card_ids):
            print("Last card green! Picking blue")
            # Gotta pick a blue card
            return blue_card_ids[-1]
        if is_red_card(last_card) and len(green_card_ids):
            print("Last card red! Picking green")
            # First, if it's turn 3, use Jorm's buff card if it exists
            if self._phase_turn_index("phase_4") == 3:
                print("Can we use a buff removal??")
            buff_removal_ids = [i for i, card in enumerate(hand_of_cards) if is_buff_removal_card(card)]
            return (
                buff_removal_ids[-1]
                if len(buff_removal_ids) and self._phase_turn_index("phase_4") == 3
                else green_card_ids[-1]
            )
        if is_blue_card(last_card) and len(red_card_ids):
            print("Last card blue! Picking red")
            # Gotta pick a red card
            return red_card_ids[-1]

        # If the above doesn't happen...
        print("Couldn't find the right card, defaulting while avoiding ultimates...")
        # But let's disable the ults, just in case
        ult_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type.value == CardTypes.ULTIMATE.value]
        for id in ult_ids:
            hand_of_cards[id].card_type = CardTypes.DISABLED
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def _move_card_for_ult(
        self,
        list_of_cards: list[Card],
        tyr_card_ids: list[int],
        hel_card_ids: list[int],
        freyr_cards: list[int],
        jorm_cards: list[int],
        thor_cards: list[int],
    ):
        """Move a card of someone that doesn't have an ult"""
        unit_to_cards = {
            "tyr": tyr_card_ids,
            "hel": hel_card_ids,
            "freyr": freyr_cards,
            "jorm": jorm_cards,
            "thor": thor_cards,
        }
        # Tyr/Hel never share a team; only one carry step (prefer Tyr if both lists non-empty, e.g. vision glitch).
        carry_first = ["tyr"] if len(tyr_card_ids) else ["hel"] if len(hel_card_ids) else []
        for unit in (*carry_first, "freyr", "jorm", "thor"):
            cards = unit_to_cards[unit]
            if not has_ult(unit, list_of_cards) and len(cards):
                print(f"Unit {unit} doesn't have an ult yet!")
                return [cards[0], cards[0] + 1]

        return [-2, -1]
