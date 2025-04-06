import argparse

from utilities.deer_fighting_strategies import DeerBattleStrategy
from utilities.deer_floor4_fighting_strategies import DeerFloor4BattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.floor_4_farmers import DeerFloor4Farmer, States


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DeerFloor4Farmer,
        battle_strategy=DeerFloor4BattleStrategy,  # The AI. Floor 4 requires a very specific logic
        starting_state=States.GOING_TO_DB,  # Should be 'GOING_TO_FLOOR' or 'FIGHTING', to start the script from outside or within the fight
        max_runs="inf",  # Can be a number or "inf"
        password=args.password,  # Account password
    )


if __name__ == "__main__":

    main()
