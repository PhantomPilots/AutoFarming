import argparse

from utilities.farming_factory import FarmingFactory
from utilities.floor_4_farmers import DogsFloor4Farmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--extra-clears", type=int, default=0, help="How many of the total clears should use extra mode")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--whale",
        action="store_true",
        default=False,
        help="Use the stacked-account Gowther + Meli3k Dogs Floor 4 strat.",
    )
    args = parser.parse_args()

    if args.whale:
        from utilities.dogs_floor4_fighting_strategies_whale import DogsFloor4WhaleBattleStrategy as BattleStrategy
    else:
        from utilities.dogs_floor4_fighting_strategies import DogsFloor4BattleStrategy as BattleStrategy

    FarmingFactory.main_loop(
        farmer=DogsFloor4Farmer,
        battle_strategy=BattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_runs=args.clears,
        extra_clears=args.extra_clears,
        password=args.password,
        do_dailies=args.do_dailies,
        whale=args.whale,
    )


if __name__ == "__main__":

    main()

