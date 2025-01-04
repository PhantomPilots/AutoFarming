import os

import cv2
import numpy as np
from termcolor import cprint
from utilities.pattern_match_strategies import (
    IMatchingStrategy,
    TemplateMatchingStrategy,
)


class Vision:
    """Class to host a single image template to match"""

    def __init__(self, needle_basename, matching_strategy: IMatchingStrategy = TemplateMatchingStrategy):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        needle_path = os.path.join("images", needle_basename)

        # Save the pattern matching strategy as an attribute
        self.matching_strategy = matching_strategy

        # Save the name of the needle image
        self.image_name = os.path.basename(needle_basename).split(".")[0]

        # Store the needle image
        self.needle_img = cv2.imread(needle_path)
        if self.needle_img is None:
            cprint(f"No image can be found for '{needle_basename}'", "yellow")
            return

    def __eq__(self, other):
        if isinstance(other, Vision):
            return self.image_name == other.image_name
        return NotImplementedError(f"Cannot compare Vision instance with {type(other)}")

    def find(self, haystack_img, threshold=0.5, method=cv2.TM_CCOEFF_NORMED) -> np.ndarray:
        """Run the defined pattern matching strategy.

        Returns:
            np.ndarray: 1-D numpy array of shape (4,) with the (x,y,w,h) coordinates of the found rectangle.
                        Or `[]` if not found.
        """
        if self.needle_img is None:
            return None

        return self.matching_strategy.find(haystack_img, self.needle_img, threshold=threshold, cv_method=method)

    def find_all_rectangles(
        self, haystack_img, threshold=0.5, method=cv2.TM_CCOEFF_NORMED
    ) -> tuple[np.ndarray, np.ndarray]:
        """Find all the rectangles corresponding to the needle image."""
        if self.needle_img is None:
            return None

        return self.matching_strategy.find_all_rectangles(
            haystack_img, self.needle_img, threshold=threshold, method=method
        )
