import argparse

from utilities.farming_factory import FarmingFactory
from utilities.supreme_deity_farming_logic import States, SupremeDeityFarmer


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--difficulty",
        "-d",
        type=str,
        choices=["hard", "extreme", "hell"],
        default="hell",
        help="Supreme Deity difficulty (default: hell)",
    )
    parser.add_argument(
        "--clears",
        type=str,
        default="10",
        help="Number of runs to perform (default: 10, set to 'inf' for infinite runs)",
    )
    parser.add_argument(
        "--stigmata",
        type=str,
        choices=["auto", "never"],
        default="auto",
        help="auto: Stigmata of Weakening on the Third Judgment and the final boss. never: no Stigmata (default: auto)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=SupremeDeityFarmer,
        starting_state=States.GOING_TO_SUPREME_DEITY,
        difficulty=args.difficulty,
        num_clears=args.clears,
        stigmata=args.stigmata,
    )


if __name__ == "__main__":

    main()
