from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy


class DogsBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Snake"""

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int, **kwargs
    ) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if floor == 1 and phase == 2:
            return self.floor_1_phase_2(hand_of_cards, picked_cards)

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_1_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Keep at least 2 ultimates in hand!"""

        # Identify the IDs that contain an ultimate
        ult_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type == CardTypes.ULTIMATE]

        # Disable the first 2 ultimates
        for i, id in enumerate(ult_ids[::-1]):
            if i < 2:
                print("Disabling an ultimate!")
                hand_of_cards[id].card_type = CardTypes.DISABLED

        # Default to Smarter strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
