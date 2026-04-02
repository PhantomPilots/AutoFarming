import argparse

from utilities.farming_factory import FarmingFactory
from utilities.sa_dungeon_farming_logic import SADungeonFarmer, States


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-resets",
        default=10,
        type=int,
        help="How many times we'll allow to reset if we don't see a chest on phase 1",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=SADungeonFarmer,
        starting_state=States.GOING_TO_DUNGEON,  # Should be 'GOING_TO_DUNGEON'
        max_resets=args.max_resets,  # How many times we'll allow to reset
    )


if __name__ == "__main__":

    main()
