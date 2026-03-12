import argparse

from utilities.farming_factory import FarmingFactory
from utilities.legendary_boss_farming_logic import LegendaryBossFarmer, States


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--difficulty",
        "-d",
        type=str,
        choices=["extreme", "hell", "challenge"],
        default="hell",
        help="LegendaryBoss difficulty (default: hell)",
    )
    parser.add_argument(
        "--clears",
        type=str,
        default="20",
        help="Number of runs to perform (default: 1, set to 'inf' for infinite runs)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=LegendaryBossFarmer,
        starting_state=States.GOING_TO_LB,  # Should be 'GOING_TO_LB'
        difficulty=args.difficulty,  # Can be "extreme", "hell", "challenge"
        num_runs=args.clears,  # How many runs we want. Set to "inf" for infinite runs.
    )


if __name__ == "__main__":

    main()
