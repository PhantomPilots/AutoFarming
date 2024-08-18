from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import (
    DummyBattleStrategy,
    Floor4BattleStrategy,
    SmarterBattleStrategy,
)
from utilities.floor_4_farming_logic import Floor4Farmer, States


def main():

    FarmingFactory.main_loop(
        farmer=Floor4Farmer,
        battle_strategy=Floor4BattleStrategy,  # The AI. Floor 4 requires a very specific logic
        starting_state=States.FIGHTING,  # Should be 'GOING_TO_FLOOR'
    )


if __name__ == "__main__":

    main()
