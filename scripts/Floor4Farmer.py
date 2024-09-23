from utilities.bird_floor4_fighting_strategies import Floor4BattleStrategy
from utilities.farming_factory import FarmingFactory
from utilities.floor_4_farming_logic import Floor4Farmer, States


def main():

    FarmingFactory.main_loop(
        farmer=Floor4Farmer,
        battle_strategy=Floor4BattleStrategy,  # The AI. Floor 4 requires a very specific logic
        starting_state=States.FIGHTING,  # Should be 'GOING_TO_FLOOR' or 'FIGHTING', to start the script from outside or within the fight
    )


if __name__ == "__main__":

    main()
