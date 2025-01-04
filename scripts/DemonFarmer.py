import utilities.vision_images as vio
from utilities.demon_farming_logic import DemonFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DemonFarmer,
        starting_state=States.GOING_TO_DEMONS,  # Should be 'GOING_TO_DEMONS'
        demons_to_farm=[  # Accepts: vio.red_demon, vio.gray_demon, vio.crimson_demon, vio.bell_demon, vio.og_demon
            vio.bell_demon,
            # vio.og_demon,
        ],
        time_to_sleep=9.3,  # How many seconds to sleep before accepting an invitation
        do_dailies=True,  # Do we halt demon farming to do dailies?
        do_daily_pvp=True,  # If we do dailies, do we do PVP?
    )


if __name__ == "__main__":

    main()
