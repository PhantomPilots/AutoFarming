from utilities.dogs_farming_logic import DogsFarmer, States
from utilities.dogs_fighting_strategies import DogsBattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import SmarterBattleStrategy


def main():

    FarmingFactory.main_loop(
        farmer=DogsFarmer,
        battle_strategy=DogsBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DOGS,  # Should be 'GOING_TO_DOGS'
        max_stamina_pots="inf",  # How many stamina pots to use at max
    )


if __name__ == "__main__":

    main()
