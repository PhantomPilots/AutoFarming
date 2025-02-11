from utilities.daily_farming_logic import DailyFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DailyFarmer,
        starting_state=States.IN_TAVERN_STATE,  # Should be 'IN_TAVERN_STATE'
        do_daily_pvp=True,  # Whether to auto a PVP match (you may win, who knows 🤷‍♂️)
    )


if __name__ == "__main__":

    main()
