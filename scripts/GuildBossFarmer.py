import argparse

from utilities.farming_factory import FarmingFactory
from utilities.guild_boss_farming_logic import GuildBossFarmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=GuildBossFarmer,
        starting_state=States.FIGHTING,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
        password=args.password,
    )


if __name__ == "__main__":
    main()
