import argparse

from utilities.daily_farming_logic import DailyFarmer, States
from utilities.farming_factory import FarmingFactory


def main():
    parser = argparse.ArgumentParser(description="Run standalone daily quest automation.")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP while running daily quests (default: True)",
    )
    parser.add_argument(
        "--do-daily-pvp",
        dest="daily_pvp",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DailyFarmer,
        starting_state=States.IN_TAVERN_STATE,  # Should be 'IN_TAVERN_STATE'
        restart_on_completion=False,
        do_daily_pvp=args.daily_pvp,  # Whether to auto a PVP match (you may win, who knows 🤷‍♂️)
    )


if __name__ == "__main__":

    main()
