import argparse

from utilities.farming_factory import FarmingFactory
from utilities.guild_boss_farming_logic import GuildBossFarmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument(
        "--max-pots",
        type=str,
        default="inf",
        help="Max stamina pots: a whole number of 0 or more, or 'inf' for no limit",
    )
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    args = parser.parse_args()

    try:
        limit = args.max_pots.strip().lower()
        args.max_pots = float("inf") if limit == "inf" else int(limit)
        if args.max_pots < 0:
            raise ValueError
    except ValueError:
        parser.error("Enter a whole number of 0 or more, or inf for no limit.")

    FarmingFactory.main_loop(
        farmer=GuildBossFarmer,
        starting_state=States.FIGHTING,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
        password=args.password,
        max_stamina_pots=args.max_pots,
    )


if __name__ == "__main__":
    main()
