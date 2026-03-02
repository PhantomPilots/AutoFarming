import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardColors, CardRanks, CardTypes
from utilities.card_color_mapper import CardColorMapper
from utilities.deer_utilities import (
    has_ult,
    is_buff_removal_card,
    is_Hel_card,
    is_Jorm_card,
    is_Thor_card,
    is_Tyr_card,
    reorder_debuff_cards_to_front,
    reorder_jorms_heal,
)
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, find

logger = LoggerWrapper("BirdFloor4FightingStrategies", log_file="deer_floor4_AI.log")

ADVANCING_TYPES = {CardTypes.ATTACK, CardTypes.ATTACK_DEBUFF, CardTypes.ULTIMATE}

_COLOR_WHEEL = {
    CardColors.GREEN: CardColors.BLUE,
    CardColors.BLUE: CardColors.RED,
    CardColors.RED: CardColors.GREEN,
}


class DeerFloor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for Floor 4"""

    turn = 0
    _phase_initialized = set()
    _color_cards_used_p2t0 = None
    _last_phase_seen = None
    _color_cards_picked_p3 = None

    def _initialize_static_variables(self):
        DeerFloor4BattleStrategy.turn = 0
        DeerFloor4BattleStrategy._phase_initialized = set()
        DeerFloor4BattleStrategy._color_cards_used_p2t0 = None
        DeerFloor4BattleStrategy._color_cards_picked_p3 = None

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int, card_turn=0, **kwargs
    ) -> int:
        color_mapper: CardColorMapper | None = kwargs.get("color_mapper")

        if phase == 1 and DeerFloor4BattleStrategy._last_phase_seen != 1:
            self._initialize_static_variables()

        DeerFloor4BattleStrategy._last_phase_seen = phase

        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards, card_turn=card_turn)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(
                hand_of_cards, picked_cards, card_turn=card_turn, color_mapper=color_mapper
            )
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(
                hand_of_cards, picked_cards, card_turn=card_turn, color_mapper=color_mapper
            )
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(
                hand_of_cards, picked_cards, card_turn=card_turn, color_mapper=color_mapper
            )

        if card_turn == 3:
            DeerFloor4BattleStrategy.turn += 1

        return card_index

    def _maybe_reset(self, phase_id: str):
        if phase_id not in DeerFloor4BattleStrategy._phase_initialized:
            print("Resetting turn counter for phase", phase_id)
            DeerFloor4BattleStrategy.turn = 0
            DeerFloor4BattleStrategy._phase_initialized.add(phase_id)

    # -- Phase 1: purely unit-specific, no color mapper needed --

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int) -> int:
        # sourcery skip: merge-duplicate-blocks
        """The strategy is the following:

        Turn 1 - Freyr Cleave > tyr Att > Jorm buff removal > Thor Crit chance

        (This where the Strat deviates depending on the rng you get)

        Turn 2 (With an extra thor card) - Move thor card 2 times and use her lvl 2 (she must have 4 ult gauge )tyr card once.

        Turn 2 (without a extra thor card) - Attack with thor and move tyr card 3 times

        Turn 3 - (With extra thor card) - move thor once and use her card to kill, then move tyr or freyr card 2 times (u want tyr and freyr to be close to their ults. ideally u want tyr to have 3 ult points)
        """

        self._maybe_reset("phase_1")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

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

        if DeerFloor4BattleStrategy.turn == 0:
            if card_turn == 0:
                if not len(tyr_hel_cards):
                    raise ValueError(
                        "Something's very wrong with your bot, no Hel/Tyr cards detected. Resize the 7DS window and try again."
                    )
                return tyr_hel_cards[0]
            elif card_turn == 1:
                return jorm_cards[-1]
            elif card_turn == 2:
                return thor_cards[0]

            return tyr_hel_cards[-1]

        elif DeerFloor4BattleStrategy.turn == 1 and len(thor_cards):
            if card_turn <= 2:
                return [thor_cards[0], thor_cards[0] + 1]
            return thor_cards[-1]

        elif DeerFloor4BattleStrategy.turn == 2:
            cards_to_move = tyr_hel_cards if len(tyr_hel_cards) else jorm_cards
            if card_turn < 2:
                return [cards_to_move[0], cards_to_move[0] + 1]
            if card_turn == 2:
                if len(thor_cards) > 1:
                    return thor_cards[0]
                else:
                    return [cards_to_move[0], cards_to_move[0] + 1]
            if len(thor_cards):
                return thor_cards[0]

        print("[WARN] We couldn't finish in 3 turns...")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # -- Phase 2: color mapper for color groups, unit-specific for unit detection --

    def get_next_card_index_phase2(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, color_mapper: CardColorMapper | None
    ) -> int:
        # sourcery skip: extract-method
        self._maybe_reset("phase_2")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [
            card.card_rank.value if card.card_type != CardTypes.ULTIMATE else -card.card_rank.value
            for card in hand_of_cards
        ]

        tyr_hel_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Tyr_card(card) or is_Hel_card(card)],
            key=lambda idx: card_ranks[idx],
        )
        jorm_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Jorm_card(card)], key=lambda idx: card_ranks[idx]
        )

        green_card_ids, red_card_ids, blue_card_ids = self._get_color_groups(
            hand_of_cards, card_ranks, color_mapper
        )
        green_card_ids = reorder_jorms_heal(hand_of_cards, green_card_ids)

        num_red_cards = color_mapper.count_color_cards(hand_of_cards + picked_cards, CardColors.RED) if color_mapper else 0
        if DeerFloor4BattleStrategy.turn == 0 and num_red_cards > 1:
            if card_turn == 0:
                return red_card_ids[0]
            if card_turn <= 2:
                return [red_card_ids[0], red_card_ids[0] + 1]
            return red_card_ids[0]

        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}
        if card_turn == 0 or DeerFloor4BattleStrategy._color_cards_picked_p3 is None:
            card_colors = ["green", "blue"]
            n = DeerFloor4BattleStrategy.turn - 1
            rolled_colors = card_colors[-n % len(card_colors) :] + card_colors[: -n % len(card_colors)]
            rolled_colors.append("red")
            print("Current priority order:", rolled_colors)
            for color in rolled_colors:
                if len(card_groups[color]) >= 3:
                    DeerFloor4BattleStrategy._color_cards_picked_p3 = color
                    break
            else:
                DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))

        print(f"Setting '{DeerFloor4BattleStrategy._color_cards_picked_p3}' as the color type for this round!")
        picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
        if card_turn <= 2 and len(picked_card_ids):
            if card_turn == 2 and DeerFloor4BattleStrategy._color_cards_picked_p3 == "green":
                heal_ids = sorted(
                    [i for i, card in enumerate(hand_of_cards) if find(vio.jorm_1, card.card_image)],
                    key=lambda idx: card_ranks[idx],
                )
                if len(heal_ids):
                    print("Picking HEAL card!")
                    return heal_ids[-1]

            return picked_card_ids[-1]

        return self._move_card_for_ult(
            hand_of_cards + picked_cards,
            tyr_hel_cards=tyr_hel_cards,
            freyr_cards=red_card_ids,
            jorm_cards=jorm_cards,
            thor_cards=blue_card_ids,
        )

    # -- Phase 3: mapper color groups --

    def get_next_card_index_phase3(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, color_mapper: CardColorMapper | None
    ) -> int:
        self._maybe_reset("phase_3")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        card_ranks = [card.card_rank.value for card in hand_of_cards]
        green_card_ids, red_card_ids, blue_card_ids = self._get_color_groups(
            hand_of_cards, card_ranks, color_mapper
        )

        # Exclude Freyr's ult from red to save it for phase 4
        red_card_ids = [i for i in red_card_ids if not find(vio.freyr_ult, hand_of_cards[i].card_image)]

        green_card_ids = reorder_debuff_cards_to_front(hand_of_cards, green_card_ids)

        card_groups = {"green": green_card_ids, "red": red_card_ids, "blue": blue_card_ids}

        num_green_cards = color_mapper.count_color_cards(hand_of_cards + picked_cards, CardColors.GREEN) if color_mapper else 0
        if DeerFloor4BattleStrategy.turn == 0 and card_turn <= 2 and num_green_cards >= 3:
            DeerFloor4BattleStrategy._color_cards_picked_p3 = "green"
            return green_card_ids[-1]

        if card_turn == 0:
            card_colors = ["red", "green", "blue"]
            DeerFloor4BattleStrategy._color_cards_picked_p3 = max(card_colors, key=lambda k: len(card_groups[k]))
            print(f"Setting '{DeerFloor4BattleStrategy._color_cards_picked_p3}' as the color type for this round!")

        picked_card_ids = card_groups[DeerFloor4BattleStrategy._color_cards_picked_p3]
        if card_turn <= 2 and len(picked_card_ids):
            return picked_card_ids[-1]

        if card_turn > 2:
            picked_color_ids = max(green_card_ids, red_card_ids, blue_card_ids, key=len)
            idx = -1
            if not len(picked_color_ids):
                return idx
            if find(vio.freyr_ult, hand_of_cards[picked_color_ids[idx]].card_image):
                print(f"We found Freyr's ult on the picked id {picked_color_ids[idx]}! Saving it for phase 4")
                idx -= 1
            return picked_color_ids[idx]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # -- Phase 4: mapper color groups + roulette + unit-specific --

    def get_next_card_index_phase4(
        self, hand_of_cards: list[Card], picked_cards: list[Card], card_turn: int, color_mapper: CardColorMapper | None
    ) -> int:
        self._maybe_reset("phase_4")

        if card_turn == 0:
            print(f"TURN {DeerFloor4BattleStrategy.turn}:")

        screenshot, _ = capture_window()

        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        green_card_ids, red_card_ids, blue_card_ids = self._get_color_groups(
            hand_of_cards, card_ranks.tolist(), color_mapper
        )
        tyr_hel_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Tyr_card(card) or is_Hel_card(card)],
            key=lambda idx: card_ranks[idx],
        )
        jorm_cards = sorted(
            [i for i, card in enumerate(hand_of_cards) if is_Jorm_card(card)], key=lambda idx: card_ranks[idx]
        )

        # If Deer has a counter, use Hel ult if we have it
        if find(vio.snake_f3p2_counter, screenshot):
            if len(hel_ult_ids := [i for i, card in enumerate(hand_of_cards) if find(vio.hel_ult, card.card_image)]):
                return hel_ult_ids[-1]

        if DeerFloor4BattleStrategy.turn < 3:
            print("DISABLING ULTS!")
            blue_card_ids = blue_card_ids[::-1]
            green_card_ids = green_card_ids[::-1]
            if DeerFloor4BattleStrategy.turn < 2:
                red_card_ids = red_card_ids[::-1]

            if card_turn == 3 and not find(vio.hel_ult, picked_cards[0].card_image):
                return self._move_card_for_ult(
                    hand_of_cards + picked_cards,
                    tyr_hel_cards=tyr_hel_cards,
                    freyr_cards=red_card_ids,
                    jorm_cards=jorm_cards,
                    thor_cards=blue_card_ids,
                )

        green_card_ids = reorder_debuff_cards_to_front(hand_of_cards, green_card_ids)

        # --- Roulette ---

        color_groups = {CardColors.RED: red_card_ids, CardColors.BLUE: blue_card_ids, CardColors.GREEN: green_card_ids}

        if card_turn == 0 and DeerFloor4BattleStrategy.turn == 0:
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
                print("We're starting the round with a BLUE card!")
                return blue_card_ids[-1]
            if find(vio.red_buff, screenshot) and len(red_card_ids):
                print("We're starting the round with a RED card!")
                return red_card_ids[-1]
            if find(vio.green_buff, screenshot) and len(green_card_ids):
                print("We're starting the round with a GREEN card!")
                return green_card_ids[-1]

        last_advancing_card = Card()
        for i in range(card_turn - 1, -1, -1):
            if picked_cards[i].card_type in ADVANCING_TYPES:
                last_advancing_card = picked_cards[i]
                break

        # Special case: Hel's ult didn't trigger green buff
        if card_turn == 1 and find(vio.hel_ult, last_advancing_card.card_image) and not find(vio.green_buff, screenshot):
            print("Last card is Hel's ult, but no green buff! Re-starting the wheel.")
            last_advancing_card = Card()

        last_color = color_mapper.get_card_color(last_advancing_card) if color_mapper else CardColors.NONE

        if last_color == CardColors.RED and len(green_card_ids):
            print("Last card red! Picking green")
            if DeerFloor4BattleStrategy.turn == 2:
                print("Can we use a buff removal??")
            buff_removal_ids = [i for i, card in enumerate(hand_of_cards) if is_buff_removal_card(card)]
            return (
                buff_removal_ids[-1]
                if len(buff_removal_ids) and DeerFloor4BattleStrategy.turn == 2
                else green_card_ids[-1]
            )

        if last_color in _COLOR_WHEEL:
            next_color = _COLOR_WHEEL[last_color]
            if len(color_groups[next_color]):
                print(f"Last card {last_color.name}! Picking {next_color.name}")
                return color_groups[next_color][-1]

        print("Couldn't find the right card, defaulting while avoiding ultimates...")
        ult_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type == CardTypes.ULTIMATE]
        for uid in ult_ids:
            hand_of_cards[uid].card_type = CardTypes.DISABLED
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    # -- Helpers --

    @staticmethod
    def _get_color_groups(
        hand_of_cards: list[Card], card_ranks: list, color_mapper: CardColorMapper | None
    ) -> tuple[list[int], list[int], list[int]]:
        """Return (green_ids, red_ids, blue_ids) sorted by card_ranks."""
        if color_mapper and color_mapper.is_calibrated:
            green = sorted(
                [i for i, c in enumerate(hand_of_cards) if color_mapper.get_card_color(c) == CardColors.GREEN],
                key=lambda idx: card_ranks[idx],
            )
            red = sorted(
                [i for i, c in enumerate(hand_of_cards) if color_mapper.get_card_color(c) == CardColors.RED],
                key=lambda idx: card_ranks[idx],
            )
            blue = sorted(
                [i for i, c in enumerate(hand_of_cards) if color_mapper.get_card_color(c) == CardColors.BLUE],
                key=lambda idx: card_ranks[idx],
            )
        else:
            green, red, blue = [], [], []
        return green, red, blue

    def _move_card_for_ult(
        self,
        list_of_cards: list[Card],
        tyr_hel_cards: list[Card],
        freyr_cards: list[Card],
        jorm_cards: list[Card],
        thor_cards: list[Card],
    ):
        """Move a card of someone that doesn't have an ult"""
        unit_to_cards = {
            "tyr": tyr_hel_cards,
            "hel": tyr_hel_cards,
            "freyr": freyr_cards,
            "jorm": jorm_cards,
            "thor": thor_cards,
        }
        for unit in ["tyr", "hel", "freyr", "jorm", "thor"]:
            if not has_ult(unit, list_of_cards):
                cards = unit_to_cards[unit]
                if len(cards):
                    print(f"Unit {unit} doesn't have an ult yet!")
                    return [cards[0], cards[0] + 1]

        return [-2, -1]
