import threading
from enum import Enum, auto

import numpy as np
import utilities.vision_images as vio
from utilities.general_farmer_interface import IFarmer
from utilities.general_fighter_interface import IBattleStrategy, IFighter
from utilities.supreme_deity_fighter import SupremeDeityFighter
from utilities.supreme_deity_fighting_strategies import SupremeDeityBattleStrategy
from utilities.utilities import capture_window, find, find_and_click


class States(Enum):
    GOING_TO_SUPREME_DEITY = auto()
    SELECTING_DIFFICULTY = auto()
    FIGHTING = auto()
    EXIT_FARMER = auto()


class SupremeDeityFarmer(IFarmer):

    num_clears = 0

    difficulty_visions = {
        "hard": vio.sd_hard,
        "extreme": vio.sd_extreme,
        "hell": vio.sd_hell,
    }

    def __init__(
        self,
        starting_state=States.GOING_TO_SUPREME_DEITY,
        battle_strategy: IBattleStrategy = None,  # Always the Supreme Deity strategy
        difficulty: str = "hell",
        num_clears: str | float | int = 10,
        stigmata: str = "auto",
        **kwargs,
    ):
        super().__init__()

        self.current_state = starting_state
        self._menu_hint_shown = False

        self.difficulty = str(difficulty).strip().lower()
        if self.difficulty not in SupremeDeityFarmer.difficulty_visions:
            print(f"Unknown difficulty '{difficulty}', using hell.")
            self.difficulty = "hell"

        self.max_clears = float(num_clears)
        if self.max_clears < float("inf"):
            print(f"We're gonna fight the Supreme Deity ({self.difficulty}) {int(self.max_clears)} times.")

        # Using composition to decouple the main farmer logic from the actual fight.
        self.fighter: IFighter = SupremeDeityFighter(
            battle_strategy=SupremeDeityBattleStrategy,
            callback=self.fight_complete_callback,
            stigmata_mode=stigmata,
        )
        self.fighting_thread: threading.Thread = None

    def exit_message(self):
        super().exit_message()
        print(f"We fought the Supreme Deity {SupremeDeityFarmer.num_clears} times.")

    @staticmethod
    def _find_start_button(screenshot: np.ndarray) -> bool:
        return find(vio.startbutton, screenshot)

    def going_to_supreme_deity_state(self):
        """Go to the difficulty selection of the Supreme Deity Battle"""
        screenshot, window_location = capture_window()

        # In case we come from a complete fight
        find_and_click(vio.ok_main_button, screenshot, window_location)

        if find(vio.sd_menu_title, screenshot, threshold=0.8):
            self.current_state = States.SELECTING_DIFFICULTY
            print(f"Moving to {self.current_state}")
            return

        if self._find_start_button(screenshot):
            # Already on the team screen
            self.current_state = States.FIGHTING
            print(f"Moving to {self.current_state}")
            return

        # The Supreme Deity entry of the Battle menu isn't captured yet: the bot has to start from its menu
        if not self._menu_hint_shown:
            print("[WARN] Open the Supreme Deity difficulty menu, the bot can't find it by itself yet.")
            self._menu_hint_shown = True

    def selecting_difficulty_state(self):
        """Click on the chosen difficulty card"""
        screenshot, window_location = capture_window()

        if self._find_start_button(screenshot) or not find(vio.sd_menu_title, screenshot, threshold=0.8):
            self.current_state = States.FIGHTING
            print(f"Moving to {self.current_state}")
            return

        # The 3 difficulty labels look alike, so we need a high threshold
        find_and_click(
            SupremeDeityFarmer.difficulty_visions[self.difficulty], screenshot, window_location, threshold=0.85,
            sleep_time=1,
        )

    def fighting_state(self):
        """Start the fight and let the SupremeDeityFighter play it"""
        screenshot, window_location = capture_window()

        # We may need to restore stamina
        if find(vio.stamina_pot, screenshot) and find_and_click(vio.restore_stamina, screenshot, window_location):
            IFarmer.stamina_pots += 1
            print(f"We've used {IFarmer.stamina_pots} stamina pots so far")
            return

        # If we're back on the difficulty menu, pick the difficulty again
        if find(vio.sd_menu_title, screenshot, threshold=0.8) and (
            self.fighting_thread is None or not self.fighting_thread.is_alive()
        ):
            self.current_state = States.SELECTING_DIFFICULTY
            return

        find_and_click(vio.startbutton, screenshot, window_location)
        find_and_click(vio.skip, screenshot, window_location)

        with IFarmer._lock:
            # Lock necessary, such that `fight_complete_callback` and the next `if` don't happen simultaneously
            if (
                self.fighting_thread is None or not self.fighting_thread.is_alive()
            ) and self.current_state == States.FIGHTING:
                print("Starting the Supreme Deity fight!")
                self.fighter.prepare_for_new_fight()
                self.fighting_thread = threading.Thread(target=self.fighter.run, daemon=True)
                self.fighting_thread.start()

    def fight_complete_callback(self, victory: bool = None, **kwargs):
        """Called by the SupremeDeityFighter when the fight is over"""

        with IFarmer._lock:
            if victory:
                SupremeDeityFarmer.num_clears += 1
                print(f"Supreme Deity cleared! {SupremeDeityFarmer.num_clears} times so far.")
                print("[CLEAR]")
                if SupremeDeityFarmer.num_clears >= self.max_clears:
                    print("Reached the desired number of runs, closing the farmer...")
                    self.current_state = States.EXIT_FARMER
                    return
            else:
                print("We lost against the Supreme Deity :(")
                print("[LOSS]")

            self.current_state = States.GOING_TO_SUPREME_DEITY

    def run(self):

        print(f"Farming the Supreme Deity ({self.difficulty}), starting in state {self.current_state}.")

        self.run_state_loop(
            {
                States.GOING_TO_SUPREME_DEITY: self.going_to_supreme_deity_state,
                States.SELECTING_DIFFICULTY: self.selecting_difficulty_state,
                States.FIGHTING: self.fighting_state,
                States.EXIT_FARMER: self.exit_farmer_state,
            },
            login_return_state=States.GOING_TO_SUPREME_DEITY,
            sleep_seconds=0.5,
        )
