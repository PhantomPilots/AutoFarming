import os

import cv2
import numpy as np
from termcolor import cprint
from utilities.pattern_match_strategies import (
    IMatchingStrategy,
    TemplateMatchingStrategy,
)


class Vision:
    """Needle class"""

    def __init__(self, needle_basename, matching_strategy: IMatchingStrategy = TemplateMatchingStrategy):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        needle_path = os.path.join("images", needle_basename)

        self.needle_img = cv2.imread(needle_path)
        if self.needle_img is None:
            cprint(f"No image can be found for '{needle_basename}'", "yellow")
            return

        # Save the pattern matching strategy as an attribute
        self.matching_strategy = matching_strategy

        # Save the name of the needle image
        self.image_name = os.path.basename(needle_basename).split(".")[0]

    def find(self, haystack_img, threshold=0.5) -> np.ndarray:
        """Run the defined pattern matching strategy.

        Returns:
            np.ndarray: 1-D numpy array of shape (4,) with the (x,y,w,h) coordinates of the found rectangle.
                        Or `[]` if not found.
        """
        return self.matching_strategy.find(
            haystack_img, self.needle_img, threshold=threshold, cv_method=cv2.TM_CCOEFF_NORMED
        )

    def find_all_rectangles(self, haystack_img, threshold=0.5) -> tuple[np.ndarray, np.ndarray]:
        """Find all the rectangles corresponding to the needle image."""
        return self.matching_strategy.find_all_rectangles(haystack_img, self.needle_img, threshold=threshold)

    def draw_rectangles(self, haystack_img, rectangles: np.ndarray) -> np.ndarray:
        """Given a list of [x, y, w, h] rectangles and a canvas image to draw on, return an image with
        all of those rectangles drawn"""

        # these colors are actually BGR
        line_color = (0, 255, 0)
        line_type = cv2.LINE_4

        # Expand to 2D if 1-dimensional
        rectangles = rectangles[None, ...] if rectangles.ndim == 1 else rectangles

        for x, y, w, h in rectangles:
            # determine the box positions
            top_left = (x, y)
            bottom_right = (x + w, y + h)
            # draw the box
            cv2.rectangle(haystack_img, top_left, bottom_right, line_color, lineType=line_type)

        return haystack_img
