import argparse

from utilities.dogs_floor4_fighting_strategies import DogsFloor4BattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.floor_4_farmers import DogsFloor4Farmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DogsFloor4Farmer,
        battle_strategy=DogsFloor4BattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_runs=args.clears,
        password=args.password,
        do_dailies=args.do_dailies,
    )


if __name__ == "__main__":

    main()
