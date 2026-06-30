import time
from dataclasses import dataclass
from enum import Enum

import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter
from utilities.coordinates import Coordinates
from utilities.deer_fighter import DeerFighter
from utilities.deer_fighting_strategies import DeerBattleStrategy
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer
from utilities.demonic_beast_farming_logic import States as DemonicBeastStates
from utilities.dogs_fighter import DogsFighter
from utilities.dogs_fighting_strategies import DogsBattleStrategy
from utilities.fighting_strategies import SmarterBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, drag_im, find, find_and_click

logger = LoggerWrapper(name="DemonicBeastRotationLogger", log_file="demonic_beast_rotation_logger.log")


class RotationStates(Enum):
    SWITCHING_BEAST = 0
    RETURNING_TO_TAVERN = 1


@dataclass(frozen=True)
class BeastConfig:
    key: str
    display_name: str
    db_image: vio.Vision
    fighter_cls: type
    battle_strategy_cls: type
    reset_after_defeat: bool


class DemonicBeastRotationFarmer(DemonicBeastFarmer):
    BEAST_ORDER = ("bird", "deer", "dogs")
    BEASTS = {
        "bird": BeastConfig(
            key="bird",
            display_name="Bird",
            db_image=vio.hraesvelgr,
            fighter_cls=BirdFighter,
            battle_strategy_cls=SmarterBattleStrategy,
            reset_after_defeat=False,
        ),
        "deer": BeastConfig(
            key="deer",
            display_name="Deer",
            db_image=vio.eikthyrnir,
            fighter_cls=DeerFighter,
            battle_strategy_cls=DeerBattleStrategy,
            reset_after_defeat=True,
        ),
        "dogs": BeastConfig(
            key="dogs",
            display_name="Dogs",
            db_image=vio.skollandhati,
            fighter_cls=DogsFighter,
            battle_strategy_cls=DogsBattleStrategy,
            reset_after_defeat=True,
        ),
    }

    _selected_beast_keys: tuple[str, ...] = BEAST_ORDER
    _active_beast_index = 0
    _switch_from_beast_key: str | None = None
    _switch_swipe_attempts = 0

    def __init__(
        self,
        battle_strategy=None,
        starting_state=DemonicBeastStates.GOING_TO_DB,
        beasts_to_farm: list[str] | tuple[str, ...] | None = None,
        max_stamina_pots="inf",
        logger=logger,
        password: str | None = None,
        do_dailies=False,
        do_daily_pvp=True,
    ):
        del battle_strategy

        beast_keys = self.normalize_beast_keys(beasts_to_farm)
        type(self)._set_selected_beasts(beast_keys)

        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_floor_3_clears="inf",
            demonic_beast_image=self.current_beast_config.db_image,
            reset_after_defeat=self.current_beast_config.reset_after_defeat,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
            do_daily_pvp=do_daily_pvp,
        )
        self._apply_current_beast()
        print(f"We'll run floors 1-3 once for: {self.selected_beast_names}.")
        print(f"Starting with {self.current_beast_config.display_name}.")

    @classmethod
    def normalize_beast_keys(cls, beast_keys: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
        if not beast_keys:
            return cls.BEAST_ORDER

        selected = set(beast_keys)
        unknown = selected - set(cls.BEAST_ORDER)
        if unknown:
            raise ValueError(f"Unknown demonic beast(s): {', '.join(sorted(unknown))}")

        return tuple(key for key in cls.BEAST_ORDER if key in selected)

    @classmethod
    def _set_selected_beasts(cls, beast_keys: tuple[str, ...]) -> None:
        if cls._selected_beast_keys != beast_keys:
            cls._selected_beast_keys = beast_keys
            cls._active_beast_index = 0
            cls._switch_from_beast_key = None
            cls._switch_swipe_attempts = 0
        elif cls._active_beast_index >= len(beast_keys):
            cls._active_beast_index = 0
            cls._switch_from_beast_key = None
            cls._switch_swipe_attempts = 0

    @classmethod
    def reset_rotation_state(cls) -> None:
        cls._selected_beast_keys = cls.BEAST_ORDER
        cls._active_beast_index = 0
        cls._switch_from_beast_key = None
        cls._switch_swipe_attempts = 0

    @property
    def active_beast_key(self) -> str:
        return type(self)._selected_beast_keys[type(self)._active_beast_index]

    @property
    def current_beast_config(self) -> BeastConfig:
        return self.BEASTS[self.active_beast_key]

    @property
    def selected_beast_names(self) -> list[str]:
        return [self.BEASTS[key].display_name for key in type(self)._selected_beast_keys]

    def _apply_current_beast(self) -> None:
        config = self.current_beast_config
        self.db_image = config.db_image
        self.reset_after_defeat = config.reset_after_defeat
        self.fighter = config.fighter_cls(
            battle_strategy=config.battle_strategy_cls,
            callback=self.fight_complete_callback,
        )
        self.fight_thread = None

    def _advance_to_next_beast(self) -> bool:
        next_index = type(self)._active_beast_index + 1
        if next_index >= len(type(self)._selected_beast_keys):
            return False

        type(self)._active_beast_index = next_index
        DemonicBeastFarmer.current_floor = 1
        DemonicBeastFarmer._swipe_attempts = 0
        self._apply_current_beast()
        print(f"Switching to {self.current_beast_config.display_name}.")
        return True

    def fight_complete_callback(self, victory=True, phase="unknown"):
        """Called when the active beast fighter completes a floor."""

        with IFarmer._lock:
            if victory:
                DemonicBeastFarmer.num_victories += 1
                completed_floor = DemonicBeastFarmer.current_floor
                print(f"{self.current_beast_config.display_name} floor {completed_floor} complete!")

                DemonicBeastFarmer.current_floor = (DemonicBeastFarmer.current_floor % 3) + 1
                if DemonicBeastFarmer.current_floor == 1:
                    DemonicBeastFarmer.num_floor_3_victories += 1
                    print("[CLEAR]")

                    completed_beast_key = self.active_beast_key
                    if self._advance_to_next_beast():
                        type(self)._switch_from_beast_key = completed_beast_key
                        type(self)._switch_swipe_attempts = 0
                        self.current_state = RotationStates.SWITCHING_BEAST
                    else:
                        type(self)._switch_from_beast_key = None
                        type(self)._switch_swipe_attempts = 0
                        print("Finished all selected Demonic Beasts, returning to the tavern.")
                        self.current_state = RotationStates.RETURNING_TO_TAVERN
                else:
                    print("Moving to GOING_TO_DB")
                    self.current_state = DemonicBeastStates.GOING_TO_DB

            else:
                print(f"The {self.current_beast_config.display_name} fighter told me we lost... :/")
                print("[LOSS]")
                DemonicBeastFarmer.num_losses += 1
                IFarmer.dict_of_defeats[
                    f"{self.current_beast_config.display_name} Floor {DemonicBeastFarmer.current_floor} Phase {phase}"
                ] += 1

                if self.reset_after_defeat:
                    self.current_state = DemonicBeastStates.RESETTING_DB
                else:
                    self.current_state = DemonicBeastStates.GOING_TO_DB

            self.exit_message()

    def switching_beast_state(self):
        screenshot, window_location = capture_window()
        completed_beast_key = type(self)._switch_from_beast_key

        if completed_beast_key is None:
            print(f"No completed beast recorded; looking for {self.current_beast_config.display_name}.")
            self.current_state = DemonicBeastStates.GOING_TO_DB
            return

        completed_config = self.BEASTS[completed_beast_key]
        target_config = self.current_beast_config

        if find(target_config.db_image, screenshot):
            print(f"Found {target_config.display_name}; resuming Demonic Beast navigation.")
            type(self)._switch_from_beast_key = None
            type(self)._switch_swipe_attempts = 0
            self.current_state = DemonicBeastStates.GOING_TO_DB
            return

        if not find(completed_config.db_image, screenshot):
            print(f"Backing out until {completed_config.display_name} is visible.")
            find_and_click(vio.ok_main_button, screenshot, window_location)
            find_and_click(vio.back, screenshot, window_location)
            return

        type(self)._switch_swipe_attempts += 1
        print(
            f"{completed_config.display_name} visible; swiping right toward "
            f"{target_config.display_name} (attempt {type(self)._switch_swipe_attempts})."
        )
        drag_im(
            Coordinates.get_coordinates("right_swipe"),
            Coordinates.get_coordinates("left_swipe"),
            window_location,
        )
        time.sleep(0.5)

    def returning_to_tavern_state(self):
        screenshot, window_location = capture_window()

        if find(vio.tavern, screenshot) and find_and_click(
            vio.tavern,
            screenshot,
            window_location,
            threshold=0.8,
            sleep_time=1,
        ):
            self.current_state = DemonicBeastStates.EXIT_FARMER
            return

        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.back, screenshot, window_location)

    def dailies_complete_callback(self):
        with IFarmer._lock:
            print("All dailies complete! Going back to Demonic Beast rotation.")
            IFarmer.dailies_thread = None
            self.current_state = DemonicBeastStates.GOING_TO_DB

    def run(self):
        self.run_state_loop(
            {
                DemonicBeastStates.GOING_TO_DB: self.going_to_db_state,
                DemonicBeastStates.SET_PARTY: self.set_party_state,
                DemonicBeastStates.READY_TO_FIGHT: self.proceed_to_floor_state,
                DemonicBeastStates.FIGHTING_FLOOR: self.fighting_floor,
                DemonicBeastStates.RESETTING_DB: self.resetting_db_state,
                DemonicBeastStates.EXIT_FARMER: self.exit_farmer_state,
                RotationStates.SWITCHING_BEAST: self.switching_beast_state,
                RotationStates.RETURNING_TO_TAVERN: self.returning_to_tavern_state,
            },
            login_return_state=DemonicBeastStates.GOING_TO_DB,
            sleep_seconds=0.1,
        )
