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
    def find_all_rectangles(image: np.ndarray, template: np.ndarray, **kwargs) -> tuple[np.ndarray, np.ndarray]:
        """Must be implemented by subclasses"""

    @staticmethod
    @abc.abstractmethod
    def find(image: np.ndarray, template: np.ndarray, **kwargs) -> np.ndarray:
        """Must be implemented by subclasses.
        Ideally, it uses `find_all_rectangles`, and then picks the best match.
        """


class TemplateMatchingStrategy:
    """Naive pattern matching algorithm"""

    @staticmethod
    def find_all_rectangles(image: np.ndarray, template: np.ndarray, **kwargs):

        # Extract the optional parameters with default values
        match_threshold = kwargs.get("threshold", 0.5)
        method = kwargs.get("cv_method", cv2.TM_CCOEFF_NORMED)

        # Perform template matching
        match_result = cv2.matchTemplate(image, template, method)

        # Identify positions where matches exceed the threshold
        match_locations = np.where(match_result >= match_threshold)
        match_points = list(zip(*match_locations[::-1]))

        if not match_points:
            return np.empty(0), np.empty(0)

        # Create rectangles based on the match points
        detected_rectangles = []
        for point in match_points:
            rectangle = [int(point[0]), int(point[1]), template.shape[1], template.shape[0]]
            detected_rectangles.extend((rectangle, rectangle))

        # Use groupRectangles to refine results
        # TODO: Also keep those rectangles that have no overlapping as well?
        grouped_rectangles, confidence_weights = cv2.groupRectangles(detected_rectangles, groupThreshold=1, eps=0.5)

        return grouped_rectangles, confidence_weights

    @staticmethod
    def _best_match(image: np.ndarray, template: np.ndarray, **kwargs):
        """Internal helper: returns best (rectangle, confidence)."""
        rectangles, weights = TemplateMatchingStrategy.find_all_rectangles(image, template, **kwargs)

        if len(rectangles) == 0:
            return np.array([], dtype=np.int32).reshape(0, 4), None

        best_index = np.argmax(weights)
        return rectangles[best_index], weights[best_index]

    @staticmethod
    def find(image: np.ndarray, template: np.ndarray, **kwargs) -> np.ndarray:
        """Find the best rectangle match of the needle in the haystack"""
        best_rect, _ = TemplateMatchingStrategy._best_match(image, template, **kwargs)
        return best_rect

    @staticmethod
    def find_with_confidence(image: np.ndarray, template: np.ndarray, **kwargs) -> tuple[np.ndarray, np.ndarray]:
        """Like `find`, but returning confidence value as well"""
        return TemplateMatchingStrategy._best_match(image, template, **kwargs)
