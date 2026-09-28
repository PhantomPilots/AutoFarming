import numpy as np
import utilities.vision_images as vio
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.rat_fighter import IFighter, RatFighter

logger = LoggerWrapper(name="RatLogger", log_file="rat_logger.log")


class RatFarmer(DemonicBeastFarmer):

    cycle_length = 2

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        max_clears="inf",
        reset_after_defeat=False,
        logger=logger,
        password: str | None = None,
        do_dailies=False,
        do_daily_pvp=True,
    ):
        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_clears=max_clears,
            reset_after_defeat=reset_after_defeat,
            demonic_beast_image=vio.ratatoskr,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
            do_daily_pvp=do_daily_pvp,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        self.fighter: IFighter = RatFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def determine_db_floor(self, screenshot: np.ndarray, threshold=0.8) -> int:
        """Use the shared floor check with this farmer's matching threshold."""
        return super().determine_db_floor(screenshot, threshold=threshold)
