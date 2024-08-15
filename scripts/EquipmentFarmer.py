from utilities.equipment_farming_logic import EquipmentFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=EquipmentFarmer,
        battle_strategy=None,  # Equipment farming uses 'auto' fighting, no need for a custom AI fighter
        starting_state=States.TAVERN_TO_FARM,  # Should be 'TAVERN_TO_FARM'
    )


if __name__ == "__main__":

    main()
