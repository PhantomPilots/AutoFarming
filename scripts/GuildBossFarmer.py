import argparse

import utilities.vision_images as vio
from utilities.canopus_fighting_strategy import CanopusBattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.guild_boss_fighter import GuildBossFighter
from utilities.guild_boss_farming_logic import GuildBossFarmer, States

GUILD_BOSSES = {"Canopus": (vio.canopus_hel, CanopusBattleStrategy)}


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--push-week", action="store_true", help="Push the selected weekly Guild Boss")
    parser.add_argument("--guild-boss", choices=GUILD_BOSSES, default="Canopus", help="Guild Boss to push")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    args = parser.parse_args()
    guild_boss, battle_strategy = GUILD_BOSSES[args.guild_boss]

    FarmingFactory.main_loop(
        farmer=GuildBossFarmer,
        battle_strategy=battle_strategy if args.push_week else None,
        starting_state=States.FIGHTING,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
        password=args.password,
        push_week=args.push_week,
        guild_boss=guild_boss,
        fighter_cls=GuildBossFighter if args.push_week else None,
    )


if __name__ == "__main__":
    main()
