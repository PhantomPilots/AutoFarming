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

    def __init__(
        self,
        needle_basename,
        image_name: str | None = None,
        matching_strategy: IMatchingStrategy = TemplateMatchingStrategy,
    ):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        needle_path = os.path.join("images", needle_basename)

        # Save the pattern matching strategy as an attribute
        self.matching_strategy = matching_strategy

        # Save the name of the needle image
        if image_name is None:
            self._image_name = os.path.basename(needle_basename).split(".")[0]
        else:
            self._image_name = image_name

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

    def find_with_confidence(
        self, haystack_img, threshold=0.5, method=cv2.TM_CCOEFF_NORMED
    ) -> tuple[np.ndarray, float] | tuple[np.ndarray, None]:
        """Find the best match and return both the rectangle and its confidence value.

        Returns:
            (np.ndarray, float): tuple of (rectangle, confidence)
                                 or (empty array, None) if not found.
        """
        if self.needle_img is None:
            return np.array([], dtype=np.int32).reshape(0, 4), None

        # If the matching strategy supports this directly, use it
        if hasattr(self.matching_strategy, "find_with_confidence"):
            return self.matching_strategy.find_with_confidence(
                haystack_img, self.needle_img, threshold=threshold, cv_method=method
            )

        # Otherwise, gracefully fall back to standard `find`
        rect = self.matching_strategy.find(haystack_img, self.needle_img, threshold=threshold, cv_method=method)
        return rect, None


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

    def find_with_confidence(
        self,
        haystack_img,
        threshold=0.5,
        method=cv2.TM_CCOEFF_NORMED,
    ) -> tuple[np.ndarray, float | None]:
        """Like `find`, but returns (rectangle, confidence) for the best match found."""
        best_rect = np.array([], dtype=np.int32).reshape(0, 4)
        best_conf = -np.inf

        for needle_img in self.needle_imgs:
            if hasattr(self.matching_strategy, "find_with_confidence"):
                rect, conf = self.matching_strategy.find_with_confidence(
                    haystack_img, needle_img, threshold=threshold, cv_method=method
                )
            else:
                rect = self.matching_strategy.find(haystack_img, needle_img, threshold=threshold, cv_method=method)
                conf = None

            if rect.size and (conf is None or conf > best_conf):
                best_rect, best_conf = rect, conf if conf is not None else best_conf

        if best_conf == -np.inf:
            return np.array([], dtype=np.int32).reshape(0, 4), None
        return best_rect, best_conf
