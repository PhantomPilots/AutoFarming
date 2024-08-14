import abc
from enum import Enum
from typing import Callable

import numpy as np
from utilities.card_data import Card
from utilities.fighting_strategies import IBattleStrategy
from utilities.utilities import click_im, count_empty_card_slots


class FightingStates(Enum):
    # Ideally they should be the same states for ANY Fighter subclass
    FIGHTING = 0
    FIGHTING_COMPLETE = 1
    MY_TURN = 2
    DEFEAT = 3


class IFighter(abc.ABC):
    """Interface that will encompass all different types of fights (Demonic beasts, KH boss, FB boss...)"""

    # Static in case we want to set it to True it with a `signal`
    exit_thread = False

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None):
        """Initialize the fighter instance with a (optional) callback to call when the fight has finished,
        and a battle strategy.
        The 'battle strategy' corresponds to the logic that picks the cards to use based on
        the current state of the fight, and should be independent of the type of fight.
        """

        self.battle_strategy: IBattleStrategy = battle_strategy()
        self.complete_callback = callback or (lambda: None)
        self._reset_instance_variables()

    def _reset_instance_variables(self):
        IFighter.exit_thread = False
        self.current_state = FightingStates.FIGHTING
        self.available_card_slots = 0
        self.current_hand: list[Card] | None = None

    @staticmethod
    def _signal_hander(*args):
        IFighter.exit_thread = True

    def play_cards(self, selected_cards: list[Card], screenshot: np.ndarray, window_location: np.ndarray):
        """Click on the cards from the picked cards to play."""

        empty_card_slots = count_empty_card_slots(screenshot)
        # if empty_card_slots == 1:
        #     raise ValueError("debugging")

        if empty_card_slots > self.available_card_slots:
            # A patch in case we read the available card slots wrongly earlier
            self.available_card_slots = empty_card_slots

        if empty_card_slots > 0 and len(selected_cards) >= empty_card_slots:
            # Compute the card index based on how many empty slots we had at the beginning, and how many we have now
            card_index = self.available_card_slots - empty_card_slots
            print("Playing card...")
            self._play_card(selected_cards, card_index, window_location)

    def _play_card(self, selected_cards: list[Card], idx: int, window_location: np.ndarray):
        """Picks the corresponding card from the list, and EATS IT!
        TODO: Account for manual card merges, how to do that?"""
        rectangle = selected_cards[idx].rectangle
        click_im(rectangle, window_location, sleep_after_click=0.05)

    @staticmethod
    def run_wrapper(func: Callable):
        """Wrapper to the `run` function to ensure proper clean-up of attributes,
        no matter the subclass implementation of `run`.
        NOTE: This decorator should be used on the `run()` method of all subclasses.
        """

        def wrapper_func(self: IFighter):
            # Call the original function
            func(self)

            # Clean up the attributes by resetting them, in case the subclass instance is reused
            print("Resetting fighter...")
            self._reset_instance_variables()

        return wrapper_func

    @abc.abstractmethod
    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked.
        Needs to be implemented by subclasses.
        """

    @abc.abstractmethod
    def run(self):
        """Main fighter state machine.
        Needs to be implemented by subclasses.
        """
