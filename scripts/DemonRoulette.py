import utilities.vision_images as vio
from utilities.demon_farming_logic import DemonRouletteFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DemonRouletteFarmer,
        starting_state=States.GOING_TO_DEMONS,  # Should be 'GOING_TO_DEMONS'
        # Accepts: 'vio.og_demon', 'vio.bell_demon', 'vio.red_demon', 'vio.gray_demon', 'vio.crimson_demon'
        demons_to_farm=[
            vio.red_demon,
            vio.gray_demon,
            vio.crimson_demon,
            vio.bell_demon,
            vio.og_demon,
        ],
        time_to_sleep=9.3,  # How many seconds to sleep before accepting an invitation
        time_between_demons=1,  # How many hours before switching to next demon
        do_dailies=False,  # Do we halt demon farming to do dailies?
        do_daily_pvp=False,  # If we do dailies, do we do PVP?
    )


if __name__ == "__main__":

    main()
