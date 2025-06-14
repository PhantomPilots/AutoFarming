import argparse

from utilities.farming_factory import FarmingFactory
from utilities.final_boss_farming_logic import FinalBossFarmer, States


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--difficulty",
        "-d",
        type=str,
        choices=["hard", "hell", "challenge"],
        default="hell",
        help="FinalBoss difficulty (default: hell)",
    )
    parser.add_argument(
        "--clears",
        type=str,
        default="20",
        help="Number of runs to perform (default: 1, set to 'inf' for infinite runs)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=FinalBossFarmer,
        starting_state=States.GOING_TO_FB,  # Should be 'GOING_TO_FB'
        difficulty=args.difficulty,  # Can be "hard", "extreme", "hell", "challenge"
        num_runs=args.clears,  # How many runs we want. Set to "inf" for infinite runs.
    )


if __name__ == "__main__":

    main()
