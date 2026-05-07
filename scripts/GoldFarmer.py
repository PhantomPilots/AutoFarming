import argparse

from utilities.farming_factory import FarmingFactory
from utilities.gold_farming_logic import GoldFarmer, States


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=GoldFarmer,
        starting_state=States.GOING_TO_DUNGEON,
        password=args.password,
        do_dailies=args.do_dailies,
    )


if __name__ == "__main__":
    main()
