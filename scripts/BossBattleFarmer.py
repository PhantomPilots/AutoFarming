from utilities.farming_factory import FarmingFactory
from utilities.boss_battle_farming_logic import BossBattleFarmer, States


def main():
    FarmingFactory.main_loop(
        farmer=BossBattleFarmer,
        starting_state=States.GOING_TO_DUNGEON
    )


if __name__ == "__main__":

    main()
