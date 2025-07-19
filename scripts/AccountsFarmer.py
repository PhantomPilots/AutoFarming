from utilities.accounts_farming_logic import ManyAccountsFarmer, States
from utilities.farming_factory import FarmingFactory


def main():
    FarmingFactory.main_loop(
        farmer=ManyAccountsFarmer,
        starting_state=States.SWITCH_ACCOUNT,  # Should be 'DALY_QUESTS'
    )


if __name__ == "__main__":
    main()
