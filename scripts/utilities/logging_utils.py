import logging
import os
import threading
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image


class LoggerWrapper:
    _lock = threading.Lock()  # Static lock shared among all instances

    def __init__(self, name: str, log_file: str = "", level: int = logging.DEBUG, log_to_file: bool = False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # prevent double logging via root handlers

        if not self.logger.hasHandlers():
            # Centralize timestamping here; no manual timestamps elsewhere
            formatter = logging.Formatter(
                fmt="%(asctime)s %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            if log_to_file and log_file:
                os.makedirs("logs", exist_ok=True)
                file_handler = logging.FileHandler(os.path.join("logs", log_file))
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(level)
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    # Log methods now pass messages directly—no manual timestamps
    def debug(self, message: str):
        with LoggerWrapper._lock:
            self.logger.debug(message)

    def info(self, message: str):
        with LoggerWrapper._lock:
            self.logger.info(message)

    def warning(self, message: str):
        with LoggerWrapper._lock:
            self.logger.warning(message)

    def error(self, message: str):
        with LoggerWrapper._lock:
            self.logger.error(message)

    def critical(self, message: str):
        with LoggerWrapper._lock:
            self.logger.critical(message)

    def save_image(
        self,
        image,
        name: str | None = None,
        subdir: str = "images",
        assume_bgr: bool = True,
    ) -> str:
        """
        Save an image as PNG under logs/<subdir>/ with a timestamped filename.

        Accepts:
          - NumPy arrays (H,W), (H,W,3), or (H,W,4) in uint8 (BGR/BGRA or RGB/RGBA)
          - PIL.Image.Image

        Returns:
          Absolute path to the saved file.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = f"{name or 'img'}_{ts}.png"
        out_dir = os.path.join("logs", subdir)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.abspath(os.path.join(out_dir, base))

        # Normalize to PIL Image
        if isinstance(image, np.ndarray):
            arr = image

            # Validate shape
            if arr.ndim == 2:
                # Grayscale
                pass
            elif arr.ndim == 3 and arr.shape[2] in (3, 4):
                if assume_bgr:
                    arr = arr[:, :, ::-1] if arr.shape[2] == 3 else arr[:, :, [2, 1, 0, 3]]
                    # else: already RGB/RGBA
            else:
                raise TypeError("Unsupported ndarray shape; expected (H,W), (H,W,3), or (H,W,4).")

            # Ensure dtype and contiguity
            if arr.dtype != np.uint8:
                arr = np.clip(arr, 0, 255).astype(np.uint8)
            arr = np.ascontiguousarray(arr)

            pil_im = Image.fromarray(arr)

        elif isinstance(image, Image.Image):
            pil_im = image
        else:
            raise TypeError("Unsupported image type; provide a NumPy array or a PIL.Image.Image.")

        # Save
        with LoggerWrapper._lock:
            pil_im.save(out_path, format="PNG")
            self.logger.info(f"Saved image -> {out_path}")

        return out_path
