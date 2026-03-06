import sys
import threading
import time

from utilities.fighting_strategies import IBattleStrategy
from utilities.general_farmer_interface import IFarmer
from utilities.utilities import (
    get_consecutive_click_info,
    get_config,
    get_last_click_time,
    re_open_7ds_window,
    reset_click_pattern_tracking,
    reset_last_click_time,
    send_push_notification,
)


class FarmingFactory:
    """Since the main loop will be the same for ANY Farmer, we need to decouple this function from
    `main()`, so that when new farmers are defined, only the parameters in the `main()` function of the new
    farming script needs to be defined.

    Check `BirdFarmer.py` for an example.
    """

    @staticmethod
    def _runtime_monitor(runtime_context: dict, runtime_context_lock: threading.Lock, stop_event: threading.Event):
        poll_interval_seconds = float(get_config("runtime_watchdog_poll_interval_seconds", 1.0))
        state_stagnation_timeout_minutes = float(get_config("state_stagnation_timeout_minutes", 10))
        click_idle_timeout_minutes = float(get_config("click_idle_timeout_minutes", 3))
        notification_cooldown_minutes = float(get_config("stuck_notification_cooldown_minutes", 5))
        repeated_click_same_image_threshold = int(get_config("repeated_click_same_image_threshold", 0))

        state_timeout_seconds = max(0.0, state_stagnation_timeout_minutes * 60)
        click_timeout_seconds = max(0.0, click_idle_timeout_minutes * 60)
        notification_cooldown_seconds = max(30.0, notification_cooldown_minutes * 60)

        last_state = None
        last_state_transition_time = time.time()
        last_stuck_notification_time = 0.0
        monitor_started_at = time.time()

        while not stop_event.wait(timeout=max(0.1, poll_interval_seconds)):
            now = time.time()

            with runtime_context_lock:
                farmer_instance = runtime_context.get("farmer_instance")

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

            last_click_time = get_last_click_time()
            click_reference_time = last_click_time if last_click_time is not None else monitor_started_at

            state_stagnant = state_timeout_seconds > 0 and (now - last_state_transition_time) >= state_timeout_seconds
            click_idle = click_timeout_seconds > 0 and (now - click_reference_time) >= click_timeout_seconds
            last_clicked_image_name, consecutive_click_count = get_consecutive_click_info()
            repeated_click_pattern = (
                repeated_click_same_image_threshold > 0
                and consecutive_click_count >= repeated_click_same_image_threshold
                and state_stagnant
            )

            should_notify_stuck = (state_stagnant and click_idle) or repeated_click_pattern

            if should_notify_stuck and (now - last_stuck_notification_time) >= notification_cooldown_seconds:
                stagnant_minutes = (now - last_state_transition_time) / 60
                idle_minutes = (now - click_reference_time) / 60
                repeated_click_msg = ""
                if repeated_click_pattern:
                    repeated_click_msg = (
                        f" Repeated click pattern: '{last_clicked_image_name}' clicked "
                        f"{consecutive_click_count} times in a row."
                    )

                if click_idle:
                    base_message = (
                        "Potential stuck bot detected: state and click activity are both stale. "
                        f"State unchanged for {stagnant_minutes:.1f}m and no successful click for {idle_minutes:.1f}m. "
                    )
                else:
                    base_message = (
                        "Potential stuck bot detected: state appears stagnant with repeated click behavior. "
                        f"State unchanged for {stagnant_minutes:.1f}m. "
                    )

                send_push_notification(
                    f"{base_message}Current state: {current_state}.{repeated_click_msg}"
                )
                last_stuck_notification_time = now

    @staticmethod
    def main_loop(farmer: IFarmer, starting_state, battle_strategy: IBattleStrategy | None = None, **kwargs):
        """Defined for any subclass of the interface IFarmer, and any subclass of the interface IBattleStrategy"""
        runtime_context_lock = threading.Lock()
        runtime_context = {
            "farmer_instance": None,
        }

        reset_click_pattern_tracking()
        reset_last_click_time(time.time())

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
                        **kwargs,  # To set farmer-specific options
                    )

                    with runtime_context_lock:
                        runtime_context["farmer_instance"] = farmer_instance

                    farmer_instance.run()

                except KeyboardInterrupt as e:
                    print(f"{e}: Exiting the program.")
                    break

                except Exception as e:
                    print(f"An error occurred:\n{e}")

                    # Recover the current state the farmer was in, and restart from there
                    if farmer_instance is not None and hasattr(farmer_instance, "current_state"):
                        starting_state = farmer_instance.current_state

                    # Re-open the 7DS window if it has been closed
                    if game_opened := re_open_7ds_window():
                        print("Re-opened the game, we'll try to login immediately!")
                        IFarmer.first_login = True

                finally:
                    with runtime_context_lock:
                        runtime_context["farmer_instance"] = None

                    print("FINALLY:")
                    # Call the 'exit message'
                    if farmer_instance is not None and hasattr(farmer_instance, "exit_message"):
                        farmer_instance.exit_message()

                    # We also need to send a STOP command to the Fighter thread
                    if farmer_instance is not None and hasattr(farmer_instance, "stop_fighter_thread"):
                        farmer_instance.stop_fighter_thread()

        finally:
            runtime_monitor_stop_event.set()
            runtime_monitor_thread.join(timeout=2)
            sys.exit(0)
