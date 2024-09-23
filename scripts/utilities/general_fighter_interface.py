import abc
import logging
import threading
import time
from enum import Enum
from numbers import Integral
from typing import Callable

import numpy as np
from utilities.card_data import Card
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_hand_image,
    capture_window,
    click_im,
    display_image,
    drag_im,
    get_click_point_from_rectangle,
    get_hand_cards,
    is_ground_card,
)

logger = LoggerWrapper("FighterLogger", "fighter.log", level=logging.DEBUG)


class FightingStates(Enum):
    # Ideally they should be the same states for ANY Fighter subclass
    FIGHTING = 0
    FIGHTING_COMPLETE = 1
    MY_TURN = 2
    DEFEAT = 3
    EXIT_FIGHT = 4


class IFighter(abc.ABC):
    """Interface that will encompass all different types of fights (Demonic beasts, KH boss, FB boss...)"""

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None):
        """Initialize the fighter instance with a (optional) callback to call when the fight has finished,
        and a battle strategy.
        The 'battle strategy' corresponds to the logic that picks the cards to use based on
        the current state of the fight, and should be independent of the type of fight.
        """

        self._lock = threading.Lock()
        self.exit_thread = False
        self.battle_strategy: IBattleStrategy = battle_strategy()
        self.complete_callback = callback or (lambda: None)

        self._reset_instance_variables()

    def _reset_instance_variables(self):
        self.exit_thread = False
        self.current_state = FightingStates.FIGHTING
        self.available_card_slots = 0
        # The hand will be a tuple of: the list of original cards in hand, and the list of indices to play
        self.current_hand: tuple[list[Card], list[int]] = None

    def stop_fighter(self):
        with self._lock:
            print("An error occurred, closing the fighter thread!")
            self.exit_thread = True

    def play_cards(self, selected_cards: tuple[list[Card], list[int | tuple[int, int]]]):
        """Click on the cards from the picked cards to play.

        Args:
            selected_cards (tuple[list[Card], list[int]]): A tuple of two elements: The first is the original list of cards,
                                                           the second one is the list of indices to click on.
        """

        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot)

        # if empty_card_slots == 1:
        #     raise RuntimeError("Debugging")

        if empty_card_slots > self.available_card_slots:
            # A patch in case we read the available card slots wrongly earlier
            self.available_card_slots = empty_card_slots

        if empty_card_slots > 0 and len(selected_cards[1]) >= empty_card_slots:
            # Read the card index based on how many empty slots we had at the beginning, and how many we have now
            # TODO: In DOGS, "count_empty_card_slots" doesn't work as well as we want, fixed this somehow.
            slot_index = self.available_card_slots - empty_card_slots
            print("Selecting card for slot index", slot_index)
            # What is the index in the hand we have to play? I can be an `int` or a `tuple[int, int]`
            try:
                index_to_play = selected_cards[1][slot_index]
            except IndexError as e:
                print("slot index:", slot_index, "len indices:", len(selected_cards[1]))
                raise e

            self._play_card(selected_cards[0], index=index_to_play, window_location=window_location)

        elif empty_card_slots == 0:
            print("Finished my turn!")
            return 1

    def _play_card(self, list_of_cards: list[Card], index: int | tuple[int, int], window_location: np.ndarray):
        """Decide whether we're clicking or moving a card"""
        if isinstance(index, Integral):
            # Just click on the card
            print("Clicking card with index:", index)
            self._click_card(list_of_cards[index], window_location)

        else:
            # We have to MOVE the card!
            self._move_card(list_of_cards[index[0]], list_of_cards[index[1]], window_location)

    def _click_card(self, card_to_play: Card, window_location: np.ndarray):
        """Picks the corresponding card from the list, and EATS IT!"""
        rectangle = card_to_play.rectangle
        click_im(rectangle, window_location, sleep_after_click=0.05)

    def _move_card(self, origin_card: Card, target_card: Card, window_location: np.ndarray):
        """Move one card to the other"""
        origin_point = get_click_point_from_rectangle(origin_card.rectangle)
        target_point = get_click_point_from_rectangle(target_card.rectangle)
        drag_im(origin_point, target_point, window_location=window_location, drag_duration=0.2)
        time.sleep(0.2)

    @staticmethod
    def run_wrapper(func: Callable):
        """Wrapper to the `run` function to ensure proper clean-up of attributes,
        no matter the subclass implementation of `run`.
        NOTE: This decorator should be used on the `run()` method of all subclasses.
        """

        def wrapper_func(self: IFighter, *args, **kwargs):
            # Call the original function
            func(self, *args, **kwargs)

            # Clean up the attributes by resetting them, in case the subclass instance is reused
            print("Resetting fighter...")
            self._reset_instance_variables()

        return wrapper_func

    @abc.abstractmethod
    def my_turn_state(self):
        """State in which the 4 cards will be picked and clicked.
        Needs to be implemented by subclasses.
        """

    @staticmethod
    @abc.abstractmethod
    def count_empty_card_slots(screenshot, threshold=0.7):
        """Count how many card slots are there. Needs to be overriden, because it's very fight-specific!"""

    @abc.abstractmethod
    def run(self, **kwargs):
        """Main fighter state machine.
        Needs to be implemented by subclasses.
        """
