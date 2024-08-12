"""This file should be improved in the future to account for a variable game window."""


class Coordinates:
    """Namespace-like class to group all the hardcoded coordinates"""

    # Screen coordinates for each floor
    coordinates = {
        # General
        "battle_menu": (502, 676),  # Coordinates for the battle menu in the Tavern screen
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
    }

    @staticmethod
    def get_coordinates(event):
        return Coordinates.coordinates[event]
