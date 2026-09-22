import threading
import time
from enum import Enum

import numpy as np
import pyautogui as pyautogui
import utilities.vision_images as vio
from utilities.app_config import get_minutes_to_wait_before_login
from utilities.coordinates import Coordinates
from utilities.general_farmer_interface import CHECK_IN_HOUR, IFarmer
from utilities.general_fighter_interface import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    find,
    find_and_click,
)
from utilities.vision import Vision

logger = LoggerWrapper(name="DemonLogger", log_to_file=False)


class States(Enum):
    GOING_TO_DEMONS = 0
    LOOKING_FOR_DEMON = 1
    READY_TO_FIGHT = 2
    FIGHTING_DEMON = 3


class IDemonFarmer(IFarmer):

    # Needs to be static in case we restart the instance
    demons_destroyed = 0

    # We need to keep track if 'auto' is clicked or not...
    auto = False

    # For sending an emoji
    sent_emoji = False

    # For checking if we've seen and missed an invite
    not_seen_invite = False
    start_time_without_invite = time.time()

    # Keep track how many demons we've tried to beat
    num_tries = 0

    # Keep track how many missed invites we've had
    missed_invites = 0

    # To control the sleeping time
    sleeper = threading.Event()

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demon_to_farm: Vision = vio.og_demon,
        time_to_sleep=9.3,
        do_dailies=False,
        do_daily_pvp=True,
        password: str | None = None,
    ):
        super().__init__(do_daily_pvp=do_daily_pvp)

        # Store the account password in this instance if given
        if password:
            IFarmer.password = password
            print("Stored the account password locally in case we need to log in again.")
            print(f"We'll wait {get_minutes_to_wait_before_login()} mins. before attempting a log in.")

        # Starting state
        self.current_state = starting_state

        # Demon to farm
        self.demon_to_farm = demon_to_farm

        # No battle strategy needed, we'll auto
        self.battle_strategy = battle_strategy

        # How much time to sleep before accepting the invitation -- May need to me hand-tuned
        self.sleep_before_accept = time_to_sleep

        # Set specific properties of our DailyFarmer
        IFarmer.daily_farmer.add_complete_callback(self.dailies_complete_callback)

        IFarmer.do_dailies = do_dailies
        if do_dailies:
            print(f"We'll stop farming to do daily missions at {CHECK_IN_HOUR}h PST.")

    def exit_message(self):
        """Final message!"""
        print(
            f"We destroyed {IDemonFarmer.demons_destroyed}/{IDemonFarmer.num_tries} demons and missed {IDemonFarmer.missed_invites} invites."
        )

    def configure_difficulty(self, screenshot, window_location):
        """Select the difficulty used by the public automatic demon flow."""
        find_and_click(vio.hell_difficulty, screenshot, window_location, threshold=0.6)

    def inspect_invitation(self, screenshot, window_location):
        """Allow specialized farmers to inspect an invitation before it is accepted."""

    def on_invitation_accepted(self):
        """Allow specialized farmers to record a successfully accepted invitation."""

    def ensure_fight_started(self, screenshot, window_location):
        """Start or maintain the active fight."""
        if not IDemonFarmer.auto and find_and_click(vio.demons_auto, screenshot, window_location, threshold=0.7):
            IDemonFarmer.auto = True
            IDemonFarmer.sent_emoji = False

    def on_fight_finished(self, victory):
        """Allow specialized farmers to record additional fight results."""

    def stop_active_fight(self):
        """Stop any specialized fighter owned by this farmer."""
        self.stop_fighter_thread()

    def result_demon_label(self):
        """Return an optional label inserted before the word 'demons'."""
        return ""

    def going_to_demons_state(self):
        """Go to the demons page"""
        screenshot, window_location = capture_window()

        if find(vio.demons_auto, screenshot):
            # Going to the fight!
            self.current_state = States.FIGHTING_DEMON
            print(f"We're still fighting, we were wrong!")

        if find(vio.preparation_incomplete, screenshot):
            # We're waiting to click on preparation incomplete!
            self.current_state = States.READY_TO_FIGHT
            print(f"Moving to {self.current_state}.")
            return

        # If we see a 'CANCEL', change the state
        if find(vio.cancel_realtime, screenshot):
            self.current_state = States.LOOKING_FOR_DEMON
            print(f"Moving to {self.current_state}.")
            return

        if self._handle_daily_reset_entrypoint(screenshot, window_location):
            if IFarmer.do_dailies:
                logger.info("We entered the daily reset state!")
            return

        # Click OK if we see it (?)
        if find(vio.ok_main_button, screenshot) and not find(self.demon_to_farm, screenshot):
            find_and_click(vio.ok_main_button, screenshot, window_location, threshold=0.7, sleep_time=1)

        # Go to battle menu
        find_and_click(vio.battle_menu, screenshot, window_location, threshold=0.6, sleep_time=1)

        # Go to demons
        find_and_click(vio.boss_menu, screenshot, window_location, sleep_time=1)

        # Click on real-time menu
        find_and_click(vio.real_time, screenshot, window_location, threshold=0.6, sleep_time=0.2)

        # Click on the demon to farm (if it's not Red, since Red is by default)
        if "red" not in self.demon_to_farm.image_name.lower():
            find_and_click(self.demon_to_farm, screenshot, window_location, sleep_time=0.2)

        self.configure_difficulty(screenshot, window_location)

    def wait_for_accepting_invite(self):
        """Wait for 9 seconds before accepting the invite. This should be a threading event!"""
        print(f"Found a raid! Sleeping for {self.sleep_before_accept} s before clicking...")
        IDemonFarmer.sleeper.clear()  # We have to reset the sleeper event
        IDemonFarmer.sleeper.wait(timeout=self.sleep_before_accept)

    def looking_for_demon_state(self):  # sourcery skip: extract-method
        """Waiting for someone to send us a demon"""
        screenshot, window_location = capture_window()

        # First, if it's time to check in, do it
        if self.check_for_dailies():
            return
        # If we're past the checkin hour, reset the flag for tomorrow
        self.maybe_reset_daily_checkin_flag()

        if find(vio.accept_invitation, screenshot, threshold=0.7):
            # First of all, start the sleeping thread
            sleep_thread = threading.Thread(target=self.wait_for_accepting_invite)
            sleep_thread.start()

            self.inspect_invitation(screenshot, window_location)

            sleep_thread.join()  # Wait for the sleeping thread to finish

            # Need to re-check if 'accept invitation' is there
            accept_screenshot, window_location = capture_window()
            find_and_click(vio.accept_invitation, accept_screenshot, window_location, threshold=0.7)
            time.sleep(3)

            # Evaluate if the invite was successsful
            screenshot, _ = capture_window()
            if find(vio.real_time, screenshot):
                IDemonFarmer.missed_invites += 1
                print(f"We missed the invite :( {IDemonFarmer.missed_invites} invites so far.")
                # And let's save the screenshot we tried to accept on, to see what happened
                logger.save_image(accept_screenshot, subdir="demons")
            else:
                self.on_invitation_accepted()

            return

        if find(vio.demons_loading_screen, screenshot) or find(vio.preparation_incomplete, screenshot):
            # Going to the raid screen
            self.current_state = States.READY_TO_FIGHT
            print(f"Moving to {self.current_state}.")
            return

        if not find(vio.cancel_realtime, screenshot):
            if not IDemonFarmer.not_seen_invite:
                IDemonFarmer.start_time_without_invite = time.time()
                IDemonFarmer.not_seen_invite = True

            if time.time() - IDemonFarmer.start_time_without_invite > 2:  # Only wait 2 seconds
                self.current_state = States.GOING_TO_DEMONS
                IDemonFarmer.not_seen_invite = False

    def ready_to_fight_state(self):
        """We've accepted a raid!"""
        screenshot, window_location = capture_window()

        # If we're ready to fight, send an emoji *only once*
        if not IDemonFarmer.sent_emoji and find(vio.cancel_preparation, screenshot):
            find_and_click(
                vio.cancel_preparation,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("stamp_box"),
                sleep_time=1,
            )
            find_and_click(
                vio.cancel_preparation,
                screenshot,
                window_location,
                point_coordinates=Coordinates.get_coordinates("first_stamp"),
                sleep_time=1,
            )
            IDemonFarmer.sent_emoji = True

        # Click on the "preparation"
        find_and_click(vio.preparation_incomplete, screenshot, window_location, threshold=0.8, sleep_time=1)

        # We may have been kicked, move to initial state if so
        if find(vio.ok_main_button, screenshot) or find(vio.battle_menu, screenshot, threshold=0.6):
            self.current_state = States.GOING_TO_DEMONS
            print(f"We've been kicked out... Moving to {self.current_state}.")
            return

        if find(vio.demons_auto, screenshot):
            # Going to the fight!
            self.current_state = States.FIGHTING_DEMON
            print(f"Moving to {self.current_state}.")

    def fighting_demon_state(self):
        # sourcery skip: extract-duplicate-method, extract-method, split-or-ifs
        """Fighting the demon hard..."""
        screenshot, window_location = capture_window()

        self.ensure_fight_started(screenshot, window_location)

        # If we see a skip
        find_and_click(vio.skip, screenshot, window_location)

        # When we've destroyed the demon
        find_and_click(vio.demons_destroyed, screenshot, window_location, threshold=0.5)

        if find_and_click(vio.ok_main_button, screenshot, window_location) or find(
            vio.battle_menu, screenshot, threshold=0.6
        ):
            IDemonFarmer.num_tries += 1
            victory = find(vio.victory, screenshot, threshold=0.6)
            if victory:
                print("Demon destroyed!")
                IDemonFarmer.demons_destroyed += 1
            else:
                print("Couldn't defeat this demon :(")
                print("[LOSS]")

            self.on_fight_finished(victory)

            IDemonFarmer.auto = False
            self.current_state = States.GOING_TO_DEMONS

            percent = IDemonFarmer.demons_destroyed / IDemonFarmer.num_tries * 100 if IDemonFarmer.num_tries > 0 else 0
            demon_label = self.result_demon_label()

            msg = (
                f"We've destroyed {IDemonFarmer.demons_destroyed}/"
                f"{IDemonFarmer.num_tries}{demon_label} demons "
                f"({percent:.2f}%)."
            )

            print(msg)
            if victory:
                print("[CLEAR]")
            print(f"We've missed {IDemonFarmer.missed_invites} invites.")
            print(f"Moving to {self.current_state}.")

            # And kill the fighter in case we have it
            self.stop_active_fight()

    def dailies_complete_callback(self):
        """The dailies thread told us we're done with all the dailies, go back to farming demons"""
        with IFarmer._lock:
            print("All dailies complete! Going back to farming demons.")
            IFarmer.dailies_thread = None
            self.current_state = States.GOING_TO_DEMONS

    def run(self):
        raise NotImplementedError("Virtual method. Need to implement this method in a derived class.")


class DemonFarmer(IDemonFarmer):
    """This class resets the demon to farm every X hours"""

    def __init__(
        self,
        battle_strategy: IBattleStrategy = None,
        starting_state=States.GOING_TO_DEMONS,
        demons_to_farm: list[Vision] = None,
        time_to_sleep=9.4,
        time_between_demons=2,
        do_dailies=False,  # Do we halt demon farming to do dailies?
        do_daily_pvp=True,  # If we do dailies, do we do PVP?
        password: str = None,
    ):
        if demons_to_farm is None:
            demons_to_farm = [vio.og_demon]

        # Initialize the DemonFarmer with the first demon of the list
        super().__init__(
            battle_strategy,
            starting_state,
            demons_to_farm[0],
            time_to_sleep,
            do_dailies=do_dailies,
            do_daily_pvp=do_daily_pvp,
            password=password,
        )

        # Every how many hours to switch between demons
        self.time_between_demons = time_between_demons

        # Roulette of demons
        self.demon_roulette = demons_to_farm
        self.start_time = time.time()

    def rotate_demon(self):
        """Rotate a demon if X hours have passed"""

        if time.time() - self.start_time > self.time_between_demons * 3600:
            # Increase the index by one
            demon_names: list[str] = [demon.image_name for demon in self.demon_roulette]
            demon_idx = np.where(np.array(demon_names) == self.demon_to_farm.image_name)[0] + 1
            demon_idx = int(demon_idx % len(self.demon_roulette))

            # Update the new demon to farm
            new_demon_to_farm = self.demon_roulette[demon_idx]
            if new_demon_to_farm != self.demon_to_farm:
                self.demon_to_farm = new_demon_to_farm
                logger.info(f"Switched demon to {self.demon_to_farm.image_name}")

            # Record the new time
            self.start_time = time.time()

    def run(self):

        print(f"Farming demons, starting from {self.current_state}.")
        print(f"We'll be farming {[demon.image_name for demon in self.demon_roulette]} demon(s).")

        def fighting_demon_state():
            self.fighting_demon_state()
            time.sleep(0.2)

        self.run_state_loop(
            {
                States.GOING_TO_DEMONS: self.going_to_demons_state,
                States.LOOKING_FOR_DEMON: self.looking_for_demon_state,
                States.READY_TO_FIGHT: self.ready_to_fight_state,
                States.FIGHTING_DEMON: fighting_demon_state,
            },
            login_return_state=States.GOING_TO_DEMONS,
            sleep_seconds=0.01,
        )

    def before_state_loop_iteration(self) -> None:
        self.rotate_demon()
