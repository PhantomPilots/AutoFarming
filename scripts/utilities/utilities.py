import glob
import os
import random
import time
from numbers import Integral
from typing import Callable, Union

import cv2
import dill as pickle
import numpy as np
import pyautogui
import utilities.vision_images as vio
import win32api
import win32con
import win32gui
import win32ui
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from utilities.capture_window import (
    capture_screen,
    capture_window,
    get_window_size,
    is_7ds_window_open,
)
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.models import (
    AmplifyCardPredictor,
    CardMergePredictor,
    CardTypePredictor,
    GroundCardPredictor,
    HAMCardPredictor,
    ThorCardPredictor,
)
from utilities.vision import Vision


def draw_rectangles(
    haystack_img, rectangles: np.ndarray, line_color: tuple = (0, 255, 0), line_type=cv2.LINE_4
) -> np.ndarray:
    """Given a list of [x, y, w, h] rectangles and a canvas image to draw on, return an image with
    all of those rectangles drawn"""

    # these colors are actually BGR
    line_type = cv2.LINE_4

    # Expand to 2D if 1-dimensional
    rectangles = rectangles[None, ...] if rectangles.ndim == 1 else rectangles

    for x, y, w, h in rectangles:
        # determine the box positions
        top_left = (x, y)
        bottom_right = (x + w, y + h)
        # draw the box
        cv2.rectangle(haystack_img, top_left, bottom_right, line_color, lineType=line_type)

    return haystack_img


def screenshot_testing(screenshot: np.ndarray, vision_image: Vision, threshold=0.7, cv_method=cv2.TM_CCOEFF_NORMED):
    """Debugging function that displays a screenshot and the patterns matched for a specific `Vision` image"""

    # cv2.imshow("screenshot", screenshot)

    # rectangle = vision_image.find(screenshot, threshold=threshold)
    rectangles, _ = vision_image.find_all_rectangles(screenshot, threshold=threshold, method=cv_method)
    if rectangles.size:
        new_image = draw_rectangles(screenshot, rectangles)
        cv2.imshow("Rectangles", new_image)
        cv2.waitKey(0)

    else:
        print("No rectangles found!")

    # Simply to stop the execution of the rest of the code
    # raise ValueError("This function should only be used for testing, killing program execution.")


def count_needle_image(vio_image: Vision, screenshot: np.ndarray, threshold=0.7) -> int:
    """Count how many times a `Vision` image is found in the screenshot"""
    rectangles, _ = vio_image.find_all_rectangles(screenshot, threshold=threshold)
    return rectangles.shape[0]


def count_immortality_buffs(screenshot: np.ndarray, threshold=0.7) -> int:
    """Count how many immortaility buffs the bird has"""
    return count_needle_image(vio.immortality_buff, screenshot, threshold)


def check_for_reconnect() -> bool:
    """Return True if we can keep running, False if restart is needed."""
    screenshot, window_location = capture_window()

    if find_and_click(vio.reconnect, screenshot, window_location):
        print("Reconnecting...")
        return True

    if find_and_click(vio.restart, screenshot, window_location):
        print("No reconnection possible, restarting the game...")
        return False

    # No reconnect/restart buttons found → assume connection is fine
    return True


def check_for_window_size():
    screenshot, window_location = capture_window()


def click_event(event, x, y, flags, params):
    if event == cv2.EVENT_LBUTTONDOWN:
        # Print the local coordinates relative to the window
        print(f"Local coordinates in window: ({x}, {y})")


def determine_relative_coordinates(img: np.ndarray):
    """Gets a screenshot, and prints to the screen the local coordinates of clicked events"""

    # Display the screenshot
    cv2.imshow("Window Screenshot", img)

    # Set the mouse callback function to capture clicks
    cv2.setMouseCallback("Window Screenshot", click_event)

    # Wait for a key press indefinitely or for a specific amount of time
    cv2.waitKey(0)

    # Close the image window
    cv2.destroyAllWindows()


def clear_console():
    os.system("cls")


def get_click_point_from_rectangle(rectangle):
    """Return the middle point of the rectangle to click on"""

    x, y, w, h = rectangle
    # Determine the center position of the rectangle
    center_x = x + int(w / 2)
    center_y = y + int(h / 2)
    return [center_x, center_y]


def click_im(rectangle_or_point: Union[np.ndarray, tuple], window_location: list[float], sleep_after_click=0.01):
    """Clicks on an image using the mouse event.

    Args:
        rectangle_point (Union[list, tuple]):  Can be a list of lists containing rectangle (x,y,w,h), or a tuple of (x, y) coordinates to click on.
                                                If the first, click on the center of the rectangle.
        window_location (list[float]):          Coordinates of the top-left corner of the window; acts as an offset.
    """
    if isinstance(rectangle_or_point, (list, np.ndarray, tuple)) and len(rectangle_or_point) == 4:
        # It's a list of rectangle, get it's center point to click on
        (x, y) = get_click_point_from_rectangle(rectangle_or_point)
    else:
        # It's a hardcoded point, provided in the form of (x, y) coordinates
        (x, y) = rectangle_or_point

    (x, y) = (x + window_location[0], y + window_location[1])
    click(x, y, sleep_after_click)


def move_to_location(point: np.ndarray | tuple, window_location: list[float]):
    """Move the cursor to a location without clicking on it"""
    (x, y) = (point[0] + window_location[0], point[1] + window_location[1])
    pyautogui.moveTo(x, y)
    time.sleep(0.1)


def find(vision_image: Vision, screenshot: np.ndarray | None, threshold=0.7, method=cv2.TM_CCOEFF_NORMED) -> bool:
    """Simply return if a match is found"""
    if screenshot is None:
        return False
    rectangle = vision_image.find(screenshot, threshold=threshold, method=method)
    return bool(rectangle.size) if rectangle is not None else False


def find_and_click(
    vision_image: Vision,
    screenshot: np.ndarray,
    window_location: list[float] = (0, 0),
    threshold=0.7,
    point_coordinates: tuple[float, float] | None = None,
) -> bool:
    """Tries to find the given `vision_image` on the screenshot; if it is found, clicks on it.
    `point_coordinates` can be a tuple with the hardcoded coordinates to click on. TODO: This should be improved
    """
    rectangle = vision_image.find(screenshot, threshold=threshold)
    if rectangle.size:
        if point_coordinates:
            click_im(point_coordinates, window_location)
        else:
            # If point coordinates not provided, click on the rectangle center
            click_im(rectangle, window_location)

        print(f"Clicked on '{vision_image.image_name}'")

        time.sleep(0.5)

        return True

    return False


def click_and_sleep(
    vision_image: Vision,
    screenshot: np.ndarray,
    window_location: list[float],
    threshold=0.7,
    point_coordinates: tuple[float, float] | None = None,
    sleep_time=1,  # In seconds
) -> bool:
    """First click, then sleep for 1 sec"""
    if find_and_click(vision_image, screenshot, window_location, threshold, point_coordinates):
        time.sleep(sleep_time)
        return True
    return False


def find_floor_coordinates(screenshot: np.ndarray, window_location):
    """Given a screenshot of the DB screen, find the coordinates of the available floor"""
    rectangle = vio.available_floor.find(screenshot, threshold=0.8)
    if rectangle.size:
        w, _ = get_window_size()

        x = w // 2  # Click on the middle with of the image...
        y = rectangle[1]  # At the same height as the arrow

        return (x, y)

    return None


def click(x, y, sleep_after_click=0.01):
    pyautogui.moveTo(x, y)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    time.sleep(sleep_after_click)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


# def click(x, y, sleep_after_click=0.01):
#     pyautogui.click(x, y)
#     time.sleep(sleep_after_click)


def rclick(x, y, sleep_after_click=0.01):
    pyautogui.moveTo(x, y)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
    time.sleep(sleep_after_click)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)


def click_and_drag(start_x, start_y, end_x, end_y, steps=100, sleep_after_click=0.01, drag_duration=0.5):
    """Move to the start position and press the left mouse button down"""
    win32api.SetCursorPos((start_x, start_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)

    # Optionally, you can sleep for a while before starting the drag
    time.sleep(sleep_after_click)

    # Calculate the distance to move in each step
    delta_x = (end_x - start_x) / steps
    delta_y = (end_y - start_y) / steps

    # Calculate the time to sleep between steps
    step_duration = drag_duration / steps

    # Move to the end position incrementally
    for step in range(steps):
        # Update cursor position by a small amount
        new_x = int(start_x + delta_x * step)
        new_y = int(start_y + delta_y * step)
        win32api.SetCursorPos((new_x, new_y))
        time.sleep(step_duration)

    # Release the left mouse button
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


def drag_im(start_point, end_point, window_location, steps=100, sleep_after_click=0.01, drag_duration=0.5):
    """Click and drag on an image given a window location"""
    global_start_point = (start_point[0] + window_location[0], start_point[1] + window_location[1])
    global_end_point = (end_point[0] + window_location[0], end_point[1] + window_location[1])
    click_and_drag(
        global_start_point[0],
        global_start_point[1],
        global_end_point[0],
        global_end_point[1],
        steps=steps,
        sleep_after_click=sleep_after_click,
        drag_duration=drag_duration,
    )


def press_key(key: str):
    print(f"Pressing key '{key}'")
    pyautogui.press(key)


def close_game():
    # Find the window by title
    hwnd = win32gui.FindWindow(None, "7DS")
    if hwnd == 0:
        print("[WARN] '7DS' window not found.")
        return

    # Bring the window to the foreground
    win32gui.SetForegroundWindow(hwnd)

    # Optional: give a moment for the window to become active
    time.sleep(0.5)

    # Send the hotkey
    pyautogui.hotkey("alt", "f4")


def close_game_if_not_in_login_screen():
    # Find the window by title
    hwnd = win32gui.FindWindow(None, "7DS")
    if hwnd == 0:
        print("[WARN] '7DS' window not found.")
        return

    # Bring the window to the foreground
    win32gui.SetForegroundWindow(hwnd)

    # Optional: give a moment for the window to become active
    time.sleep(0.5)

    screenshot, _ = capture_window()
    if not find(vio.sync_code, screenshot):
        print("Trying to close the game...")
        # Send the hotkey
        pyautogui.hotkey("alt", "f4")


def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))


def crop_image(image: np.ndarray, top_left: tuple, bottom_right: tuple) -> np.ndarray:
    """Crop an image given the top-right and bottom-left coordinates"""
    # Extract the coordinates
    x1, y1 = top_left
    x2, y2 = bottom_right

    return image[y1:y2, x1:x2]


def increment_if_condition(value: Integral | list[Integral], thresh: Integral, condition: Callable, operator=1):
    """Increments a value if it meets the given condition.

    Args:
        value (int | list[int]): The value we're trying to increment.
        thresh (int): The value that will serve as thershold to determine if we increase `value` or not.
        condition (Callable): Collable function (probably `lambda`) that specifies how to compare `value` and `thresh`.
    """
    if isinstance(value, Integral):
        return value + operator if condition(value, thresh) else value
    elif isinstance(value, list):
        return [increment_if_condition(item, thresh, condition, operator=operator) for item in value]


def increment_in_place(lst: list[Integral], thresh: Integral, condition: Callable, operator=1):
    """Increments the list in place based on the given callable condition.

    Args:
        value (int | list[int]): The value we're trying to increment.
        thresh (int): The value that will serve as thershold to determine if we increase `value` or not.
        condition (Callable): Collable function (probably `lambda`) that specifies how to compare `value` and `thresh`.
    """
    for i in range(len(lst)):
        if isinstance(lst[i], Integral) and condition(lst[i], thresh):
            lst[i] += operator
        elif isinstance(lst[i], list):
            lst[i] = increment_if_condition(lst[i], thresh, condition, operator=operator)


def capture_hand_image() -> np.ndarray:
    """Capture the hand image"""
    screenshot, _ = capture_window()

    return crop_image(
        screenshot,
        Coordinates.get_coordinates("4_cards_top_left"),
        Coordinates.get_coordinates("4_cards_bottom_right"),
    )


def capture_hand_image_3_cards() -> np.ndarray:
    """Capture the hand image"""
    screenshot, _ = capture_window()

    return crop_image(
        screenshot,
        Coordinates.get_coordinates("3_cards_top_left"),
        Coordinates.get_coordinates("3_cards_bottom_right"),
    )


def get_card_type_image(card: np.ndarray, num_units=4) -> np.ndarray:
    """Extract the card type image from the card"""
    if num_units not in [3, 4]:
        raise ValueError(f"Invalid number of units: {num_units}. Expected 3 or 4.")

    if num_units == 3:
        return get_card_type_image_3_cards(card)
    w = card.shape[-2]
    return crop_image(card, (40, 0), (w, 20))


def get_card_type_image_3_cards(card: np.ndarray) -> np.ndarray:
    """Extract the card type image from the card, when we can only use 3 cards"""
    w = card.shape[-2]
    return crop_image(card, (50, 0), (w, 18))


def get_card_interior_image(card_image: np.ndarray, num_units=4) -> np.ndarray:
    """Get the inside of the card, without the border."""
    if num_units == 4:
        border = 8
        return crop_image(
            card_image,
            (border, border + 4),
            (card_image.shape[1] - border, card_image.shape[0] - border - 12),
        )
    elif num_units == 3:
        border = 8
        return crop_image(
            card_image,
            (border, border + 4),
            (card_image.shape[1] - border - 9, card_image.shape[0] - border - 12),
        )
    else:
        raise ValueError(f"Invalid number of units: {num_units}. Expected 3 or 4.")


def get_hand_cards(num_units=4) -> list[Card]:
    """Retrieve the current cards in the hand.

    Returns:
        list[Card]:   The hand of cards. It's a list of tuples; each tuple contains the card type,
                      the `np.ndarray` card, as an image, and a tuple with the top-left coordinates of the card.
    """
    if num_units == 3:
        return get_hand_cards_3_cards()

    hand_cards = capture_hand_image()

    # Determine the width of each column
    height, width = hand_cards.shape[:2]
    column_width = int(width / 8)  # Calculate the width of each column

    # Split the image into 8 equal columns -- TODO: Not the best way to do it, doesn't work well
    house_of_cards = [
        ([61 + i * column_width, 822, column_width, height], hand_cards[:, i * column_width : (i + 1) * column_width])
        for i in range(8)
    ]

    return [Card(determine_card_type(card[-1]), *card, determine_card_rank(card[-1])) for card in house_of_cards]


def get_hand_cards_3_cards() -> list[Card]:
    """Retrieve the current cards in the hand, when we can only use 3 cards.
    TODO: Implement specific pixel coordinates/values.

    Returns:
        list[Card]:   The hand of cards. It's a list of tuples; each tuple contains the card type,
                      the `np.ndarray` card, as an image, and a tuple with the top-left coordinates of the card.
    """
    hand_cards = capture_hand_image_3_cards()

    # Determine the width of each column
    height, width = hand_cards.shape[:2]
    column_width = int(width / 7)  # Calculate the width of each column

    # Split the image into 8 equal columns -- TODO: Not the best way to do it, doesn't work well
    house_of_cards = [
        ([52 + i * column_width, 822, column_width, height], hand_cards[:, i * column_width : (i + 1) * column_width])
        for i in range(7)
    ]

    return [
        Card(determine_card_type(card[-1], three_cards=True), *card, determine_card_rank(card[-1], three_cards=True))
        for card in house_of_cards
    ]


def get_card_slot_region_image(screenshot: np.ndarray) -> np.ndarray:
    """Get the sub-image where the card slots are"""
    return crop_image(
        screenshot,
        Coordinates.get_coordinates("top_left_card_slots"),
        Coordinates.get_coordinates("bottom_right_card_slots"),
    )


def determine_card_type(card: np.ndarray | None, three_cards: bool = False) -> CardTypes:
    """Predict the card type"""

    # First, use the ground predictor. If it returns GROUND, no need to explore further
    if card is None or GroundCardPredictor.is_ground_card(
        get_card_interior_image(card, num_units=3 if three_cards else 4)
    ):
        return CardTypes.GROUND

    # If the above didn't return GROUND, explore it further. This logic allows for backwards compatibility (with Bird, for instance)
    card_type_image = get_card_type_image_3_cards(card) if three_cards else get_card_type_image(card)
    card_type = CardTypePredictor.predict_card_type(card_type_image)
    # If we predict GROUND, assume it's an ULTIMATE, therefore relying entirely on the GroundCardPredictor
    if card_type == CardTypes.GROUND:
        # print("Detecting GROUND, but setting ULTIMATE instead. Is this correct?")
        card_type = CardTypes.ULTIMATE
    return card_type


def determine_card_merge(card_1: Card | None, card_2: Card | None) -> bool:
    """Predict whether two cards are going to merge"""

    if card_1.card_type in [CardTypes.NONE, CardTypes.GROUND] or card_2.card_type in [CardTypes.NONE, CardTypes.GROUND]:
        return 0

    card_1_interior = get_card_interior_image(card_1.card_image)
    card_2_interior = get_card_interior_image(card_2.card_image)

    return (
        CardMergePredictor.predict_card_merge(card_1_interior, card_2_interior)
        and card_1.card_rank == card_2.card_rank
        and card_1.card_rank.value in {0, 1}  # Only merge if both cards are BRONZE or SILVER
    )


def determine_card_rank(card: np.ndarray, three_cards: bool = False) -> CardRanks:
    """Predict the card rank"""
    if find(vio.bronze_card, card, threshold=0.7):
        return CardRanks.BRONZE

    if find(vio.silver_card, card, threshold=0.7):
        return CardRanks.SILVER

    return (
        CardRanks.GOLD
        if find(vio.gold_card, card, threshold=0.7)
        else (
            CardRanks.ULTIMATE
            if determine_card_type(card, three_cards=three_cards) == CardTypes.ULTIMATE
            else CardRanks.NONE
        )
    )


def determine_db_floor(screenshot: np.ndarray, threshold=0.9) -> int:
    """Determine the Demonic Beast floor"""
    # sourcery skip: assign-if-exp, reintroduce-else
    floor_img_region = crop_image(
        screenshot,
        Coordinates.get_coordinates("floor_top_left"),
        Coordinates.get_coordinates("floor_bottom_right"),
    )

    # display_image(floor_img_region)
    # screenshot_testing(floor_img_region, vio.floor1, threshold=threshold)

    # Default
    db_floor = -1

    if find(vio.floor2, floor_img_region, threshold=threshold):
        db_floor = 2
    elif find(vio.floor3, floor_img_region, threshold=threshold):
        db_floor = 3
    elif find(vio.floor1, floor_img_region, threshold=threshold):
        db_floor = 1

    print(f"We're gonna fight floor {db_floor}.")

    return db_floor


def is_amplify_card(card: Card) -> bool:
    """Identify if a card is amplify or Thor"""
    if card.card_image is None:
        return 0

    card_interior = get_card_interior_image(card.card_image)
    return AmplifyCardPredictor.is_amplify_card(card_interior)


def is_hard_hitting_card(card: Card) -> bool:
    """Identify if a card is a card-hitting card"""
    if card.card_image is None:
        return 0

    card_interior = get_card_interior_image(card.card_image)
    return HAMCardPredictor.is_HAM_card(card_interior)


def is_Thor_card(card: Card) -> bool:
    """Identify Thor cards"""
    if card.card_image is None:
        return 0
    card_interior = get_card_interior_image(card.card_image)
    return ThorCardPredictor.is_Thor_card(card_interior)


def is_Meli_card(card: Card) -> bool:
    """Identify a Traitor Meli card"""
    return not is_ground_card(card) and (
        find(vio.meli_ult, card.card_image)
        or find(vio.meli_aoe, card.card_image)
        or find(vio.meli_ampli, card.card_image)
    )


def is_ground_card(card: Card) -> bool:
    """Return whether a card is of type GROUND"""
    return card.card_type in [CardTypes.GROUND, CardTypes.NONE]


def is_ground_region(screenshot: np.ndarray, rectangle: tuple[float, float, float, float], plot: bool = False) -> bool:
    """Given an entire screenshot and a rectangle of a region with [x,y,w,h], return whether the region is ground"""
    region_image = crop_image(
        screenshot, (rectangle[0], rectangle[1]), (rectangle[0] + rectangle[2], rectangle[1] + rectangle[3])
    )

    is_ground = GroundCardPredictor.is_ground_card(region_image)
    if plot and is_ground:
        print("IS GROUND!")
        display_image(region_image, "Region to check if ground")
    return is_ground


def is_stance_cancel_card(card: Card) -> bool:
    """Return whether the card is Stance Cancel"""
    if card.card_image is None:
        return False
    return find(vio.freyja_st, card.card_image) or find(vio.margaret_st, card.card_image)


def is_hard_hitting_snake_card(card: Card) -> bool:
    """Return whether a card can be used as hard-hitting on Snake (excluding ultimates)"""
    if card.card_image is None:
        return False
    card_image = card.card_image
    return (
        find(vio.mael_aoe, card_image)
        or find(vio.mael_st, card_image)
        or find(vio.freyja_st, card_image)
        or find(vio.freyja_aoe, card_image)
    )


def display_image(image: np.ndarray, title: str = "Image"):
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def load_dataset(glob_pattern: str) -> tuple[list | np.ndarray, np.ndarray]:
    """Return all the data and labels together, based on the specified file pattern"""
    dataset = []
    all_labels = []

    for filepath in glob.iglob(glob_pattern):
        print(f"Loading {filepath}...")
        local_data = pickle.load(open(filepath, "rb"))
        data, labels = local_data["data"], local_data["labels"]

        dataset.append(data)
        all_labels.append(labels)

    try:
        dataset = np.concatenate(dataset, axis=0)
    except ValueError:
        print("Error concatenating dataset, returning list instead")

    all_labels = np.concatenate(all_labels, axis=0)

    return dataset, all_labels


def save_model(model: KNeighborsClassifier | LogisticRegression, filename: str):
    """Save the model in file"""
    model_path = os.path.join("models", f"{filename}")
    with open(model_path, "wb") as pfile:
        pickle.dump(model, pfile)

    print(f"Model saved in '{model_path}'")


def type_word(word: str):
    """Types a word to the screen; useful to re-introduce the password if needed"""
    # To simulate human typing, just for fun
    delays = [random.uniform(0.1, 0.2) for _ in word]
    for char, delay in zip(word, delays):
        pyautogui.write(char)
        pyautogui.sleep(delay)  # Sleep for the given delay before typing the next character


def re_open_7ds_window():
    """Re-open the 7DS window"""
    # Maybe the 7DS window is closed, so we need to re-open it
    if not is_7ds_window_open():
        entire_screen = capture_screen()
        print("7DS window has been closed!")
        if find_and_click(vio.server_cancel, entire_screen):
            print("We cannot open the game...")
        time.sleep(5)  # Let's sleep to allow the game to be closed properly...
        if find_and_click(vio.run_game, entire_screen):
            print("Trying to re-open the game...")
            time.sleep(5)  # Let's wait for a while


def load_yaml_config(file_path: str) -> dict:
    """Load a YAML configuration file and return its contents as a dictionary."""
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)
    return config
