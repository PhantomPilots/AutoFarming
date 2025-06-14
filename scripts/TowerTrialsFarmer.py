from utilities.farming_factory import FarmingFactory
from utilities.tower_trials_farming_logic import States, TowerTrialsFarmer


def main():
    FarmingFactory.main_loop(
        farmer=TowerTrialsFarmer,
        starting_state=States.READY_TO_FIGHT,  # Should be 'READY_TO_FIGHT'
    )


if __name__ == "__main__":
    main()
