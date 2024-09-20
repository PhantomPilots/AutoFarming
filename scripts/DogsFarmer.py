from utilities.dogs_farming_logic import DogsFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import DummyBattleStrategy, SmarterBattleStrategy


def main():

    FarmingFactory.main_loop(
        farmer=DogsFarmer,
        battle_strategy=SmarterBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DOGS,  # Should be 'GOING_TO_DOGS'
    )


if __name__ == "__main__":

    main()
