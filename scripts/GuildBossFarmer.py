import argparse

from utilities.farming_factory import FarmingFactory
from utilities.guild_boss_farming_logic import GuildBossFarmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=GuildBossFarmer,
        starting_state=States.FIGHTING,
        do_dailies=args.do_dailies,
        do_daily_pvp=True,
        password=args.password,
    )


if __name__ == "__main__":
    main()
