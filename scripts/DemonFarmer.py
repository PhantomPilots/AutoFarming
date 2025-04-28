import argparse

import utilities.vision_images as vio
from utilities.demon_farming_logic import DemonFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=DemonFarmer,
        starting_state=States.FIGHTING_DEMON,  # Should be 'GOING_TO_DEMONS'
        demons_to_farm=[
            # vio.red_demon,
            # vio.gray_demon,
            # vio.crimson_demon,
            # vio.bell_demon,
            # vio.og_demon,
            vio.indura_demon,
        ],
        time_to_sleep=9.25,  # How many seconds to sleep before accepting an invitation
        time_between_demons=2,  # How many hours between each type of demon
        do_dailies=True,  # Do we halt demon farming to do dailies?
        do_daily_pvp=True,  # If we do dailies, do we do PVP?
        password=args.password,  # Account password
    )


if __name__ == "__main__":

    main()
