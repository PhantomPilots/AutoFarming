import argparse

from utilities.dogs_farming_logic import DogsFarmer, States
from utilities.dogs_fighting_strategies import DogsBattleStrategy
from utilities.farming_factory import FarmingFactory


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument("--clears", type=str, default="inf", help="Number of clears or 'inf'")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DogsFarmer,
        battle_strategy=DogsBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DB,  # Should be 'GOING_TO_DB'
        reset_after_defeat=True,  # After we lose, should we reset the Demonic Beast team?
        max_stamina_pots="inf",  # How many stamina pots at most
        max_floor_3_clears=args.clears,  # How many floor 3 clears at most
        password=args.password,  # Account password
        do_dailies=True,  # Should we do our dailies?
    )


if __name__ == "__main__":

    main()
