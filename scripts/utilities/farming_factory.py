import argparse
import io
import os
import sys

from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer


class FarmingFactory:
    """Since the main loop will be the same for ANY Farmer, we need to decouple this function from
    `main()`, so that when new farmers are defined, only the parameters in the `main()` function of the new
    farming script needs to be defined.

    Check `BirdFarmer.py` for an example.
    """

    @staticmethod
    def main_loop(farmer: IFarmer, starting_state, battle_strategy: IBattleStrategy | None = None, **kwargs):
        """Defined for any subclass of the interface IFarmer, and any subclass of the interface IBattleStrategy"""

        # Extract the password if given
        parser = argparse.ArgumentParser()
        parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
        args = parser.parse_args()

        while True:
            try:
                farmer_instance: IFarmer = farmer(
                    battle_strategy=battle_strategy,
                    starting_state=starting_state,
                    password=args.password,  # Send the given password to the farmer instance
                    **kwargs,  # To set farmer-specific options
                )
                farmer_instance.run()

            except KeyboardInterrupt as e:
                print("Exiting the program.")
                sys.exit(0)

            except Exception as e:
                print(f"An error occurred:\n{e}")
                # Recover the current state the bird farmer was in, and restart from there
                starting_state = farmer_instance.current_state

            finally:
                print("FINALLY:")
                # Call the 'exit message'
                farmer_instance.exit_message()
                # We also need to send a STOP command to the Fighter thread
                farmer_instance.stop_fighter_thread()
