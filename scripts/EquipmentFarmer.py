from utilities.equipment_farming_logic import EquipmentFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=EquipmentFarmer,
        starting_state=States.FARMING,  # Should be 'FARMING'
    )


if __name__ == "__main__":

    main()
