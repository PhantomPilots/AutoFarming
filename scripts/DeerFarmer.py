from utilities.deer_farming_logic import DeerFarmer, States
from utilities.deer_fighting_strategies import DeerBattleStrategy
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DeerFarmer,
        battle_strategy=DeerBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_DB,  # It should be 'GOING_TO_DB'
        reset_after_defeat=True,  # After we lose, should we reset the Demonic Beast team?
        max_stamina_pots="inf",  # How many stamina pots at most
        max_floor_3_clears="inf",  # How many floor 3 clears at most
    )


if __name__ == "__main__":

    main()
