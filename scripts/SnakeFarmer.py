from utilities.farming_factory import FarmingFactory
from utilities.snake_farming_logic_2 import SnakeFarmer, States
from utilities.snake_fighting_strategies import SnakeBattleStrategy


def main():

    FarmingFactory.main_loop(
        farmer=SnakeFarmer,
        battle_strategy=SnakeBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DB,  # It should be 'GOING_TO_DB'
        reset_after_defeat=False,  # After we lose, should we reset the Demonic Beast team?
        max_stamina_pots="inf",  # How many stamina pots at most
        max_floor_3_clears="inf",  # How many floor 3 clears at most
    )


if __name__ == "__main__":

    main()
