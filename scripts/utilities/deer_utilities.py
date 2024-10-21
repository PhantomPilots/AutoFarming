import utilities.vision_images as vio
from utilities.card_data import Card
from utilities.utilities import find


def is_red_card(card: Card) -> bool:
    return find(vio.lv_st, card.card_image) or find(vio.lv_aoe, card.card_image) or find(vio.lv_ult, card.card_image)


def is_green_card(card: Card) -> bool:
    return (
        find(vio.jorm_1, card.card_image)
        or find(vio.jorm_2, card.card_image)
        or find(vio.jorm_ult, card.card_image)
        or find(vio.escanor_st, card.card_image)
        or find(vio.escanor_aoe, card.card_image)
        or find(vio.escanor_ult, card.card_image)
    )


def is_blue_card(card: Card) -> bool:
    return (
        find(vio.roxy_st, card.card_image) or find(vio.roxy_aoe, card.card_image) or find(vio.roxy_ult, card.card_image)
    )
