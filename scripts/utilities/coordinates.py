"""This file should be improved in the future to account for a variable game window."""

from utilities.capture_window import capture_window


class Coordinates:
    """Namespace-like class to group all the hardcoded coordinates"""

    # Screen coordinates for each floor
    __coordinates = {
        # General
        "battle_menu": (502, 676),  # Coordinates for the battle menu in the Tavern screen
        "knighthood": (421, 677),
        "center_screen": (270, 480),  # To click on the center of the screen
        "sync_code": (278, 388),  # Coordinates for the username input field
        # The region in the screenshot corresponding to the card slots
        "top_left_card_slots": (150, 690),
        "bottom_right_card_slots": (410, 800),
        # General demonic beasts
        "floor_top_left": (344, 122),
        "floor_bottom_right": (459, 175),
        "right_swipe": (361, 466),
        "left_swipe": (177, 463),
        # For bird
        "4_cards_top_left": (61, 822),  # Top-left corner of the hand when we can use 4 cards
        "4_cards_bottom_right": (517, 945),  # Bottom-right corner of the hand when we can use 4 cards
        "lazy_weekly_bird_mission": (283, 631),  # Weekly mission popup for demonic beast
        # For 3-team fights
        "3_cards_top_left": (52, 822),  # Top-left corner of the hand when we can use 3 cards
        "3_cards_bottom_right": (517, 945),  # Bottom-right corner of the hand when we can use 3 cards
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
        # For SA coin dungeon
        "start_drag_sa": (276, 800),
        "end_drag_sa": (275, 650),
        # Dogs farming
        "light_dog": (346, 386),
        "dark_dog": (160, 412),
        # Card slots
        "first_slot": (161, 746),
        "second_slot": (227, 746),
        "third_slot": (276, 746),
        "fourth_slot": (331, 746),
        "fifth_slot": (397, 746),
        # Receive Brawl coordinates
        "receive_brawl": (384, 187),
        # Daily fortune card
        "daily_fortune_bottom": (277, 651),
        "daily_fortune_top": (277, 215),
        # Demon farming
        "stamp_box": (515, 662),
        "first_stamp": (83, 762),
        "team_invite_top_left": (233, 615),
        "team_invite_bottom_right": (449, 669),
        "6_cards_top_left": (75, 693),  # Top-left corner of the 6 empty slots
        "6_cards_bottom_right": (471, 793),  # Bottom-right corner of the 6 empty slots
        # For Indura
        "half_screen_top_left": (247, 438),  # To detect Alpha buffs only on our side
        "half_screen_bottom_right": (491, 689),
    }

    @staticmethod
    def get_coordinates(event: str):
        x, y = Coordinates.__coordinates[event]
        return x, y

        # # Adjust their size based on the window!
        # screenshot, _ = capture_window()
        # y_ref, x_ref = screenshot.shape[:2]
        # return int(x / 552 * x_ref), int(y / 948 * y_ref)
