import sys
import threading
import time

from utilities.app_config import click_tracker, config
from utilities.capture_window import capture_window
from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import re_open_7ds_window, send_push_notification

_POLL_INTERVAL_SECONDS = 2.0
_REPEATED_CLICK_THRESHOLD = 30


class FarmingFactory:
    """Since the main loop will be the same for ANY Farmer, we need to decouple this function from
    `main()`, so that when new farmers are defined, only the parameters in the `main()` function of the new
    farming script needs to be defined.

    Check `BirdFarmer.py` for an example.
    """

    @staticmethod
    def _runtime_monitor(runtime_context: dict, runtime_context_lock: threading.Lock, stop_event: threading.Event):
        stuck_timeout_seconds = max(0.0, float(config.get("stuck_timeout_minutes", 10)) * 60)
        notification_cooldown_seconds = max(30.0, float(config.get("notification_cooldown_minutes", 5)) * 60)
        max_notifications = int(config.get("max_notifications_per_incident", 5))

        last_state = None
        last_state_transition_time = time.time()
        monitor_started_at = time.time()

        # Incident tracking
        incident_active = False
        incident_start_time = 0.0
        incident_notification_count = 0
        last_notification_time = 0.0

        while not stop_event.wait(timeout=_POLL_INTERVAL_SECONDS):
            now = time.time()

            with runtime_context_lock:
                farmer_instance = runtime_context.get("farmer_instance")
                should_reset = runtime_context.pop("reset_monitor", False)

            if should_reset:
                last_state = None
                last_state_transition_time = now
                monitor_started_at = now
                incident_active = False
                incident_start_time = 0.0
                incident_notification_count = 0
                last_notification_time = 0.0
                continue

            if farmer_instance is None:
                continue

            keepalive_deadline_getter = getattr(farmer_instance, "get_keepalive_deadline", None)
            keepalive_deadline = keepalive_deadline_getter() if callable(keepalive_deadline_getter) else 0.0
            if keepalive_deadline > now:
                last_state_transition_time = now
                monitor_started_at = now
                continue

            current_state = getattr(farmer_instance, "current_state", None)
            if current_state != last_state:
                last_state = current_state
                last_state_transition_time = now

            last_click_time, last_image_name, consecutive_clicks, last_image_click_time = click_tracker.get_state()
            click_reference_time = last_click_time if last_click_time is not None else monitor_started_at

            state_stagnant = stuck_timeout_seconds > 0 and (now - last_state_transition_time) >= stuck_timeout_seconds
            click_idle = stuck_timeout_seconds > 0 and (now - click_reference_time) >= stuck_timeout_seconds
            repeated_click_pattern = (
                consecutive_clicks >= _REPEATED_CLICK_THRESHOLD
                and state_stagnant
                and last_image_click_time is not None
                and (now - last_image_click_time) < stuck_timeout_seconds
            )

            is_stuck = (state_stagnant and click_idle) or repeated_click_pattern

            if is_stuck and not incident_active:
                incident_active = True
                incident_start_time = now
                incident_notification_count = 0

            if incident_active and not is_stuck:
                if incident_notification_count > 0:
                    duration_minutes = (now - incident_start_time) / 60
                    send_push_notification(
                        f"Bot recovered — now in state {current_state}. " f"Incident lasted {duration_minutes:.1f}m."
                    )
                incident_active = False
                incident_notification_count = 0
                continue

            if not incident_active:
                continue

            capped = incident_notification_count >= max_notifications
            cooldown_ok = (now - last_notification_time) >= notification_cooldown_seconds

            if not capped and cooldown_ok:
                stagnant_minutes = (now - last_state_transition_time) / 60
                idle_minutes = (now - click_reference_time) / 60

                repeated_click_msg = ""
                if repeated_click_pattern:
                    repeated_click_msg = (
                        f" Repeated click pattern: '{last_image_name}' clicked " f"{consecutive_clicks} times in a row."
                    )

                if click_idle:
                    base_message = (
                        f"Bot stuck: state unchanged for {stagnant_minutes:.1f}m, " f"no click for {idle_minutes:.1f}m."
                    )
                else:
                    base_message = (
                        f"Bot stuck: state unchanged for {stagnant_minutes:.1f}m " f"with repeated click behavior."
                    )

                message = f"{base_message} State: {current_state}.{repeated_click_msg}"

                try:
                    screenshot, _ = capture_window()
                except Exception:
                    screenshot = None

                send_push_notification(message, screenshot=screenshot)
                incident_notification_count += 1
                last_notification_time = now

    @staticmethod
    def main_loop(farmer: IFarmer, starting_state, battle_strategy: IBattleStrategy | None = None, **kwargs):
        """Defined for any subclass of the interface IFarmer, and any subclass of the interface IBattleStrategy"""
        runtime_context_lock = threading.Lock()
        runtime_context: dict = {"farmer_instance": None}

        click_tracker.reset()

        runtime_monitor_stop_event = threading.Event()
        runtime_monitor_thread = threading.Thread(
            target=FarmingFactory._runtime_monitor,
            args=(runtime_context, runtime_context_lock, runtime_monitor_stop_event),
            daemon=True,
        )
        runtime_monitor_thread.start()

        try:
            while True:
                farmer_instance: IFarmer | None = None
                try:
                    farmer_instance = farmer(
                        battle_strategy=battle_strategy,
                        starting_state=starting_state,
                        **kwargs,
                    )

                    with runtime_context_lock:
                        runtime_context["farmer_instance"] = farmer_instance
                        runtime_context["reset_monitor"] = True

                    click_tracker.reset()
                    farmer_instance.run()

                except KeyboardInterrupt as e:
                    print(f"{e}: Exiting the program.")
                    break

                except Exception as e:
                    print(f"An error occurred:\n{e}")

                    if farmer_instance is not None and hasattr(farmer_instance, "current_state"):
                        starting_state = farmer_instance.current_state

                    if game_opened := re_open_7ds_window():
                        print("Re-opened the game, we'll try to login immediately!")
                        IFarmer.first_login = True

                finally:
                    with runtime_context_lock:
                        runtime_context["farmer_instance"] = None

                    print("FINALLY:")
                    if farmer_instance is not None and hasattr(farmer_instance, "exit_message"):
                        farmer_instance.exit_message()

                    if farmer_instance is not None and hasattr(farmer_instance, "stop_fighter_thread"):
                        farmer_instance.stop_fighter_thread()

        finally:
            runtime_monitor_stop_event.set()
            runtime_monitor_thread.join(timeout=2)
            sys.exit(0)
