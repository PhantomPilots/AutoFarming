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
from utilities.dogs_floor4_fighter_whale import DogsFloor4FighterWhale
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
        extra_clears: int = 0,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.hraesvelgr,
            extra_mode_source_image=vio.wind_source,
            do_dailies=do_dailies,
            password=password,
            extra_clears=extra_clears,
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
        extra_clears: int = 0,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.eikthyrnir,
            extra_mode_source_image=vio.river_source,
            do_dailies=do_dailies,
            password=password,
            extra_clears=extra_clears,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete
        self.fighter: IFighter = DeerFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
            whale=whale,
        )


class DogsFloor4Farmer(IFloor4Farmer):

    whale = False
    lillia_in_team = False
    roxy_in_team = False
    meli3k_in_team = False
    bluegow_in_team = False

    def __init__(
        self,
        battle_strategy: type[DogsFloor4BattleStrategy],
        starting_state: States,
        max_runs="inf",
        do_dailies=False,
        password: str | None = None,
        *,
        whale: bool = False,
        extra_clears: int = 0,
    ):

        super().__init__(
            battle_strategy=battle_strategy,
            starting_state=starting_state,
            max_runs=max_runs,
            demonic_beast_image=vio.skollandhati,
            extra_mode_source_image=vio.twilight_source,
            do_dailies=do_dailies,
            password=password,
            extra_clears=extra_clears,
        )

        DogsFloor4Farmer.whale = whale
        DogsFloor4Farmer.lillia_in_team = False
        DogsFloor4Farmer.roxy_in_team = False
        DogsFloor4Farmer.meli3k_in_team = False
        DogsFloor4Farmer.bluegow_in_team = False
        self._missing_whale_team_warning_printed = False
        self._whale_team_confirmed = False

        fighter_cls = DogsFloor4FighterWhale if whale else DogsFloor4Fighter
        self.fighter: IFighter = fighter_cls(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def on_ready_to_fight_before_start(self, screenshot):
        if DogsFloor4Farmer.whale:
            if self._whale_team_confirmed:
                return True
            DogsFloor4Farmer.meli3k_in_team = find(vio.meli3k_in_team, screenshot)
            DogsFloor4Farmer.bluegow_in_team = find(vio.bluegow_in_team, screenshot)
            if DogsFloor4Farmer.meli3k_in_team:
                print("Meli3k is in the team!")
            if DogsFloor4Farmer.bluegow_in_team:
                print("Blue Gowther is in the team!")
            if DogsFloor4Farmer.meli3k_in_team and DogsFloor4Farmer.bluegow_in_team:
                self._missing_whale_team_warning_printed = False
                self._whale_team_confirmed = True
                return True
            print(
                "Please make sure both OG Blue Gowther and Meliodas 3k (Demon King) "
                "are in the team before starting the fight"
            )
            self.current_state = States.EXIT_FARMER
            return False

        if find(vio.lillia_in_team, screenshot):
            print("Lillia is in the team!")
            DogsFloor4Farmer.lillia_in_team = True
        elif find(vio.roxy_in_team, screenshot):
            print("Roxy is in the team!")
            DogsFloor4Farmer.roxy_in_team = True
        return True

    def get_fighter_run_kwargs(self) -> dict:
        if DogsFloor4Farmer.whale:
            return {
                "meli3k_in_team": DogsFloor4Farmer.meli3k_in_team,
                "bluegow_in_team": DogsFloor4Farmer.bluegow_in_team,
            }
        return {
            "lillia_in_team": DogsFloor4Farmer.lillia_in_team,
            "roxy_in_team": DogsFloor4Farmer.roxy_in_team,
        }




