import argparse

from utilities.farming_factory import FarmingFactory
from utilities.gold_farming_logic import GoldFarmer, States


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--use-skip-tickets", action="store_true", default=False, help="Use skip tickets")
    parser.add_argument(
        "--max-skip-tickets-to-use",
        type=float,
        default=float("inf"),
        help="Maximum number of skip tickets to use or 'inf'",
    )
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=GoldFarmer,
        starting_state=States.GOING_TO_DUNGEON,
        password=args.password,
        use_skip_tickets=args.use_skip_tickets,
        max_skip_tickets_to_use=args.max_skip_tickets_to_use,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
    )


if __name__ == "__main__":
    main()
