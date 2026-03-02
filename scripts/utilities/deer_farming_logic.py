import threading

import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.card_data import CardColors
from utilities.deer_fighter import DeerFighter, IFighter
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, determine_unit_types, find, find_and_click

logger = LoggerWrapper("DeerLogger", log_file="deer_logger.log")


class DeerFarmer(DemonicBeastFarmer):

    unit_colors: list[CardColors] = []

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        max_floor_3_clears="inf",
        reset_after_defeat=False,
        logger=logger,
        password: str | None = None,
        do_dailies=False,
    ):

        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_floor_3_clears=max_floor_3_clears,
            reset_after_defeat=reset_after_defeat,
            demonic_beast_image=vio.eikthyrnir,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        self.fighter: IFighter = DeerFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def proceed_to_floor_state(self):
        """Detect unit colors right before we press start (once per session)."""
        screenshot, _ = capture_window()
        if find(vio.startbutton, screenshot) and not DeerFarmer.unit_colors:
            DeerFarmer.unit_colors = determine_unit_types()
            print(f"[DeerFarmer] Stored unit types: {[c.name for c in DeerFarmer.unit_colors]}")
        super().proceed_to_floor_state()

    def fighting_floor(self):
        """Override to pass unit_colors to the fighter thread."""
        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location, threshold=0.6)
        find_and_click(vio.close, screenshot, window_location, threshold=0.8)
        find_and_click(vio.first_reward, screenshot, window_location)

        if (self.fight_thread is None or not self.fight_thread.is_alive()) and (
            self.current_state == States.FIGHTING_FLOOR
        ):
            self.fight_thread = threading.Thread(
                target=self.fighter.run,
                daemon=True,
                args=(DemonicBeastFarmer.current_floor,),
                kwargs={"unit_colors": DeerFarmer.unit_colors},
            )
            self.fight_thread.start()
            print("DemonicBeast fighter started!")

        if find(vio.available_floor, screenshot, threshold=0.9):
            print("We finished the fight but are still fighting? Get outta here!")
            self.stop_fighter_thread()
            self.current_state = States.READY_TO_FIGHT
