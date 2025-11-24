import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.coordinates import Coordinates
from utilities.demonic_beast_farming_logic import DemonicBeastFarmer, States
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.logging_utils import LoggerWrapper
from utilities.rat_fighter import IFighter, RatFighter
from utilities.utilities import crop_image, find, screenshot_testing

logger = LoggerWrapper(name="RatLogger", log_file="rat_logger.log")


class RatFarmer(DemonicBeastFarmer):

    def __init__(
        self,
        battle_strategy: IBattleStrategy,
        starting_state=States.GOING_TO_DB,
        max_stamina_pots="inf",
        num_floor_3_clears="inf",
        reset_after_defeat=False,
        logger=logger,
        password: str | None = None,
        do_dailies=False,
    ):
        super().__init__(
            starting_state=starting_state,
            max_stamina_pots=max_stamina_pots,
            max_floor_3_clears=num_floor_3_clears,
            reset_after_defeat=reset_after_defeat,
            demonic_beast_image=vio.ratatoskr,
            logger=logger,
            password=password,
            do_dailies=do_dailies,
        )

        # Using composition to decouple the main farmer logic from the actual fight.
        # Pass in the callback to call after the fight is complete.
        self.fighter: IFighter = RatFighter(
            battle_strategy=battle_strategy,
            callback=self.fight_complete_callback,
        )

    def determine_db_floor(self, screenshot: np.ndarray, threshold=0.8) -> int:
        """Determine the Demonic Beast floor"""
        # sourcery skip: assign-if-exp, reintroduce-else
        floor_img_region = crop_image(
            screenshot,
            Coordinates.get_coordinates("floor_top_left"),
            Coordinates.get_coordinates("floor_bottom_right"),
        )

        # display_image(floor_img_region)
        # screenshot_testing(floor_img_region, vio.floor2, threshold=threshold)

        # Default
        db_floor = -1

        if find(vio.floor2, floor_img_region, threshold=threshold):
            db_floor = 2
        elif find(vio.floor1, floor_img_region, threshold=threshold):
            db_floor = 1

        print(f"We're gonna fight floor {db_floor}.")

        return db_floor

    def fight_complete_callback(self, victory=True, phase="unknown"):
        """Called when the fight logic completes."""

        with IFarmer._lock:
            if victory:
                DemonicBeastFarmer.num_victories += 1

                print(f"Floor {DemonicBeastFarmer.current_floor} complete!")

                self.current_state = States.RESETTING_DB

                # Update the floor number
                DemonicBeastFarmer.current_floor = (DemonicBeastFarmer.current_floor % 3) + 1

                # Transition to another state or perform clean-up actions
                if DemonicBeastFarmer.current_floor == 3:  # Since we updated it already beforehand!
                    DemonicBeastFarmer.num_floor_3_victories += 1

                    # Check if we need to exit the farmer due to reaching the max number of desired floor 3 clears
                    if DemonicBeastFarmer.num_floor_3_victories >= self.max_floor_3_clears:
                        print("We've reached the desired number of floor 3 clears, closing the farmer.")
                        self.current_state = States.EXIT_FARMER
                    else:
                        # Just reset the team
                        print("We defeated floor 2, gotta reset the DB.")
                        self.current_state = States.RESETTING_DB

                else:
                    # Go straight to the original states
                    print("Moving to GOING_TO_DB")
                    self.current_state = States.GOING_TO_DB

            else:
                print("The Demonic Beast fighter told me we lost... :/")
                # print("Resetting the team in case the saved team has very little health")
                DemonicBeastFarmer.num_losses += 1
                IFarmer.dict_of_defeats[f"Floor {DemonicBeastFarmer.current_floor} Phase {phase}"] += 1

                if self.reset_after_defeat:
                    self.current_state = States.RESETTING_DB
                else:
                    self.current_state = States.GOING_TO_DB

            self.exit_message()
