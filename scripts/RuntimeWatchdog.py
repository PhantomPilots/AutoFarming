from utilities.utilities import get_config, send_push_notification
import time

class RuntimeWatchdog:
    def __init__(self):
        self.heartbeat_interval = get_config("heartbeat_interval", 300)  # seconds
        self.repeated_messages_threshold = get_config("repeated_messages_threshold", 20)
        self.unrecoverable_error_messages = get_config("unrecoverable_error_messages", [])

        self.last_heartbeat = None
        self.last_message = None
        self.repeated_message_count = 0
        self.watching = False

        self.notifications_for_messages = set()  # To track which messages have already triggered notifications

    def _check_unrecoverable_errors(self, new_lines):
        for line in new_lines:
            normalized_line = line.strip().lower()
            for error_message in self.unrecoverable_error_messages:
                if error_message.lower() in normalized_line:
                    notification_key = f"unrecoverable::{error_message}"
                    if notification_key not in self.notifications_for_messages:
                        send_push_notification(f"Unrecoverable error detected: {line.strip()}")
                        self.notifications_for_messages.add(notification_key)

    def terminal_heartbeat(self, new_lines):
        if not self.watching:
            return
        
        # remove heartbeat lines from new_lines
        new_lines[:] = [line for line in new_lines if "[Heartbeat]" not in line]
        self.last_heartbeat = time.time()

        self._check_unrecoverable_errors(new_lines)

        if new_lines:
            last_line = new_lines[-1].strip()
            if last_line == self.last_message:
                self.repeated_message_count += 1
            else:
                self.last_message = last_line
                self.repeated_message_count = 0

            if self.repeated_message_count >= self.repeated_messages_threshold:
                if last_line not in self.notifications_for_messages:
                    send_push_notification(f"The same message has been repeated {self.repeated_message_count} times. The bot may be stuck. Last message: {last_line}")
                    self.notifications_for_messages.add(last_line)
                self.repeated_message_count = 0  # Reset count after notification

    def check_heartbeat(self):
        if not self.watching:
            return

        current_time = time.time()
        if self.last_heartbeat is not None and (current_time - self.last_heartbeat) > self.heartbeat_interval:
            send_push_notification(f"No heartbeat received in the last {self.heartbeat_interval} seconds. The bot may be unresponsive.")
            self.last_heartbeat = current_time  # Reset heartbeat to avoid repeated notifications

    def start(self):
        self.last_heartbeat = time.time()
        self.watching = True
        self.notifications_for_messages.clear()  # Clear notifications when starting
        print("Runtime Watchdog started.")

    def stop(self):
        self.watching = False
        print("Runtime Watchdog stopped.")