import argparse

from utilities.bird_farming_logic import BirdFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import DummyBattleStrategy, SmarterBattleStrategy


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=BirdFarmer,
        battle_strategy=SmarterBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_BIRD,  # Should be 'GOING_TO_BIRD'
        num_floor_3_clears=args.clears,  # A number or "inf"
        password=args.password,  # Account password
    )


if __name__ == "__main__":

    main()
