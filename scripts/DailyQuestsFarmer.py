import argparse

from utilities.daily_farming_logic import States as DailyStates
from utilities.farming_factory import FarmingFactory
from utilities.general_farmer_interface import IFarmer
from utilities.general_farmer_interface import States as GlobalStates


class StandaloneDailyFarmer(IFarmer):
    def __init__(
        self,
        *,
        starting_state=GlobalStates.DAILIES_STATE,
        battle_strategy=None,
        password: str | None = None,
        do_daily_pvp=True,
        **kwargs,
    ):
        del battle_strategy, kwargs
        super().__init__(do_daily_pvp=do_daily_pvp)

        self.current_state = starting_state
        IFarmer.do_dailies = True

        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")

        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

    def dailies_complete_callback(self):
        """Exit after completion, unless the daily thread stopped for login recovery."""
        with IFarmer._lock:
            IFarmer.dailies_thread = None
            if IFarmer.doing_dailies or IFarmer.daily_farmer.manual_kill:
                return
            self.current_state = DailyStates.EXIT_FARMER

    def run(self):
        self.run_state_loop(
            {DailyStates.EXIT_FARMER: self.exit_farmer_state},
            login_return_state=GlobalStates.DAILIES_STATE,
        )


def main():
    parser = argparse.ArgumentParser(description="Run standalone daily quest automation.")
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP while running daily quests (default: True)",
    )
    parser.add_argument(
        "--do-daily-pvp",
        dest="daily_pvp",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=StandaloneDailyFarmer,
        starting_state=GlobalStates.DAILIES_STATE,
        password=args.password,
        do_daily_pvp=args.daily_pvp,  # Whether to auto a PVP match (you may win, who knows 🤷‍♂️)
    )


if __name__ == "__main__":

    main()
