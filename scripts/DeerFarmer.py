import argparse

from utilities.deer_farming_logic import DeerFarmer, States
from utilities.deer_fighting_strategies import DeerBattleStrategy
from utilities.farming_factory import FarmingFactory


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DeerFarmer,
        battle_strategy=DeerBattleStrategy,
        starting_state=States.GOING_TO_DB,
        reset_after_defeat=True,
        max_stamina_pots="inf",
        max_floor_3_clears=args.clears,
        password=args.password,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
    )


if __name__ == "__main__":

    main()
