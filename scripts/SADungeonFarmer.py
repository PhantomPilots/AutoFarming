from utilities.farming_factory import FarmingFactory
from utilities.sa_dungeon_farming_logic import SADungeonFarmer, States


def main():

    FarmingFactory.main_loop(
        farmer=SADungeonFarmer,
        starting_state=States.GOING_TO_DUNGEON,
    )


if __name__ == "__main__":

    main()
