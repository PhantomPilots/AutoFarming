from typing import Callable

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import find


def is_shock_card(card: Card):
    return find(vio.val_shock, card.card_image)


def is_bleed_card(card: Card):
    return find(vio.jorm_bleed, card.card_image)


def is_poison_card(card: Card):
    return find(vio.val_poison, card.card_image) or find(vio.val_ult, card.card_image)
