import utilities.vision_images as vio
from utilities.utilities import (
    capture_hand_image,
    capture_window,
    click_and_drag,
    crop_image,
    determine_card_merge,
    determine_relative_coordinates,
    display_image,
    get_hand_cards,
    screenshot_testing,
)


def development():
    """Some development function calls"""

    # determine_relative_coordinates(capture_window()[0])
    screenshot_testing(vision_image=vio.phase_4, threshold=0.8)

    # cards = get_hand_cards()
    # for i, card in enumerate(cards, start=0):
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

    # determine_relative_coordinates(capture_hand_image)

    # _, window_location = capture_window()
    # start_drag = (window_location[0] + 280, window_location[1] + 810)
    # end_drag = (window_location[0] + 280, window_location[1] + 550)
    # click_and_drag(start_drag[0], start_drag[1], end_drag[0], end_drag[1], sleep_after_click=0.01, drag_duration=0.5)

    return


if __name__ == "__main__":
    development()
