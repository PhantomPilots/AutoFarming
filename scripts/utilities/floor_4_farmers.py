import os
import sys
import threading
import time
from collections import defaultdict
from enum import Enum

import pyautogui as pyautogui
import tqdm

# Import all images
import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter, IFighter
from utilities.deer_fighter import DeerFighter
from utilities.fighting_strategies import IBattleStrategy
from utilities.floor_4_farming_logic import IFloor4Farmer, States


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

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete
        self.fighter: IFighter = BirdFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )


class DeerFloor4Farmer(IFloor4Farmer):

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

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete
        self.fighter: IFighter = DeerFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )
