import argparse

from utilities.farming_factory import FarmingFactory
from utilities.rat_farming_logic import RatFarmer, States
from utilities.rat_fighting_strategies import RatFightingStrategy


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=RatFarmer,
        battle_strategy=RatFightingStrategy,  # The AI that will pick the cards
        starting_state=States.FIGHTING_FLOOR,  # Should be 'GOING_TO_BIRD'
        num_floor_3_clears=args.clears,  # A number or "inf"
        password=args.password,  # Account password
        do_dailies=args.do_dailies,  # Should we do our dailies?
    )


if __name__ == "__main__":

    main()
