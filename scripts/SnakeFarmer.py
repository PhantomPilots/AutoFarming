import argparse

from utilities.farming_factory import FarmingFactory
from utilities.snake_farming_logic import SnakeFarmer, States
from utilities.snake_fighting_strategies import SnakeBattleStrategy


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=True, help="Do dailies (default: True)")
    parser.add_argument("--no-do-dailies", dest="do_dailies", action="store_false", help="Don't do dailies")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=SnakeFarmer,
        battle_strategy=SnakeBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DB,  # It should be 'GOING_TO_DB'
        reset_after_defeat=True,  # After we lose, should we reset the Demonic Beast team?
        max_stamina_pots="inf",  # How many stamina pots at most
        max_floor_3_clears=args.clears,  # How many floor 3 clears at most
        password=args.password,  # Account password
        do_dailies=args.do_dailies,
    )


if __name__ == "__main__":

    main()
