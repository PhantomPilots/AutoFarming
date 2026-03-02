import threading

import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter, IFighter
from utilities.card_data import CardColors
from utilities.deer_fighter import DeerFighter
from utilities.fighting_strategies import IBattleStrategy
from utilities.floor_4_farming_logic import IFloor4Farmer, States
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import capture_window, determine_unit_types, find, find_and_click


class BirdFloor4Farmer(IFloor4Farmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state: States,
        max_runs="inf",
        do_dailies=False,
        password: str | None = None,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.hraesvelgr,
            do_dailies=do_dailies,
            password=password,
        )

        self.fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )


class DeerFloor4Farmer(IFloor4Farmer):

    unit_colors: list[CardColors] = []

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state: States,
        max_runs="inf",
        do_dailies=False,
        password: str | None = None,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.eikthyrnir,
            do_dailies=do_dailies,
            password=password,
        )

        self.fighter: IFighter = DeerFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def ready_to_fight_state(self):
        """Detect unit colors once before we press start."""
        screenshot, _ = capture_window()
        if find(vio.startbutton, screenshot) and not DeerFloor4Farmer.unit_colors:
            DeerFloor4Farmer.unit_colors = determine_unit_types()
            print(f"[DeerFloor4Farmer] Stored unit types: {[c.name for c in DeerFloor4Farmer.unit_colors]}")
        super().ready_to_fight_state()

    def fighting_state(self):
        """Override to pass unit_colors to the fighter thread."""
        screenshot, window_location = capture_window()

        find_and_click(vio.skip_bird, screenshot, window_location)

        if (self.fight_thread is None or not self.fight_thread.is_alive()) and self.current_state == States.FIGHTING:
            print("Floor4 fight started!")
            self.fight_thread = threading.Thread(
                target=self.fighter.run,
                name="Floor4FighterThread",
                daemon=True,
                kwargs={"unit_colors": DeerFloor4Farmer.unit_colors},
            )
            self.fight_thread.start()

        if find(vio.floor_3_cleared_db, screenshot):
            print("We finished the fight but are still fighting? Get outta here!")
            self.stop_fighter_thread()
            self.current_state = States.PROCEED_TO_FLOOR
