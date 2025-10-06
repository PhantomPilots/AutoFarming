import sys
import threading
import time
from datetime import datetime
from enum import Enum, auto

import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import (
    CHECK_IN_HOUR,
    MINUTES_TO_WAIT_BEFORE_LOGIN,
    PACIFIC_TIMEZONE,
    IFarmer,
)
from utilities.general_farmer_interface import States as GlobalStates
from utilities.general_fighter_interface import IBattleStrategy, IFighter
from utilities.indura_fighter import InduraFighter
from utilities.indura_fighting_strategies import InduraBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    click_and_sleep,
    crop_image,
    display_image,
    find,
    find_and_click,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="GuildBossLogger", log_to_file=False)


class States(Enum):
    GOING_TO_GB = auto()
    FIGHTING = auto()


class GuildBossFarmer(IFarmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,  # No need
        starting_state=States.GOING_TO_GB,
    ):
        super().__init__()

    def going_to_gb_state(self):
        screenshot, window_location = capture_window()

    def fighting(self):
        screenshot, window_location = capture_window()

    def run(self):

        print("[WARN] Guild Boss farmer not implemented yet, try again soon.")
        sys.exit(1)

        while True:
            # Try to reconnect first
            if not (success := check_for_reconnect()):
                # We had to restart the game! Let's log back in immediately
                print("Let's try to log back in immediately...")
                IFarmer.first_login = True

            if self.current_state == States.GOING_TO_GB:
                self.going_to_gb_state()

            elif self.current_state == States.FIGHTING:
                self.fighting()

            # We need the loop to run very fast
            time.sleep(0.7)
