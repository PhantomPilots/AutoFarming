import abc

from utilities.general_fighter_interface import IFighter


class IFarmer:
    """Generic farmer interface."""

    # For type helping
    current_state: int
    fighter: IFighter
    stamina_pots: int = 0

    def stop_fighter_thread(self):
        """Send a STOP signal to the IFighter thread"""
        if hasattr(self, "fighter") and isinstance(self.fighter, IFighter):
            print("STOPPING FIGHTER!")
            self.fighter.stop_fighter()

    def exit_message(self):
        """Final message to display on the screen when CTRL+C happens"""
        print(f"We used {IFarmer.stamina_pots} stamina pots.")

    def fight_complete_callback(self, **kwargs):
        """Callback used for the fighter to notify the farmer when the fight has ended.
        Not abstract since not all farmers use a fighter, and therefore a 'fight complete callback'.
        """

    @abc.abstractmethod
    def run(self):
        """Needs to be implemented by a subclass"""
