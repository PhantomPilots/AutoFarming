import argparse

from utilities.demonic_beast_farming_logic import States
from utilities.demonic_beast_rotation_farming_logic import DemonicBeastRotationFarmer
from utilities.farming_factory import FarmingFactory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    parser.add_argument(
        "--beasts-to-farm",
        type=str,
        nargs="+",
        choices=["bird", "deer", "dogs"],
        default=["bird", "deer", "dogs"],
        help="List of Demonic Beasts to run floors 1-3 once each.",
    )
    parser.add_argument("--do-dailies", action="store_true", default=False, help="Do dailies (default: False)")
    parser.add_argument(
        "--daily-pvp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Do daily PVP when dailies run (default: True)",
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    FarmingFactory.main_loop(
        farmer=DemonicBeastRotationFarmer,
        starting_state=States.GOING_TO_DB,
        beasts_to_farm=args.beasts_to_farm,
        password=args.password,
        do_dailies=args.do_dailies,
        do_daily_pvp=args.daily_pvp,
    )


if __name__ == "__main__":
    main()
