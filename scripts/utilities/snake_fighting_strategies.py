import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import (
    capture_window,
    determine_card_merge,
    find,
    is_hard_hitting_snake_card,
    is_stance_cancel_card,
)


class SnakeBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Snake"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if floor in {1, 3} and phase == 1:
            return self.floor_13_phase_1(hand_of_cards, picked_cards)

        elif floor == 2:
            if phase == 1:
                return self.floor_2_phase_1(hand_of_cards, picked_cards)

        elif floor == 3:
            if phase == 2:
                return self.floor_3_phase_2(hand_of_cards, picked_cards)
            elif phase == 3:
                return self.floor_3_phase_3(hand_of_cards, picked_cards)

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_13_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Use all high-hitting cards"""

        ham_ids = np.where([is_hard_hitting_snake_card(card) for card in hand_of_cards])[0]
        if len(ham_ids):
            return ham_ids[-1]

        # Default to Smarter strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_2_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Strategy for Phase 1 of Floor 2: We cannot use Liz's AOE card until the very end"""

        # If it's the last card to play, use Liz's AOE:
        if IBattleStrategy.cards_to_play - IBattleStrategy.card_turn == 1:
            print("Can we use Liz's AOE card?")
            liz_aoe_ids = np.where([find(vio.lr_liz_aoe, card.card_image) for card in hand_of_cards])[0]
            if len(liz_aoe_ids):
                return liz_aoe_ids[-1]

        # Default strategy: Simply use HAM cards to one-turn it
        ham_ids = np.where(
            [
                find(vio.freyja_st, card.card_image)
                or find(vio.mael_aoe, card.card_image)
                or find(vio.mael_st, card.card_image)
                for card in hand_of_cards
            ]
        )[0]
        if len(ham_ids):
            return ham_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_3_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        # sourcery skip: for-index-replacement
        """Use stance card at the very end of each turn?"""

        screenshot, _ = capture_window()

        # Card ranks for sorting
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])

        played_freyja_ids = np.where(
            [
                find(vio.freyja_aoe, card.card_image)
                or find(vio.freyja_st, card.card_image)
                or find(vio.freyja_ult, card.card_image)
                for card in picked_cards
            ]
        )[0]
        played_stance_cancel_ids = np.where(
            [
                find(vio.freyja_st, card.card_image)
                or find(vio.mael_ult, card.card_image)
                or find(vio.margaret_st, card.card_image)
                for card in picked_cards
            ]
        )[0]

        # First, play a buff if possible
        buff_ids = np.where([card.card_type == CardTypes.BUFF for card in hand_of_cards])[0]
        # Sort the buff IDs based on card ranks
        buff_ids = sorted(buff_ids, key=lambda idx: card_ranks[idx])
        played_buff_ids = np.where([card.card_type == CardTypes.BUFF for card in picked_cards])[0]
        if len(buff_ids) and not len(played_buff_ids):
            return buff_ids[-1]

        # If we have an extort...
        if (
            find(vio.extort, screenshot)
            and not len(played_buff_ids)
            and not np.any([find(vio.lr_liz_aoe, card.card_image) for card in picked_cards])
        ):
            if len(liz_aoe_ids := np.where([find(vio.lr_liz_aoe, card.card_image) for card in hand_of_cards])[0]):
                print("We need to remove the extort!")
                return liz_aoe_ids[-1]

        mael_ult_id: list[int] = np.where([find(vio.mael_ult, card.card_image) for card in hand_of_cards])[0]
        # If enemy has stance/damage increase, gotta remove it:
        if find(vio.snake_f3p2_counter, screenshot, threshold=0.6) or find(
            vio.damage_increase, screenshot, threshold=0.8
        ):
            if len(mael_ult_id):
                print("Removing counter/damage increase with Mael's ultimate!")
                return mael_ult_id[-1]
            elif len(
                freyja_st_ids := np.where([find(vio.freyja_st, card.card_image) for card in hand_of_cards])[0]
            ) and not len(played_stance_cancel_ids):
                print("Playing a Freyja ST to remove damage increase or counter.")
                return freyja_st_ids[-1]
            # If we don't have Freyja ST cards or Mael's ult, use a Margaret ST ONLY if damage increase is on!
            elif (
                find(vio.damage_increase, screenshot, threshold=0.8)
                and len(
                    margaret_st_ids := np.where([find(vio.margaret_st, card.card_image) for card in hand_of_cards])[0]
                )
                and not len(played_stance_cancel_ids)
            ):
                print("Playing a Margaret ST to remove damage increase.")
                return margaret_st_ids[-1]

        elif len(mael_ult_id):
            # Disable Mael's ultimate, to save it for later
            print("Saving Mael's ultimate for the future...")
            hand_of_cards[mael_ult_id[-1]].card_type = CardTypes.DISABLED

        # Play a Freyja card to avoid getting darkness!
        if not len(played_freyja_ids):
            # Try to play the ult
            if len(freyja_ult_id := np.where([find(vio.freyja_ult, card.card_image) for card in hand_of_cards])[0]):
                return freyja_ult_id[-1]
            # If not, try to play an AOE
            if len(freyja_aoe_ids := np.where([find(vio.freyja_aoe, card.card_image) for card in hand_of_cards])[0]):
                return freyja_aoe_ids[-1]
            # If not, try to play a single target IF we are not playing any buff this turn (arbitrary)
            if not len(played_buff_ids) and len(
                freyja_st_ids := np.where([find(vio.freyja_st, card.card_image) for card in hand_of_cards])[0]
            ):
                return freyja_st_ids[-1]

        # Set all stance IDs to DISABLED
        for i in range(len(hand_of_cards)):
            if is_stance_cancel_card(hand_of_cards[i]):
                hand_of_cards[i].card_type = CardTypes.DISABLED

        # Extract the card types AFTER disabling stance cards
        card_types = np.array([card.card_type.value for card in hand_of_cards])

        # ULTIMATES
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if len(ult_ids):
            return ult_ids[-1]

        # Liz AOE card
        liz_aoe_ids = np.where([find(vio.lr_liz_aoe, card.card_image) for card in hand_of_cards])[0]
        if len(liz_aoe_ids) and not np.any([find(vio.lr_liz_aoe, card.card_image) for card in picked_cards]):
            return liz_aoe_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where((card_types == CardTypes.ATTACK.value) | (card_types == CardTypes.ATTACK_DEBUFF.value))[0]
        if len(attack_ids):
            return attack_ids[-1]

        # Other BUFF CARDS
        if len(buff_ids):
            return buff_ids[-1]

        # CARD MERGE
        for i in range(len(hand_of_cards) - 2, 0, -1):
            if determine_card_merge(hand_of_cards[i - 1], hand_of_cards[i + 1]):
                # We can generate a merge, play that card
                print("Generating a merge, even if it's a stance cancel...")
                return i

        # Default to moving cards
        return [-1, -2]

    def floor_3_phase_3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """If we see an enemy stance, use a stance cancel"""

        screenshot, _ = capture_window()

        if find(vio.snake_stance, screenshot, threshold=0.8):
            print("The snake has a stance! Can we cancel it?")

            # Cancel the stance and also play a buff if possible
            buff_ids = np.where([card.card_type == CardTypes.BUFF for card in hand_of_cards])[0]
            played_buff_ids = np.where([card.card_type == CardTypes.BUFF for card in picked_cards])[0]
            stance_ids = np.where([is_stance_cancel_card(card) for card in hand_of_cards])[0]
            played_stance_ids = np.where([is_stance_cancel_card(card) for card in picked_cards])[0]

            if len(stance_ids) and not len(played_stance_ids):
                return stance_ids[-1]

            if len(buff_ids) and not len(played_buff_ids):
                return buff_ids[-1]

        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
