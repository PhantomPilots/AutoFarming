import argparse

import utilities.vision_images as vio
from utilities.demon_farming_logic import DemonFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument(
        "--indura-diff",
        "-d",
        type=str,
        choices=["extreme", "hell", "chaos"],
        default="chaos",
        help="Difficulty for Indura demon (choices: extreme, hell, chaos)",
    )
    parser.add_argument(
        "--demons-to-farm",
        type=str,
        default="indura_demon",
        help="Comma-separated list of demons to farm: red_demon,gray_demon,crimson_demon,bell_demon,og_demon,indura_demon",
    )
    parser.add_argument(
        "--time-to-sleep",
        type=float,
        default=9.1,
        help="Seconds to sleep before accepting an invitation (default: 9.1)",
    )
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    args = parser.parse_args()

    demon_map = {
        "indura_demon": vio.indura_demon,
        "og_demon": vio.og_demon,
        "bell_demon": vio.bell_demon,
        "red_demon": vio.red_demon,
        "gray_demon": vio.gray_demon,
        "crimson_demon": vio.crimson_demon,
    }
    demons_to_farm = [
        demon_map[name.strip()] for name in args.demons_to_farm.split(",") if name.strip() in demon_map
    ] or [vio.indura_demon]

    FarmingFactory.main_loop(
        farmer=DemonFarmer,
        starting_state=States.GOING_TO_DEMONS,
        demons_to_farm=demons_to_farm,
        indura_difficulty=args.indura_diff,
        time_to_sleep=args.time_to_sleep,
        time_between_demons=2,
        do_dailies=args.do_dailies,
        do_daily_pvp=True,
        password=args.password,
    )


if __name__ == "__main__":

    main()
