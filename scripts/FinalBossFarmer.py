from utilities.farming_factory import FarmingFactory
from utilities.final_boss_farming_logic import FinalBossFarmer, States


def main():

    FarmingFactory.main_loop(
        farmer=FinalBossFarmer,
        starting_state=States.GOING_TO_FB,  # Should be 'GOING_TO_FB'
        difficulty="hell",  # Can be "hard", "extreme", "hell", "challenge"
        num_runs="inf",  # How many runs we want. Set to "inf" for infinite runs.
    )


if __name__ == "__main__":

    main()
