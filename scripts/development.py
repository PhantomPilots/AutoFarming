import time

import cv2
import numpy as np
import pyautogui
import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter
from utilities.card_data import CardTypes
from utilities.coordinates import Coordinates
from utilities.dogs_fighter import DogsFighter
from utilities.utilities import (
    capture_hand_image,
    capture_screen,
    capture_window,
    click_and_drag,
    close_game,
    crop_image,
    determine_card_merge,
    determine_relative_coordinates,
    display_image,
    find,
    find_and_click,
    get_card_interior_image,
    get_card_slot_region_image,
    get_card_type_image,
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
    screenshot_testing(screenshot, vision_image=vio.annoying_chat_popup, threshold=0.75)

    # if find(vio.connection_confrm_expired, screenshot):
    #     close_game()
    # if find_and_click(vio.password, screenshot, window_location):
    #     close_game()

    # full_screenshot = capture_screen()
    # screenshot_testing(full_screenshot, vio.server_cancel)

    # determine_relative_coordinates(screenshot)

    # available_slots = BirdFighter.count_empty_card_slots(screenshot)
    # print(f"These many empty slots: {available_slots}")

    # while True:
    #     screenshot, _ = capture_window()
    #     DogsFighter.count_empty_card_slots(screenshot, threshold=0.6, plot=True)
    #     time.sleep(0.5)

    # # Get card slots image
    # card_slots = get_card_slot_region_image(screenshot)
    # display_image(card_slots)

    # # Test the 'move to location'
    # move_to_location(Coordinates.get_coordinates("fifth_slot"), window_location)
    # screenshot, window_location = capture_window()
    # # display_image(screenshot)
    # screenshot_testing(vision_image=vio.card_slot, threshold=0.9)

    # print(f"We have {count_empty_card_slots_2()} empty card slots")

    # hand_image = capture_hand_image()
    # display_image(hand_image)
    # empty_slots = count_empty_card_slots(screenshot)
    # print("We have these many empty slots:", empty_slots)

    # cards = get_hand_cards(num_units=3)
    # for i, card in enumerate(cards, start=0):
    #     card_interior = get_card_type_image(card.card_image, num_units=3)

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
