from dataclasses import dataclass, field
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
    ULTIMATE = 100


class CardColors(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
    LIGHT = 4
    DARK = 5
    NONE = -1


@dataclass
class Card:
    card_type: CardTypes = CardTypes.NONE  # From above
    rectangle: tuple[float, float, float, float] = field(default_factory=list)  # window values: [x,y,w,h]
    card_image: np.ndarray | None = None  # The card image itself
    card_rank: CardRanks = CardRanks.NONE  # From above
    card_color: CardColors = CardColors.NONE
