import logging
import os
import threading


class LoggerWrapper:
    _lock = threading.Lock()  # Static lock shared among all instances

    def __init__(self, name: str, log_file: str, level: int = logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create a file handler specific to this log file
        if not self.logger.hasHandlers():  # Avoid adding multiple handlers
            os.makedirs("logs", exist_ok=True)
            file_handler = logging.FileHandler(os.path.join("logs", log_file))
            file_handler.setLevel(level)

            # Create a formatter and set it to the handler
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)

            # Add the handler to the logger
            self.logger.addHandler(file_handler)

    def debug(self, message: str):
        print(message)
        with LoggerWrapper._lock:
            self.logger.debug(message)

    def info(self, message: str):
        print(message)
        with LoggerWrapper._lock:
            self.logger.info(message)

    def warning(self, message: str):
        print(message)
        with LoggerWrapper._lock:
            self.logger.warning(message)

    def error(self, message: str):
        print(message)
        with LoggerWrapper._lock:
            self.logger.error(message)

    def critical(self, message: str):
        print(message)
        with LoggerWrapper._lock:
            self.logger.critical(message)
