import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.snake_fighter import IFighter, SnakeFighter

logger = LoggerWrapper("SnakeLogger", log_file="snake_logger.log")


class SnakeFarmer(DemonicBeastFarmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        max_floor_3_clears="inf",
        reset_after_defeat=False,
        logger=logger,
    ):

        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_floor_3_clears=max_floor_3_clears,
            reset_after_defeat=reset_after_defeat,
            demonic_beast_image=vio.nidhoggr,
            logger=logger,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        # Using the previous BirdFighter!
        self.fighter: IFighter = SnakeFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    @property
    def fighter(self):
        return self.__fighter

    @fighter.setter
    def fighter(self, value: IFighter):
        self.__fighter = value
