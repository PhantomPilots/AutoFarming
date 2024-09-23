from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import SmarterBattleStrategy
from utilities.snake_farming_logic import SnakeFarmer, States
from utilities.snake_fighting_strategies import SnakeBattleStrategy


def main():

    FarmingFactory.main_loop(
        farmer=SnakeFarmer,
        battle_strategy=SnakeBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_SNAKE,  # Should be 'GOING_TO_DOGS'
    )


if __name__ == "__main__":

    main()
