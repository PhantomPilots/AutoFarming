from typing import Callable

import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.utilities import find

# TODO Add cards from new team


def is_red_card(card: Card) -> bool:
    return card.card_type != CardTypes.DISABLED and (
        find(vio.lv_st, card.card_image)
        or find(vio.lv_aoe, card.card_image)
        or find(vio.lv_ult, card.card_image)
        or find(vio.freyr_2, card.card_image)
        or find(vio.freyr_1, card.card_image)
        or find(vio.freyr_ult, card.card_image)
        or find(vio.meg_1, card.card_image)
        or find(vio.meg_ult, card.card_image)
    )


def is_green_card(card: Card) -> bool:
    return card.card_type != CardTypes.DISABLED and (
        find(vio.lolimerl_st, card.card_image)
        or find(vio.lolimerl_aoe, card.card_image)
        or find(vio.lolimerl_ult, card.card_image)
        or find(vio.jorm_1, card.card_image)
        or find(vio.jorm_2, card.card_image)
        or find(vio.jorm_ult, card.card_image)
        or find(vio.escanor_st, card.card_image)
        or find(vio.escanor_aoe, card.card_image)
        or find(vio.escanor_ult, card.card_image)
        or find(vio.hel_1, card.card_image)
        or find(vio.hel_2, card.card_image)
        or find(vio.hel_ult, card.card_image)
        or find(vio.tyr_1, card.card_image)
        or find(vio.tyr_2, card.card_image)
        or find(vio.tyr_ult, card.card_image)
    )


def is_blue_card(card: Card) -> bool:
    return card.card_type != CardTypes.DISABLED and (
        find(vio.albedo_1, card.card_image)
        or find(vio.albedo_ult, card.card_image)
        or find(vio.roxy_st, card.card_image)
        or find(vio.roxy_aoe, card.card_image)
        or find(vio.roxy_ult, card.card_image)
        or find(vio.thor_1, card.card_image)
        or find(vio.thor_2, card.card_image)
        or find(vio.thor_ult, card.card_image)
    )


def is_Hel_card(card: Card) -> bool:
    return find(vio.hel_1, card.card_image) or find(vio.hel_2, card.card_image) or find(vio.hel_ult, card.card_image)


def is_Freyr_card(card: Card) -> bool:
    return (
        find(vio.freyr_1, card.card_image) or find(vio.freyr_2, card.card_image) or find(vio.freyr_ult, card.card_image)
    )


def is_Jorm_card(card: Card) -> bool:
    return find(vio.jorm_1, card.card_image) or find(vio.jorm_2, card.card_image) or find(vio.jorm_ult, card.card_image)


def is_Tyr_card(card: Card) -> bool:
    return find(vio.tyr_1, card.card_image) or find(vio.tyr_2, card.card_image) or find(vio.tyr_ult, card.card_image)


# Helper to check for multiple cards of a type
def count_cards(hand_of_cards: list[Card], check_func: Callable[[Card], bool]) -> int:
    """Expects `check_func` to return a `bool`"""
    return sum(check_func(card) for card in hand_of_cards)


def is_Thor_card(card: Card) -> bool:
    return find(vio.thor_1, card.card_image) or find(vio.thor_2, card.card_image) or find(vio.thor_ult, card.card_image)


def is_buff_removal_card(card: Card):
    """Whether this is Jorm's or Tyr's buff removal card"""
    return find(vio.jorm_2, card.card_image) or find(vio.tyr_1, card.card_image) or find(vio.tyr_2, card.card_image)


def reorder_buff_removal_card(hand_of_cards: list[Card], green_card_ids: list[int]) -> list[int]:
    """Place the buff removal card at the beginning of the list"""

    # Add the buff removal ID to the beginning of the list
    buff_removal_ids = np.where([is_buff_removal_card(hand_of_cards[idx]) for idx in green_card_ids])[0]
    if len(buff_removal_ids):
        # print("Setting lowest priority to buff removal card")
        green_card_ids = np.concatenate(
            ([green_card_ids[buff_removal_ids[0]]], np.delete(green_card_ids, buff_removal_ids[0]))
        )

    return green_card_ids


def reorder_jorms_heal(hand_of_cards: list[Card], green_card_ids: list[int]) -> list[Card]:
    """Place the buff removal card at the beginning of the list, so that we pick it."""

    # Add the buff removal ID to the beginning of the list
    card_ranks = [card.card_rank.value for card in hand_of_cards]
    heal_ids = sorted(
        np.where([find(vio.jorm_1, hand_of_cards[idx].card_image) for idx in green_card_ids])[0],
        key=lambda idx: card_ranks[idx],
    )
    if len(heal_ids):
        green_card_ids = np.concatenate(([green_card_ids[heal_ids[-1]]], np.delete(green_card_ids, heal_ids[-1])))

    return green_card_ids


def has_ult(unit: str, hand_of_cards: list[Card]) -> bool:
    """Returns if said unit has the ult enabled"""
    ult_img = getattr(vio, f"{unit}_ult")
    return next((True for card in hand_of_cards if find(ult_img, card.card_image)), False)
