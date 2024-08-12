import os
from enum import Enum
from time import sleep
from typing import Union

import cv2
import dill as pickle
import numpy as np
import pyautogui
import utilities.vision_images as vio
import win32api
import win32con
import win32gui
import win32ui
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.coordinates import Coordinates
from utilities.models import CardMergePredictor, CardTypePredictor
from utilities.vision import Vision


def capture_window():
    """Make a screenshot of the 7DS window.
    Returns:
        tuple[np.ndarray, list[float]]: The image as a numpy array, and a list of the top-left corner of the window as [x,y]
    """
    hwnd_target = win32gui.FindWindow(None, r"7DS")
    window_rect = win32gui.GetWindowRect(hwnd_target)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]
    window_location = [window_rect[0], window_rect[1]]

    # Remove border pixels -- TODO: Necessary?
    border_pixels = 2
    w = w - (border_pixels * 2)
    h = h - 20

    # Whatever this is?
    hdesktop = win32gui.GetDesktopWindow()
    hwndDC = win32gui.GetWindowDC(hdesktop)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

    saveDC.SelectObject(saveBitMap)
    saveDC.BitBlt((0, 0), (w, h), mfcDC, (window_rect[0], window_rect[1]), win32con.SRCCOPY)

    # bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    # convert the raw data into a format opencv can read
    img = np.frombuffer(bmpstr, dtype="uint8")
    img.shape = (h, w, 4)
    # free resources
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hdesktop, hwndDC)
    img = img[..., :3]

    img = np.ascontiguousarray(img)
    # get updated window location
    window_rect = win32gui.GetWindowRect(hwnd_target)
    window_location = [window_rect[0], window_rect[1]]

    return img, window_location


def get_window_size():
    """Get the size of the 7DS window"""
    hwnd_target = win32gui.FindWindow(None, r"7DS")
    window_rect = win32gui.GetWindowRect(hwnd_target)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]

    return w, h


def screenshot_testing(vision_image: Vision, threshold=0.8):
    """Debugging function that displays a screenshot and the patterns matched for a specific `Vision` image"""
    # screenshot, _ = get_unfocused_screenshot()
    screenshot, _ = capture_window()

    # cv2.imshow("screenshot", screenshot)

    # rectangle = vision_image.find(screenshot, threshold=threshold)
    rectangles, _ = vision_image.find_all_rectangles(screenshot, threshold=threshold)
    if rectangles.size:
        new_image = vision_image.draw_rectangles(screenshot, rectangles)
        cv2.imshow("Rectangles", new_image)
        cv2.waitKey(0)

    else:
        print("No rectangles found!")

    # Simply to stop the execution of the rest of the code
    raise ValueError("This function should only be used for testing, killing program execution.")


def count_empty_card_slots(screenshot, threshold=0.7):
    """Ideally used within a fight, count how many empty card slots we have available"""
    rectangles, _ = vio.empty_card_slot.find_all_rectangles(screenshot, threshold=threshold)
    return rectangles.shape[0]


def check_for_reconnect():
    """Sometimes, we lose connection"""
    screenshot, window_location = capture_window()
    if find_and_click(vio.reconnect, screenshot, window_location):
        print("Reconnecting...")


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


def find(vision_image: Vision, screenshot: np.ndarray, threshold=0.8) -> bool:
    """Simply return if a match is found"""
    rectangle = vision_image.find(screenshot, threshold=threshold)
    return bool(rectangle.size)


def find_and_click(
    vision_image: Vision,
    screenshot: np.ndarray,
    window_location: list[float],
    threshold=0.8,
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

        sleep(0.5)

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
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    sleep(sleep_after_click)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


def rclick(x, y, sleep_after_click=0.01):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
    sleep(sleep_after_click)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)


def press_key(key: str):
    pyautogui.press(key)


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


def capture_hand_image() -> np.ndarray:
    """Capture the hand image"""
    screenshot, _ = capture_window()

    return crop_image(
        screenshot,
        Coordinates.get_coordinates("4_cards_top_left"),
        Coordinates.get_coordinates("4_cards_bottom_right"),
    )


def get_card_type_image(card: np.ndarray) -> np.ndarray:
    """Extract the card type image from the card"""
    w = card.shape[-2]
    return crop_image(card, (40, 0), (w, 20))


def get_card_interior_image(card_image: np.ndarray) -> np.ndarray:
    """Get the inside of the card, without the border.
    TODO: Very hardcoded, fix in the future for other resolution."""
    border = 8
    return crop_image(
        card_image,
        (border, border + 4),
        (card_image.shape[1] - border, card_image.shape[0] - border - 12),
    )


def get_hand_cards() -> list[Card]:
    """Retrieve the current cards in the hand.

    Returns:
        list[Card]:   The hand of cards. It's a list of tuples; each tuple contains the card type,
                                            the `np.ndarray` card, as an image, and a tuple with the top-left coordinates of the card.
    """
    hand_cards = capture_hand_image()
    # display_image(hand_cards)

    # Determine the width of each column
    height, width = hand_cards.shape[:2]
    column_width = width / 8  # Calculate the width of each column
    column_width = int(column_width)

    # Split the image into 8 equal columns -- TODO: Not the best way to do it, doesn't work well
    house_of_cards = [
        ([61 + i * column_width, 822, column_width, height], hand_cards[:, i * column_width : (i + 1) * column_width])
        for i in range(8)
    ]

    return [Card(determine_card_type(card[-1]), *card, determine_card_rank(card[-1])) for card in house_of_cards]


def determine_card_type(card: np.ndarray) -> CardTypes:
    """Predict the card type"""
    card_type_image = get_card_type_image(card)
    return CardTypePredictor.predict_card_type(card_type_image)


def determine_card_merge(card_1: Card, card_2: Card) -> bool:
    """Predict whether two cards are going to merge"""

    card_1_interior = get_card_interior_image(card_1.card_image)
    card_2_interior = get_card_interior_image(card_2.card_image)

    return (
        CardMergePredictor.predict_card_merge(card_1_interior, card_2_interior)
        and card_1.card_rank == card_2.card_rank
        and card_1.card_rank != CardRanks.GOLD
    )


def determine_card_rank(card: np.ndarray) -> CardRanks:
    """Predict the card rank"""
    if find(vio.bronze_card, card, threshold=0.7):
        return CardRanks.BRONZE

    if find(vio.silver_card, card, threshold=0.7):
        return CardRanks.SILVER

    return CardRanks.GOLD if find(vio.gold_card, card, threshold=0.7) else CardRanks.NONE


def display_image(image: np.ndarray):
    cv2.imshow("Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
