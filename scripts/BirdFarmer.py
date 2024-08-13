from utilities.bird_farming_logic import BirdFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import DummyBattleStrategy, SmarterBattleStrategy


def main():

    FarmingFactory.main_loop(
        farmer=BirdFarmer,
        battle_strategy=DummyBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_BIRD,  # Should be 'GOING_TO_BIRD'
    )


if __name__ == "__main__":

    main()
