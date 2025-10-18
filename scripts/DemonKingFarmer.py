import argparse

from utilities.demon_king_farming_logic import DemonKingFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import SmarterBattleStrategy


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dk-diff",
        "-d",
        type=str,
        choices=["hard", "extreme", "hell"],
        default="hell",
        help="Difficulty (choices: hard, extreme, hell)",
    )
    parser.add_argument("--max-coins", default=float("inf"), type=str, help="How many max coins to use")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DemonKingFarmer,
        starting_state=States.GOING_TO_DK,
        battle_strategy=SmarterBattleStrategy,
        max_coins=args.max_coins,
        dk_difficulty=args.dk_diff,
    )


if __name__ == "__main__":
    main()
