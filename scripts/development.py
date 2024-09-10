import numpy as np
import pyautogui
import utilities.vision_images as vio
from utilities.card_data import CardTypes
from utilities.coordinates import Coordinates
from utilities.dogs_fighter import DogsFighter
from utilities.utilities import (
    capture_hand_image,
    capture_window,
    click_and_drag,
    crop_image,
    determine_card_merge,
    determine_relative_coordinates,
    display_image,
    find,
    get_hand_cards,
    is_amplify_card,
    is_Meli_card,
    move_to_location,
    screenshot_testing,
)


def development():
    """Some development function calls"""
    screenshot, window_location = capture_window()
    print("Screenshot shape:", screenshot.shape)
    # display_image(screenshot)

    screenshot_testing(vision_image=vio.ok_button, threshold=0.8)

    # DogsFighter.count_empty_card_slots(screenshot, threshold=0.7)

    # # Test the 'move to location'
    # move_to_location(Coordinates.get_coordinates("fifth_slot"), window_location)
    # screenshot, window_location = capture_window()
    # # display_image(screenshot)
    # screenshot_testing(vision_image=vio.card_slot, threshold=0.9)

    # print(f"We have {count_empty_card_slots_2()} empty card slots")

    # determine_relative_coordinates(screenshot)

    # hand_image = capture_hand_image()
    # empty_slots = count_empty_card_slots(screenshot)
    # print("We have these many empty slots:", empty_slots)

    # cards = get_hand_cards()
    # for i, card in enumerate(cards, start=0):
    #     print(f"Is {card.card_type.name} Meli's?", is_Meli_card(card))
    #     print(card.card_type.name, card.card_rank.name)

    #     # print(card.card_image.shape)

    #     # border = 8
    #     # new_image = crop_image(
    #     #     card.card_image,
    #     #     (border, border + 4),
    #     #     (card.card_image.shape[1] - border, card.card_image.shape[0] - border - 12),
    #     # )
    #     # display_image(new_image)

    #     if i > 0 and i < len(cards) - 1 and determine_card_merge(cards[i - 1], cards[i + 1]):
    #         print("Card generates a merge!")
    #         display_image(card.card_image)

    # determine_relative_coordinates(screenshot)

    # _, window_location = capture_window()
    # start_drag = (window_location[0] + 280, window_location[1] + 810)
    # end_drag = (window_location[0] + 280, window_location[1] + 550)
    # click_and_drag(start_drag[0], start_drag[1], end_drag[0], end_drag[1], sleep_after_click=0.01, drag_duration=0.5)

    return


if __name__ == "__main__":
    development()
