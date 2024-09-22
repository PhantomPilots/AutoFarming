"""This file should be improved in the future to account for a variable game window."""

from utilities.capture_window import capture_window


class Coordinates:
    """Namespace-like class to group all the hardcoded coordinates"""

    # Screen coordinates for each floor
    coordinates = {
        # General
        "battle_menu": (502, 676),  # Coordinates for the battle menu in the Tavern screen
        # The region in the screenshot corresponding to the card slots
        "top_left_card_slots": (154, 700),
        "bottom_right_card_slots": (404, 793),
        # For bird
        "4_cards_top_left": (61, 822),  # Top-left corner of the hand when we can use 4 cards
        "4_cards_bottom_right": (517, 945),  # Bottom-right corner of the hand when we can use 4 cards
        "lazy_weekly_bird_mission": (283, 631),  # Weekly mission popup for demonic beast
        # For equipment farming
        "equipment_menu": (167, 842),
        "free_stage_hard": (280, 600),
        "start_fight": (280, 914),
        "high_grade_equipment": (362, 555),
        "ok_after_salvaging": (281, 893),
        "salvage_equipment": (60, 525),
        # For final boss farming
        "start_drag": (280, 914),
        "end_drag": (280, 550),
        "showdown": (280, 870),
        # Dogs farming
        "light_dog": (346, 386),
        "dark_dog": (160, 412),
        # Card slots
        "first_slot": (161, 746),
        "second_slot": (227, 746),
        "third_slot": (276, 746),
        "fourth_slot": (331, 746),
        "fifth_slot": (397, 746),
    }

    @staticmethod
    def get_coordinates(event):
        x, y = Coordinates.coordinates[event]

        # Adjust their size based on the window!
        screenshot, _ = capture_window()
        y_ref, x_ref = screenshot.shape[:2]
        return int(x / 552 * x_ref), int(y / 948 * y_ref)
