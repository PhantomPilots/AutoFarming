import logging
import os
from logging import Logger


class MyLogger:

    def __init__(self, log_filename: str):
        # Configure the logger
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        # Configure the logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(message)s",
            filename=os.path.join(logs_dir, log_filename),
            filemode="a",  # 'a' for append mode if you want to continue logging to the same file
        )

        # Create a logger instance
        self.logger = logging.getLogger()

    def __call__(self):
        return self.logger
