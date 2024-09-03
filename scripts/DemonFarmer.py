import utilities.vision_images as vio
from utilities.demon_farming_logic import DemonFarmer, States
from utilities.farming_factory import FarmingFactory


def main():

    FarmingFactory.main_loop(
        farmer=DemonFarmer,
        battle_strategy=None,  # The demon fights don't require an AI
        starting_state=States.GOING_TO_DEMONS,  # Should be 'GOING_TO_DEMONS'
        demon_to_farm=vio.og,  # Accepts: 'vio.og', 'vio.bell'
    )


if __name__ == "__main__":

    main()
