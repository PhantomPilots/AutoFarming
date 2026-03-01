import argparse

from utilities.farming_factory import FarmingFactory
from utilities.snake_farming_logic import SnakeFarmer, States


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument("--whale", action="store_true", default=False, help="Use whale strategy")
    args = parser.parse_args()

    if args.whale:
        from utilities.snake_fighting_strategies_whale import SnakeBattleStrategy
    else:
        from utilities.snake_fighting_strategies import SnakeBattleStrategy

    FarmingFactory.main_loop(
        farmer=SnakeFarmer,
        battle_strategy=SnakeBattleStrategy,
        starting_state=States.GOING_TO_DB,
        reset_after_defeat=True,
        max_stamina_pots="inf",
        max_floor_3_clears=args.clears,
        password=args.password,
        do_dailies=args.do_dailies,
    )


if __name__ == "__main__":

    main()
