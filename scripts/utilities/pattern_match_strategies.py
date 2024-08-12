"""Ideally, this script implements different pattern match strategies to decouple them from the `Vision` class.
The idea is that we can also implement scale-invariant pattern matching algorithms (such as SIFT or ORB).

For now, we only implemented a naive pattern matching algorithm not invariant to scaling.
"""

import abc

import cv2
import numpy as np


class IMatchingStrategy(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def find_all_rectangles(
        haystack_img: np.ndarray, needle_img: np.ndarray, **kwargs
    ) -> tuple[np.ndarray, np.ndarray]:
        """Must be implemented by subclasses"""

    @staticmethod
    @abc.abstractmethod
    def find(haystack_img: np.ndarray, needle_img: np.ndarray, **kwargs) -> np.ndarray:
        """Must be implemented by subclasses.
        Ideally, it uses `find_all_rectangles`, and then picks the best match.
        """


class TemplateMatchingStrategy:
    """Naive pattern matching algorithm"""

    @staticmethod
    def find_all_rectangles(haystack_img: np.ndarray, needle_img: np.ndarray, **kwargs):

        # Extract the keyword arguments required
        threshold = kwargs.get("threshold", 0.5)
        cv_method = kwargs.get("cv_method", cv2.TM_CCOEFF_NORMED)

        # run the OpenCV algorithm
        result = cv2.matchTemplate(haystack_img, needle_img, cv_method)

        # Get the all the positions from the match result that exceed our threshold
        locations = np.where(result >= threshold)
        locations = list(zip(*locations[::-1]))

        # if we found no results, return now. this reshape of the empty array allows us to
        # concatenate together results without causing an error
        if not locations:
            return np.empty(0), np.empty(0)

        # You'll notice a lot of overlapping rectangles get drawn. We can eliminate those redundant
        # locations by using groupRectangles().
        # First we need to create the list of [x, y, w, h] rectangles
        rectangles = []
        for loc in locations:
            rect = [int(loc[0]), int(loc[1]), needle_img.shape[1], needle_img.shape[0]]
            rectangles.extend((rect, rect))

        # Apply group rectangles
        rectangles, weights = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)

        return rectangles, weights

    @staticmethod
    def find(haystack_img: np.ndarray, needle_img: np.ndarray, **kwargs):
        """Find the best rectangle match of the needle in the haystack"""

        rectangles, weights = TemplateMatchingStrategy.find_all_rectangles(haystack_img, needle_img, **kwargs)

        # Check if there are any rectangles after grouping
        if len(rectangles) == 0:
            return np.array([], dtype=np.int32).reshape(0, 4)

        # Find the index of the rectangle with the highest weight
        best_index = np.argmax(weights)

        # Return the single rectangle with the highest confidence
        return rectangles[best_index]
