import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter, IFighter
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper

logger = LoggerWrapper(name="BirdLogger", log_file="bird_logger.log")


class BirdFarmer(DemonicBeastFarmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        num_floor_3_clears="inf",
        logger=logger,
        password: str | None = None,
        do_dailies=False,
    ):
        super().__init__(
            starting_state=starting_state,
            max_floor_3_clears=num_floor_3_clears,
            demonic_beast_image=vio.hraesvelgr,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        self.fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )
