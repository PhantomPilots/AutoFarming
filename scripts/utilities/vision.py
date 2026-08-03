import os

import cv2
import numpy as np
from termcolor import cprint
from utilities.image_assets import ImageAssetResolver, get_default_image_asset_resolver
from utilities.pattern_match_strategies import (
    IMatchingStrategy,
    TemplateMatchingStrategy,
)


def _read_image(path: str) -> np.ndarray | None:
    """Decode an image after opening its path through Python for Windows Unicode support."""
    try:
        with open(path, "rb") as image_file:
            encoded_image = np.frombuffer(image_file.read(), dtype=np.uint8)
        if not encoded_image.size:
            return None
        return cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
    except (OSError, cv2.error):
        return None


class Vision:
    """Class to host a single image template to match"""

    def __init__(
        self,
        needle_basename,
        image_name: str | None = None,
        matching_strategy: IMatchingStrategy = TemplateMatchingStrategy,
        asset_resolver: ImageAssetResolver | None = None,
    ):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        self._needle_basename = needle_basename
        self._asset_resolver = asset_resolver or get_default_image_asset_resolver()
        self._needle_path = str(self._asset_resolver.resolve(needle_basename))
        self.matching_strategy = matching_strategy

        if image_name is None:
            self._image_name = os.path.basename(needle_basename).split(".")[0]
        else:
            self._image_name = image_name

        self._needle_img: np.ndarray | None = None
        self._needle_loaded: bool = False

    @property
    def image_name(self) -> str:
        return self._image_name

    @property
    def needle_img(self) -> np.ndarray | None:
        """Lazily-loaded template image; missing file yields ``None`` (and a one-shot warning)."""
        if not self._needle_loaded:
            self._needle_img = _read_image(self._needle_path)
            if self._needle_img is None:
                cprint(
                    f"No image can be loaded for '{self._needle_basename}' "
                    f"({self._asset_resolver.game_version.value}: {self._needle_path})",
                    "yellow",
                )
            self._needle_loaded = True
        return self._needle_img

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

        if hasattr(self.matching_strategy, "find_with_confidence"):
            return self.matching_strategy.find_with_confidence(
                haystack_img, self.needle_img, threshold=threshold, cv_method=method
            )

        rect = self.matching_strategy.find(haystack_img, self.needle_img, threshold=threshold, cv_method=method)
        return rect, None


class MultiVision(Vision):
    """A class that will contain all OK buttons to be searched for in the screenshot"""

    def __init__(
        self,
        *needle_basenames: str,
        image_name: str | None = None,
        matching_strategy: IMatchingStrategy = TemplateMatchingStrategy,
        asset_resolver: ImageAssetResolver | None = None,
    ):
        """Receives the needle image to search on a haystack, and the matching algorithm to use"""

        if image_name is None:
            raise ValueError("For a MultiVision instance, the 'image_name' argument must be provided")

        self._asset_resolver = asset_resolver or get_default_image_asset_resolver()
        self._needle_basenames = list(needle_basenames)
        self._needle_paths = [str(self._asset_resolver.resolve(path)) for path in self._needle_basenames]
        self._image_names_list = [
            os.path.basename(needle_basename).split(".")[0] for needle_basename in self._needle_basenames
        ]
        self._image_name = image_name
        self.matching_strategy = matching_strategy

        self._needle_imgs: list[np.ndarray] | None = None

    @property
    def needle_imgs(self) -> list[np.ndarray]:
        """Lazily-loaded template images; raises ``ValueError`` on first access if all paths missing."""
        if self._needle_imgs is None:
            loaded = []
            for basename, path in zip(self._needle_basenames, self._needle_paths):
                image = _read_image(path)
                if image is None:
                    cprint(
                        f"No image can be loaded for '{basename}' "
                        f"({self._asset_resolver.game_version.value}: {path})",
                        "yellow",
                    )
                else:
                    loaded.append(image)
            if not loaded:
                raise ValueError(
                    f"No image can be loaded to create the MultiVision instance '{self._image_name}' "
                    f"for game version '{self._asset_resolver.game_version.value}'. "
                    f"Resolved paths: {self._needle_paths}"
                )
            self._needle_imgs = loaded
        return self._needle_imgs

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
