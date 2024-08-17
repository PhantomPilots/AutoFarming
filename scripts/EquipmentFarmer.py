import utilities.vision_images as vio
from utilities.equipment_farming_logic import EquipmentFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.utilities import (
    determine_relative_coordinates,
    press_key,
    screenshot_testing,
)


def main():

    FarmingFactory.main_loop(
        farmer=EquipmentFarmer,
        battle_strategy=None,  # Equipment farming uses 'auto' fighting, no need for a custom AI fighter
        starting_state=States.FARMING,  # Should be 'TAVERN_TO_FARM'
    )


if __name__ == "__main__":

    ## The two lines below are for development purposes, don't uncomment
    # determine_relative_coordinates()
    # screenshot_testing(vision_image=vio.auto_repeat_ended, threshold=0.8)

    main()
