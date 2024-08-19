from dataclasses import dataclass
from enum import Enum

import numpy as np


class CardTypes(Enum):
    ATTACK = 0
    STANCE = 1
    RECOVERY = 2
    ATTACK_DEBUFF = 3
    DEBUFF = 4
    BUFF = 5
    ULTIMATE = -1  # How to properly identify ultimate cards? The "default" class?
    DISABLED = 9  # Group all cards that are disabled together -- since they are grayed out, the median color should be very close
    GROUND = 10  # If some units die, their card spaces are empty ground!
    NONE = -100


class CardRanks(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    NONE = -100


@dataclass
class Card:
    card_type: CardTypes  # From above
    rectangle: tuple[float, float, float, float]  # window values: [x,y,w,h]
    card_image: np.ndarray  # The card image itself
    card_rank: CardRanks = CardRanks.NONE  # From above
