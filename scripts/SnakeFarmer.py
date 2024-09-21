from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import DummyBattleStrategy, SmarterBattleStrategy
from utilities.snake_farming_logic import SnakeFarmer, States


def main():

    FarmingFactory.main_loop(
        farmer=SnakeFarmer,
        battle_strategy=SmarterBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_SNAKE,  # Should be 'GOING_TO_DOGS'
    )


if __name__ == "__main__":

    main()
