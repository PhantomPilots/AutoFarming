import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
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


# Helper to check for multiple cards of a type
def count_cards(hand_of_cards: list[Card], check_func) -> int:
    """Expects `check_func` to return a `bool`"""
    return sum(bool(check_func(card)) for card in hand_of_cards)
