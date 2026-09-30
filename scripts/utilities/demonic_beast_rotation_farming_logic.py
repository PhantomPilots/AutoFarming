from dataclasses import dataclass
from enum import Enum

import utilities.vision_images as vio
from utilities.bird_fighter import BirdFighter
from utilities.deer_fighter import DeerFighter
from utilities.deer_fighting_strategies import DeerBattleStrategy
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer
from utilities.demonic_beast_farming_logic import States as DemonicBeastStates
from utilities.dogs_fighter import DogsFighter
from utilities.dogs_fighting_strategies import DogsBattleStrategy
from utilities.fighting_strategies import SmarterBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import capture_window, find, find_and_click, navigate_to_demonic_beast

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

    def __init__(
        self,
        battle_strategy=None,
        starting_state=DemonicBeastStates.GOING_TO_DB,
        beasts_to_farm: list[str] | tuple[str, ...] | None = None,
        repeat_rotation: bool = False,
        max_stamina_pots="inf",
        logger=logger,
        password: str | None = None,
        do_dailies=False,
        do_daily_pvp=True,
    ):
        del battle_strategy

        beast_keys = self.normalize_beast_keys(beasts_to_farm)
        type(self)._set_selected_beasts(beast_keys)
        self.repeat_rotation = repeat_rotation

        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_clears="inf",
            demonic_beast_image=self.current_beast_config.db_image,
            reset_after_defeat=self.current_beast_config.reset_after_defeat,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
            do_daily_pvp=do_daily_pvp,
        )
        self._apply_current_beast()
        if self.repeat_rotation:
            print(f"We'll continuously rotate through floors 1-3 for: {self.selected_beast_names}.")
        else:
            print(f"We'll run floors 1-3 once for: {self.selected_beast_names}.")
        print(f"Starting with {self.current_beast_config.display_name}.")

    @classmethod
    def normalize_beast_keys(cls, beast_keys: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
        if not beast_keys:
            return cls.BEAST_ORDER

        selected = set(beast_keys)
        if unknown := selected - set(cls.BEAST_ORDER):
            raise ValueError(f"Unknown demonic beast(s): {', '.join(sorted(unknown))}")

        return tuple(key for key in cls.BEAST_ORDER if key in selected)

    @classmethod
    def _set_selected_beasts(cls, beast_keys: tuple[str, ...]) -> None:
        if cls._selected_beast_keys != beast_keys:
            cls._selected_beast_keys = beast_keys
            cls._active_beast_index = 0
            cls._switch_from_beast_key = None
        elif cls._active_beast_index >= len(beast_keys):
            cls._active_beast_index = 0
            cls._switch_from_beast_key = None

    @classmethod
    def reset_rotation_state(cls) -> None:
        cls._selected_beast_keys = cls.BEAST_ORDER
        cls._active_beast_index = 0
        cls._switch_from_beast_key = None

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
            if not self.repeat_rotation:
                return False
            next_index = 0
            completed_rotation = True
        else:
            completed_rotation = False

        type(self)._active_beast_index = next_index
        DemonicBeastFarmer.current_floor = 1
        self._apply_current_beast()
        if completed_rotation:
            print(f"Rotation complete; repeating from {self.current_beast_config.display_name}.")
        else:
            print(f"Switching to {self.current_beast_config.display_name}.")
        return True

    def fight_complete_callback(self, victory=True, phase="unknown"):
        """Called when the active beast fighter completes a floor."""

        with IFarmer._lock:
            cycle_complete = self._record_fight_result(victory, phase, self.current_beast_config.display_name)
            if cycle_complete:
                completed_beast_key = self.active_beast_key
                if self._advance_to_next_beast():
                    type(self)._switch_from_beast_key = completed_beast_key
                    self.current_state = RotationStates.SWITCHING_BEAST
                else:
                    type(self)._switch_from_beast_key = None
                    print("Finished all selected Demonic Beasts, returning to the tavern.")
                    self.current_state = RotationStates.RETURNING_TO_TAVERN
            elif not victory and self.reset_after_defeat:
                self.current_state = DemonicBeastStates.RESETTING_DB
            else:
                self.current_state = DemonicBeastStates.GOING_TO_DB
            self.exit_message()

    def switching_beast_state(self):
        """Select the next beast through shared navigation before resuming farming."""
        screenshot, window_location = capture_window()
        completed_beast_key = type(self)._switch_from_beast_key

        if completed_beast_key is None:
            print(f"No completed beast recorded; looking for {self.current_beast_config.display_name}.")
            self.current_state = DemonicBeastStates.GOING_TO_DB
            return

        # Resume farming only after the selected beast is visible.
        if find(self.db_image, screenshot):
            type(self)._switch_from_beast_key = None
            self.current_state = DemonicBeastStates.GOING_TO_DB
            return

        # Use the same ordered search as the other farmers while staying at beast selection.
        if find(vio.demonic_beast_battle, screenshot):
            navigate_to_demonic_beast(self.db_image, screenshot, window_location)
            return

        print("Returning to beast selection...")
        find_and_click(vio.ok_main_button, screenshot, window_location)
        find_and_click(vio.back, screenshot, window_location)

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
            sleep_seconds=0.6,
        )
