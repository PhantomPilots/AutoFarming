import argparse

from utilities.dogs_floor4_fighting_strategies import DogsFloor4BattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.floor_4_farmers import DogsFloor4Farmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DogsFloor4Farmer,
        battle_strategy=DogsFloor4BattleStrategy,  # Placeholder until dedicated Dogs Floor 4 AI is added
        starting_state=States.GOING_TO_DB,  # Should be 'GOING_TO_FLOOR' or 'FIGHTING', to start from outside or within the fight
        max_runs=args.clears,  # Can be a number or "inf"
        password=args.password,  # Account password
        do_dailies=args.do_dailies,  # Should we do our dailies?
    )


if __name__ == "__main__":

    main()
