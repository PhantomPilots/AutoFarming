import abc
import copy
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
    is_ground_region,
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

    # Every battle has a floor and a phase, so this should be generalized here
    current_phase = 1
    current_floor = 1

    def __init__(self, battle_strategy: IBattleStrategy, callback: Callable | None = None):
        """Initialize the fighter instance with a (optional) callback to call when the fight has finished,
        and a battle strategy.
        The 'battle strategy' corresponds to the logic that picks the cards to use based on
        the current state of the fight, and should be independent of the type of fight.
        """

        self._lock = threading.Lock()
        with self._lock:
            self.exit_thread = False

        self.battle_strategy: IBattleStrategy = battle_strategy()
        self.complete_callback = callback or (lambda: None)

        self._reset_instance_variables()

    def _reset_instance_variables(self):
        with self._lock:
            self.exit_thread = False
            self.current_state = FightingStates.FIGHTING
            self.available_card_slots = 0
            # The hand will be a tuple of: the list of original cards in hand, and the list of indices to play
            self.current_hand: tuple[list[Card], list[int]] = None
            # Reset the list of picked cards
            self.picked_cards: list[Card] = [Card() for _ in range(6)]  # 6 as a buffer, should be at most 4

    def stop_fighter(self):
        with self._lock:
            print("Manually stopping the fighter thread.")
            self.exit_thread = True
            # Reset the battle strategy turn
            self.battle_strategy.reset_fight_turn()

    def play_cards(self):
        """Read the current hand of cards, and play them based on the available card slots."""

        screenshot, window_location = capture_window()
        empty_card_slots = self.count_empty_card_slots(screenshot)

        # if empty_card_slots == 1:
        #     index_to_play = selected_cards[1][self.available_card_slots - 1]
        #     raise RuntimeError(f"Debugging. Now we should be playing slot index {index_to_play}")

        if empty_card_slots > self.available_card_slots:
            # A patch in case we read the available card slots wrongly earlier
            self.available_card_slots = empty_card_slots

        slot_index = max(0, self.available_card_slots - empty_card_slots)

        if empty_card_slots > 0:
            # KEY: Read the hand of cards here
            current_hand = self.battle_strategy.pick_cards(
                picked_cards=self.picked_cards,
                card_turn=slot_index,
                phase=IFighter.current_phase,
                floor=IFighter.current_floor,
            )

            # Read the card index based on how many empty slots we had at the beginning, and how many we have now
            # TODO: In DOGS, "count_empty_card_slots" doesn't work as well as we want, fixed this somehow.
            print(
                f"Selecting card for slot index {slot_index}, with {empty_card_slots} empty slots.",
            )
            # What is the index in the hand we have to play? It can be an `int` or a `tuple[int, int]`
            try:
                # Always play the first card, since we update the hand after each card play!
                index_to_play = current_hand[1][0]
            except IndexError as e:
                print("slot index:", slot_index, "len indices:", len(current_hand[1]))
                raise e

            # Return the card played to use this in the corresponding fighting strategy
            card_played = self._play_card(
                current_hand[0], index=index_to_play, window_location=window_location, screenshot=screenshot
            )

            # Add this played card to the corresponding slot in picked cards
            self.picked_cards[slot_index] = card_played

        elif empty_card_slots == 0:
            print("Finished my turn!")
            # Increment to the next fight turn
            self.battle_strategy.increment_fight_turn()
            # Reset variables
            self._reset_instance_variables()
            return 1

    def _play_card(
        self,
        list_of_cards: list[Card],
        index: int | tuple[int, int],
        window_location: np.ndarray,
        screenshot: np.ndarray = None,
    ):
        """Decide whether we're clicking or moving a card"""
        if isinstance(index, Integral):
            # print(f"Trying to click on the card with index: {index}...")

            card_to_play = list_of_cards[index]
            if screenshot is not None:
                # If we're provided a screenshot, try to determine if we're clicking on a ground slot
                prev_card: Card = list_of_cards[index - 1]
                while (
                    index != -1
                    and is_ground_region(screenshot, card_to_play.rectangle)
                    and is_ground_region(  # Double check that we have 2 grounds before assuming it's a ground
                        screenshot, prev_card.rectangle
                    )
                ) or (index == 0 and is_ground_region(screenshot, card_to_play.rectangle)):
                    # print("We're clicking on a ground region! We should click on the next card.")
                    index += 1
                    if index >= len(list_of_cards) - 1:
                        # print("Gotta play the rightmost card")
                        card_to_play = list_of_cards[-1]
                        break
                    card_to_play = list_of_cards[index]
                    prev_card: Card = list_of_cards[index - 1]
                    # And retake the screenshot, just in case
                    screenshot, _ = capture_window()

            # Just click on the card
            print("Playing card:", card_to_play.card_type.name, card_to_play.card_rank.name)
            self._click_card(card_to_play, window_location)
            return copy.deepcopy(card_to_play)  # Return the played card, to keep track of it

        else:
            # We have to MOVE the card!
            self._move_card(list_of_cards[index[0]], list_of_cards[index[1]], window_location)
            # Return empty Card
            return Card()

    def _click_card(self, card_to_play: Card, window_location: np.ndarray):
        """Picks the corresponding card from the list, and EATS IT!"""
        rectangle = card_to_play.rectangle
        click_im(rectangle, window_location, sleep_after_click=0.1)

    def _move_card(self, origin_card: Card, target_card: Card, window_location: np.ndarray):
        """Move one card to the other"""
        origin_point = get_click_point_from_rectangle(origin_card.rectangle)
        target_point = get_click_point_from_rectangle(target_card.rectangle)
        drag_im(origin_point, target_point, window_location=window_location, drag_duration=0.5)
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
