import time

import pyautogui as pyautogui
import tqdm

# Import all images
import utilities.vision_images as vio
from utilities.deer_fighter import DeerFighter, IFighter
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper

logger = LoggerWrapper("DeerLogger", log_file="deer_logger.log")


class DeerFarmer(DemonicBeastFarmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        max_floor_3_clears="inf",
        reset_after_defeat=False,
        logger=logger,
        password: str | None = None,
    ):

        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_floor_3_clears=max_floor_3_clears,
            reset_after_defeat=reset_after_defeat,
            demonic_beast_image=vio.eikthyrnir,
            logger=logger,
            password=password,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        self.fighter: IFighter = DeerFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )
