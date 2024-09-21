import threading
import time
from enum import Enum

import pyautogui as pyautogui

# Import all images
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.snake_fighter import DogsFighter, IFighter
from utilities.utilities import (
    capture_window,
    check_for_reconnect,
    find,
    find_and_click,
    find_floor_coordinates,
)

logger = LoggerWrapper("SnakeLogger", log_file="snake_logger.log")


class States(Enum):
    GOING_TO_SNAKE = 0
    SET_PARTY = 1
    READY_TO_FIGHT = 2
    FIGHTING_FLOOR = 3
    RESETTING_DOGS = 4


class SnakeFarmer(IFarmer):
    pass
