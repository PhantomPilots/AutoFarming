from utilities.dogs_farming_logic import DogsFarmer, States
from utilities.dogs_fighting_strategies import DogsBattleStrategy
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DogsFarmer,
        battle_strategy=DogsBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DB,  # Should be 'GOING_TO_DOGS'
        reset_after_defeat=True,  # After we lose, should we reset the Demonic Beast team?
        max_stamina_pots="inf",  # How many stamina pots at most
        max_floor_3_clears=10,  # How many floor 3 clears at most
    )


if __name__ == "__main__":

    main()
