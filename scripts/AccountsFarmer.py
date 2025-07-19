import argparse

from utilities.accounts_farming_logic import ManyAccountsFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    parser = argparse.ArgumentParser(description="Run the Many Accounts Farmer.")
    parser.add_argument("--do-weeklies", action="store_true", help="Whether to do weeklies or not")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=ManyAccountsFarmer,
        starting_state=States.SWITCH_ACCOUNT,  # Should be 'DALY_QUESTS'
        do_weeklies=args.do_weeklies,  # Whether to do weeklies or not
    )


if __name__ == "__main__":
    main()
