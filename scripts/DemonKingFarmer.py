import argparse

from utilities.demon_king_farming_logic import DemonKingFarmer, States
from utilities.dk_fighting_strategies import DemonKingBattleStrategy
from utilities.farming_factory import FarmingFactory


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dk-diff",
        "-d",
        type=str,
        choices=["hard", "extreme", "hell"],
        default="hard",
        help="Difficulty (choices: hard, extreme, hell)",
    )
    parser.add_argument(
        "--num-clears", default=float("inf"), type=str, help="How many times to clear the Demon King fight."
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DemonKingFarmer,
        starting_state=States.GOING_TO_DK,
        battle_strategy=DemonKingBattleStrategy,
        num_clears=args.num_clears,
        dk_difficulty=args.dk_diff,
    )


if __name__ == "__main__":
    main()
