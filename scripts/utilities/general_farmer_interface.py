import abc

from utilities.fighting_strategies import IBattleStrategy


class IFarmer:
    """Generic farmer interface."""

    def __init__(self, battle_strategy: IBattleStrategy, starting_state: int, **kargs):

        # For type helping
        self.current_state: int
        self.battle_strategy: IBattleStrategy

        raise NotImplementedError(
            "__init__ method should be defined by subclasses, with these two parameters: battle_strategy and starting_state"
        )

    def exit_message(self):
        """Final message to display on the screen when CTRL+C happens"""

    def fight_complete_callback(self, victory=True):
        """Callback used for the fighter to notify the farmer when the fight has ended.
        Not abstract since not all farmers use a fighter, and therefore a 'fight complete callback'.
        """

    @abc.abstractmethod
    def run(self):
        """Needs to be implemented by a subclass"""
