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
from utilities.dogs_floor4_fighter import DogsFloor4Fighter
from utilities.dogs_floor4_fighting_strategies import DogsFloor4BattleStrategy
from utilities.fighting_strategies import IBattleStrategy
from utilities.floor_4_farming_logic import IFloor4Farmer, States
from utilities.utilities import find


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
        *,
        whale: bool = False,
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
            whale=whale,
        )


class DogsFloor4Farmer(IFloor4Farmer):

    lillia_in_team = False
    roxy_in_team = False

    def __init__(
        self,
        battle_strategy: type[DogsFloor4BattleStrategy],
        starting_state: States,
        max_runs="inf",
        do_dailies=False,
        password: str | None = None,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.skollandhati,
            do_dailies=do_dailies,
            password=password,
        )

        self.fighter: IFighter = DogsFloor4Fighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def on_ready_to_fight_before_start(self, screenshot):
        if find(vio.lillia_in_team, screenshot):
            print("Lillia is in the team!")
            DogsFloor4Farmer.lillia_in_team = True
        elif find(vio.roxy_in_team, screenshot):
            print("Roxy is in the team!")
            DogsFloor4Farmer.roxy_in_team = True

    def get_fighter_run_kwargs(self) -> dict:
        return {
            "lillia_in_team": DogsFloor4Farmer.lillia_in_team,
            "roxy_in_team": DogsFloor4Farmer.roxy_in_team,
        }
