from utilities.farming_factory import FarmingFactory
from utilities.many_accounts_farmer import ManyAccountsFarmer, States


def main():
    FarmingFactory.main_loop(
        farmer=ManyAccountsFarmer,
        starting_state=States.DAILY_QUESTS,  # Should be 'DALY_QUESTS'
    )


if __name__ == "__main__":
    main()
