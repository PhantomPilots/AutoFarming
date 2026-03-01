import argparse

from utilities.deer_farming_logic import DeerFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument("--whale", action="store_true", default=False, help="Use whale strategy")
    args = parser.parse_args()

    if args.whale:
        from utilities.deer_whale_fighting_strategies import DeerBattleStrategy
    else:
        from utilities.deer_fighting_strategies import DeerBattleStrategy

    FarmingFactory.main_loop(
        farmer=DeerFarmer,
        battle_strategy=DeerBattleStrategy,
        starting_state=States.GOING_TO_DB,
        reset_after_defeat=True,
        max_stamina_pots="inf",
        max_floor_3_clears=args.clears,
        password=args.password,
        do_dailies=args.do_dailies,
    )


if __name__ == "__main__":

    main()
