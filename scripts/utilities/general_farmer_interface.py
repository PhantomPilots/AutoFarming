import abc

from utilities.fighting_strategies import IBattleStrategy


class IFarmer:
    """Generic farmer interface."""

    def __init__(self, battle_strategy: IBattleStrategy, starting_state: int):

        # For type helping
        self.current_state: int
        self.battle_strategy: IBattleStrategy

        raise NotImplementedError(
            "__init__ method should be defined by subclasses, with these two parameters: battle_strategy and starting_state"
        )

    def exit_message(self):
        """Final message to display on the screen when CTRL+C happens"""

    @abc.abstractmethod
    def run(self):
        """Needs to be implemented by a subclass"""
