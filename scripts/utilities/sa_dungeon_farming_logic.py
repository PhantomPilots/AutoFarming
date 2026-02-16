import time
from enum import Enum, auto

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper, logging
from utilities.utilities import (
    Color,
    capture_window,
    check_for_reconnect,
    drag_im,
    find,
    find_and_click,
    find_rect,
    crop_roi_from_rect,
    score_template,
    press_key,
    print_clr,
)

logger = LoggerWrapper("sa_dungeon_logger", level=logging.INFO, log_to_file=False)


class States(Enum):
    GOING_TO_DUNGEON = auto()
    OPENING_DUNGEON = auto()
    GOING_TO_FLOOR_STATE = auto()
    GET_READY = auto()
    FIGHTING = auto()
    RESTART_FIGHT = auto()
    RUN_ENDED = auto()


class Scrolling(Enum):
    DOWN = auto()
    UP = auto()

class ChestTier(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2


class SADungeonFarmer(IFarmer):
    """SA dungeon farmer"""

    # How many resets so far
    num_resets = 0
    # How many runs we've done?
    num_runs_complete = 0

    # To avoid counting multiple finished runs if the "finished_auto_repeat_fight" image is detected for multiple consecutive frames
    finished_run_lockout_until: float = 0.0

    # How many chests we've collected so far
    collected_chests: dict[ChestTier, int] = {ChestTier.BRONZE: 0, ChestTier.SILVER: 0, ChestTier.GOLD: 0}

    # Detection flags
    chest_found: bool = False
    first_wave_done: bool = False
    # How many times we've retried detecting a chest before deciding to restart
    retry_count: int = 0

    def __init__(self, *, starting_state=States.GOING_TO_DUNGEON, battle_strategy=None, min_chest_type="bronze", chest_detection_count=3, **kwargs):
        self.current_state = starting_state

        # Chest filtering config
        self.num_image_detection_retries = chest_detection_count
        min_chest_type = str(min_chest_type).strip().lower()
        if min_chest_type not in {"bronze", "silver", "gold"}:
            print_clr(f"[WARN] Invalid min_chest_type='{min_chest_type}', defaulting to 'bronze'", color=Color.YELLOW)
            min_chest_type = "bronze"
        self.min_chest_type = min_chest_type
        self.min_chest_tier = {
            "bronze": ChestTier.BRONZE,
            "silver": ChestTier.SILVER,
            "gold": ChestTier.GOLD,
        }[min_chest_type]

        self.chest_templates = self.load_chest_templates()

        print(f"Chest filter: keep >= {self.min_chest_type.upper()}")
        print(f"Chest detection retries: {self.num_image_detection_retries}")

    def load_chest_templates(self) -> dict[str, np.ndarray]:
        templates = {
            "bronze": getattr(vio.chest_bronze, "needle_img", None),
            "silver": getattr(vio.chest_silver, "needle_img", None),
            "gold": getattr(vio.chest_gold, "needle_img", None),
        }
        templates = {k: v for k, v in templates.items() if v is not None}

        if not templates:
            print_clr("[WARN] No chest templates loaded from vision_images.", color=Color.YELLOW)
        return templates
    
    def classify_chest_type(self, chest_roi_bgr: np.ndarray) -> tuple[str, float]:
        best_label = "unknown"
        best_score = -1.0

        if chest_roi_bgr is None or chest_roi_bgr.size == 0 or not self.chest_templates:
            return best_label, best_score

        for label, tpl in self.chest_templates.items():
            if chest_roi_bgr.shape[0] < tpl.shape[0] or chest_roi_bgr.shape[1] < tpl.shape[1]:
                continue
            score, _ = score_template(chest_roi_bgr, tpl)
            if score > best_score:
                best_score = score
                best_label = label

        return best_label, best_score

    def should_restart_for_chest(self, screenshot: np.ndarray) -> tuple[bool, str]:
        rect = find_rect(vio.chest, screenshot, threshold=0.6)
        if rect is None or len(rect) == 0:
            return True, "no chest"

        SADungeonFarmer.chest_found = True  # We found the chest, let's set the flag to avoid re-checking until next fight
        roi = crop_roi_from_rect(screenshot, rect)
        label, score = self.classify_chest_type(roi)

        if label == "unknown" or score < 0.70:
            # Conservative keep on low-confidence classification
            return False, f"unknown chest (score={score:.3f}), keeping run"

        chest_tier = {
            "bronze": ChestTier.BRONZE,
            "silver": ChestTier.SILVER,
            "gold": ChestTier.GOLD,
        }[label]

        if chest_tier.value < self.min_chest_tier.value:
            return True, f"{label} < {self.min_chest_type}"

        SADungeonFarmer.collected_chests[chest_tier] += 1
        print_clr(f"Total collected chests: {', '.join(f'{tier.name}: {count}' for tier, count in SADungeonFarmer.collected_chests.items())}", color=Color.GREEN)
        return False, f"{label} >= {self.min_chest_type}"

    def going_to_dungeon_state(self):
        """Let's go to the dungeon"""
        screenshot, window_location = capture_window()

        # Click on battle menu
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6)
        # Click on FS dungeon
        find_and_click(vio.fs_dungeon, screenshot, window_location)
        # Click on FS Special
        find_and_click(vio.fort_solgress_special, screenshot, window_location)
        # Clock Tower
        if find(vio.sa_coin, screenshot) or find(vio.clock_tower, screenshot) or find(vio.fs_dungeon_lock, screenshot):
            self.current_state = States.OPENING_DUNGEON
            print(f"Going to {self.current_state}")

    def opening_dungeon_state(self):
        screenshot, window_location = capture_window()

        if find(vio.clock_tower_floor, screenshot):
            self.current_state = States.GOING_TO_FLOOR_STATE
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            # We're re-opening the floor!
            print("Opening the floor, resetting counters")
            SADungeonFarmer.num_resets = 0
            SADungeonFarmer.num_runs_complete = 0
            SADungeonFarmer.collected_chests = {ChestTier.BRONZE: 0, ChestTier.SILVER: 0, ChestTier.GOLD: 0}
            SADungeonFarmer.finished_run_lockout_until = 0.0
            self.reset_retry_flags()
            return

        if not find(vio.sa_coin, screenshot) and find(vio.back, screenshot):
            # Let's drag, up or down?
            direction = Scrolling.DOWN if find(vio.fs_event_dungeon, screenshot) else Scrolling.UP

            # If we find a "lock", let's scroll from that position
            rectangle = vio.fs_dungeon_lock.find(screenshot)
            if direction == Scrolling.DOWN:
                drag_im(
                    rectangle[:2] if len(rectangle) else Coordinates.get_coordinates("start_drag_sa"),
                    (
                        (rectangle[0], rectangle[1] - 150)
                        if len(rectangle)
                        else Coordinates.get_coordinates("end_drag_sa")
                    ),
                    window_location,
                )
            elif direction == Scrolling.UP:
                drag_im(
                    rectangle[:2] if len(rectangle) else Coordinates.get_coordinates("end_drag_sa"),
                    (
                        (rectangle[0], rectangle[1] + 150)
                        if len(rectangle)
                        else Coordinates.get_coordinates("start_drag_sa")
                    ),
                    window_location,
                )

            return

        if find(vio.sa_coin, screenshot, threshold=0.7):
            # Let's try to access/open the tower
            rectangle = vio.sa_coin.find(screenshot, threshold=0.7)
            find_and_click(
                vio.sa_coin,
                screenshot,
                window_location,
                threshold=0.7,
                point_coordinates=(Coordinates.get_coordinates("center_screen")[0], rectangle[1] + rectangle[-1] / 2),
            )

    def going_to_floor_state(self):
        """Dungeon is open, let's go to the floor"""
        screenshot, window_location = capture_window()

        if find(vio.startbutton, screenshot):
            # Let's go to proceed to battle!
            self.current_state = States.GET_READY
            print(f"Going to {self.current_state}")
            return

        if find(vio.clock_tower_floor, screenshot):
            rectangle = vio.clock_tower_floor.find(screenshot)
            find_and_click(
                vio.clock_tower_floor,
                screenshot,
                window_location,
                point_coordinates=(Coordinates.get_coordinates("center_screen")[0], rectangle[1] + rectangle[-1] / 2),
            )

    def get_ready_state(self):
        """Prepare the fight and go!"""
        screenshot, window_location = capture_window()

        if find_and_click(vio.auto_repeat_off, screenshot, window_location, threshold=0.8):
            return

        # Let's fight!
        if find(vio.startbutton, screenshot):
            print("LET'S FIGHT!")
            self.current_state = States.FIGHTING

    def fighting_state(self):
        """Fighting!"""
        screenshot, window_location = capture_window()

        if find(vio.auto_repeat_ended, screenshot, threshold=0.8):
            print("Finished this run! Gotta re-open the dungeon")
            self.current_state = States.RUN_ENDED
            return

        # We may need to restore stamina
        if find_and_click(vio.restore_stamina, screenshot, window_location, threshold=0.8):
            IFarmer.stamina_pots += 1
            return

        # If we've finished a fight in the auto-repeat, count it
        now = time.monotonic()
        if now >= SADungeonFarmer.finished_run_lockout_until and find(vio.finished_auto_repeat_fight, screenshot):
            SADungeonFarmer.num_runs_complete += 1
            SADungeonFarmer.finished_run_lockout_until = now + 5.0
            self.reset_retry_flags()
            print(f"We've completed {SADungeonFarmer.num_runs_complete}/12 runs")

        find_and_click(vio.startbutton, screenshot, window_location)

        # Check if we can see the boss, if so, it means we are done with the first wave and we should start looking for the chest
        # Make sure that the UI is visible, otherwise we see the boss, but no UI so can't see chests
        if find(vio.sa_boss, screenshot, threshold=0.7) and find(vio.pause, screenshot, threshold=0.7):
            SADungeonFarmer.first_wave_done = True

        # Keep rechecking for the chest after the first wave is done, until we find it or decide to restart
        if SADungeonFarmer.first_wave_done and not SADungeonFarmer.chest_found:
            should_restart, reason = self.should_restart_for_chest(screenshot)
            if not should_restart:
                print_clr(f"Keeping run: {reason}", color=Color.GREEN)
            elif reason == "no chest":
                SADungeonFarmer.retry_count += 1
                if SADungeonFarmer.retry_count <= self.num_image_detection_retries:
                    print(
                        f"[RETRY {SADungeonFarmer.retry_count}/{self.num_image_detection_retries}] "
                        f"No chest detected yet, retrying image detection before restarting."
                    )
                else:
                    print_clr("Restarting run: no chest after retry limit", color=Color.RED)
                    self.lets_restart_fight(screenshot)
            else:
                print_clr(f"Restarting run immediately: {reason}", color=Color.RED)
                self.lets_restart_fight(screenshot)

    def reset_retry_flags(self):
        """Reset flags related to retrying after not finding a chest"""
        SADungeonFarmer.retry_count = 0
        SADungeonFarmer.first_wave_done = False
        SADungeonFarmer.chest_found = False

    def lets_restart_fight(self, screenshot: np.ndarray):
        """Common logic to restart the fight"""
        self.current_state = States.RESTART_FIGHT
        # Let's log the image for later inspection
        logger.save_image(screenshot, subdir="sa_images")

        # Increase the reset count regardless
        SADungeonFarmer.num_resets += 1
        self.reset_retry_flags()
        print(f"We've restarted the fight {SADungeonFarmer.num_resets} times")

    def restart_fight_state(self):
        """We gotta restart, because of no chest..."""
        screenshot, window_location = capture_window()

        if find(vio.tavern_loading_screen, screenshot):
            self.current_state = States.OPENING_DUNGEON
            print(f"Going to {self.current_state}")
            return

        if find_and_click(vio.ok_main_button, screenshot, window_location):
            return
        if find_and_click(vio.forfeit, screenshot, window_location):
            return

        press_key("esc")

    def run_ended_state(self):
        """We finished a run! Gotta re-open the dungeon, by ESC-ing until we're back into the dungeon"""
        screenshot, _ = capture_window()

        if find(vio.back, screenshot) or find(vio.sa_coin, screenshot):
            self.current_state = States.GOING_TO_DUNGEON
            print(f"Going to {self.current_state}")
            return

        if not find(vio.fs_loading_screen, screenshot):
            press_key("esc")

    def check_for_esette_popup(self):
        """Check if we have the Essette shop, and click on it if so to remove the popup"""
        screenshot, window_location = capture_window()
        find_and_click(vio.essette_shop, screenshot, window_location)

    def run(self):

        print("Farming SA coin dungeon!")

        while True:

            check_for_reconnect()
            self.check_for_esette_popup()

            if self.current_state == States.GOING_TO_DUNGEON:
                self.going_to_dungeon_state()

            elif self.current_state == States.OPENING_DUNGEON:
                self.opening_dungeon_state()

            elif self.current_state == States.GOING_TO_FLOOR_STATE:
                self.going_to_floor_state()

            elif self.current_state == States.GET_READY:
                self.get_ready_state()

            elif self.current_state == States.FIGHTING:
                self.fighting_state()

            elif self.current_state == States.RESTART_FIGHT:
                self.restart_fight_state()

            elif self.current_state == States.RUN_ENDED:
                self.run_ended_state()

            time.sleep(0.5)
