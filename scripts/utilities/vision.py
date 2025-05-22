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
        self._image_name = os.path.basename(needle_basename).split(".")[0]

        # Store the needle image
        self.needle_img = cv2.imread(needle_path)
        if self.needle_img is None:
            cprint(f"No image can be found for '{needle_basename}'", "yellow")
            return

    @property
    def image_name(self) -> str:
        return self._image_name

    def __eq__(self, other):
        if not isinstance(other, Vision):
            raise NotImplementedError(f"Cannot compare Vision instance with {type(other)}")
        return self.image_name == other.image_name

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


class MultiVision(Vision):
    """A class that will contain all OK buttons to be searched for in the screenshot"""

    def __init__(
        self,
        *needle_basenames: str,
        image_name: str | None = None,
        matching_strategy: IMatchingStrategy = TemplateMatchingStrategy,
    ):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        if image_name is None:
            raise ValueError("For a MultiVision instance, the 'image_name' argument must be provided")

        needle_paths = [os.path.join("images", needle_basename) for needle_basename in needle_basenames]

        # List with all OK image names
        self._image_names_list = [
            os.path.basename(needle_basename).split(".")[0] for needle_basename in needle_basenames
        ]

        # Save a single image name internally
        self._image_name = image_name

        # Save the pattern matching strategy as an attribute
        self.matching_strategy = matching_strategy

        # Store the needle image
        self.needle_imgs = [
            cv2.imread(needle_path) for needle_path in needle_paths if cv2.imread(needle_path) is not None
        ]
        if not len(self.needle_imgs):
            raise ValueError("No image can be found for to create an MultiVision instance", "yellow")

    def find(self, haystack_img, threshold=0.5, method=cv2.TM_CCOEFF_NORMED) -> np.ndarray:
        """Run the defined pattern matching strategy.

        Returns:
            np.ndarray: 1-D numpy array of shape (4,) with the (x,y,w,h) coordinates of the found rectangle.
                        Or `[]` if not found.
        """
        for needle_img in self.needle_imgs:
            found_best = self.matching_strategy.find(haystack_img, needle_img, threshold=threshold, cv_method=method)
            if found_best.size:
                return found_best
        return found_best

    def find_all_rectangles(
        self, haystack_img, threshold=0.5, method=cv2.TM_CCOEFF_NORMED
    ) -> tuple[np.ndarray, np.ndarray]:
        """Find all the rectangles corresponding to the needle image."""
        for needle_img in self.needle_imgs:
            all_rectangles, confidences = self.matching_strategy.find_all_rectangles(
                haystack_img, needle_img, threshold=threshold, method=method
            )
            if len(all_rectangles) > 0:
                return all_rectangles, confidences
        return all_rectangles, confidences
