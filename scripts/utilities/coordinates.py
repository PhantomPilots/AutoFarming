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
        "talent": (276, 665),  # Where the Talent button is
        # The region in the screenshot corresponding to the card slots
        "card_slots_region": (150, 690, 410, 800),
        # General demonic beasts
        "floor_region": (344, 122, 459, 175),
        "right_swipe": (361, 466),
        "left_swipe": (177, 463),
        # For bird
        "4_cards_region": (61, 822, 517, 945),  # Hand region when we can use 4 cards
        "lazy_weekly_bird_mission": (283, 631),  # Weekly mission popup for demonic beast
        # For 3-team fights
        "3_cards_region": (52, 822, 517, 945),  # Hand region when we can use 3 cards
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
        "team_invite_region": (233, 615, 449, 669),
        "6_cards_region": (75, 693, 471, 793),  # 6 empty card slots region
        # For Indura
        "half_screen_region": (247, 438, 491, 689),  # To detect Alpha buffs only on our side
        # Guild Boss
        "change_gb": (50, 451),  # To change to the GB to the left until Belgius is found
        # Demon King
        "hell": (446, 708),
        "extreme": (279, 710),
        "hard": (111, 710),
        "rules_window_region": (145, 259, 403, 400),
        "4_units_region": (58, 239, 507, 408),
        # Rat
        "left_log": (148, 390),
        "middle_log": (242, 377),
        "right_log": (330, 380),
        # Rat stump door ROIs — (x1, y1, x2, y2) bounding boxes for darkness detection.
        # TODO: Calibrate these placeholder regions from real fight screenshots.
        "rat_door_left": (120, 360, 175, 420),
        "rat_door_center": (215, 347, 270, 407),
        "rat_door_right": (303, 350, 358, 410),
    }

    @staticmethod
    def get_coordinates(event: str):
        return Coordinates.__coordinates[event]

        # # Adjust their size based on the window!
        # screenshot, _ = capture_window()
        # y_ref, x_ref = screenshot.shape[:2]
        # return int(x / 552 * x_ref), int(y / 948 * y_ref)
