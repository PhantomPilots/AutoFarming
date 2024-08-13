from utilities.farming_factory import FarmingFactory
from utilities.final_boss_farming_logic import FinalBossFarmer, States


def main():

    FarmingFactory.main_loop(
        farmer=FinalBossFarmer,
        battle_strategy=None,  # The final boss is 'auto', no need for an AI
        starting_state=States.GOING_TO_FB,  # Should be 'GOING_TO_FB'
        difficulty="hell",  # Can be "hard", "extreme", "hell", "challenge"
    )


if __name__ == "__main__":

    main()
