"""Resolve game image assets for the active Global or Japanese client."""

import os
import warnings
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath

from utilities.app_config import APP_CONFIG_DEFAULTS, config


class GameVersion(str, Enum):
    """Supported 7DS Grand Cross client versions."""

    GLOBAL = "global"
    JAPAN = "japan"

    @property
    def display_name(self) -> str:
        if self is GameVersion.JAPAN:
            return "Japan (Japanese)"
        return "Global (English)"


def normalize_game_version(value, *, source: str = "game version") -> GameVersion:
    """Return a supported game version, defaulting invalid or missing values to Global."""
    if isinstance(value, GameVersion):
        return value

    normalized = "" if value is None else str(value).strip().lower()
    if not normalized:
        return GameVersion.GLOBAL

    try:
        return GameVersion(normalized)
    except ValueError:
        warnings.warn(
            f"Unsupported {source} '{value}'; using {GameVersion.GLOBAL.display_name}.",
            RuntimeWarning,
            stacklevel=2,
        )
        return GameVersion.GLOBAL


def get_saved_game_version() -> GameVersion:
    """Read and normalize the persisted GUI preference."""
    return normalize_game_version(
        config.get("game_version", APP_CONFIG_DEFAULTS["game_version"]),
        source="saved game version",
    )


def _default_images_root() -> Path:
    return Path(__file__).resolve().parents[1] / "images"


@dataclass(frozen=True)
class ImageAssetResolver:
    """Map logical image names to one immutable game-version asset pack."""

    game_version: GameVersion
    images_root: Path = field(default_factory=_default_images_root)

    def __post_init__(self) -> None:
        object.__setattr__(self, "game_version", normalize_game_version(self.game_version))
        object.__setattr__(self, "images_root", Path(self.images_root).resolve())

    @staticmethod
    def _normalize_relative_path(relative_path: str | os.PathLike[str]) -> PurePosixPath:
        raw_path = os.fspath(relative_path).strip()
        if not raw_path:
            raise ValueError("Image asset path cannot be empty")

        normalized = raw_path.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        if not posix_path.parts:
            raise ValueError("Image asset path cannot be empty")
        if posix_path.is_absolute() or PureWindowsPath(normalized).is_absolute():
            raise ValueError(f"Image asset path must be relative: '{relative_path}'")
        if ".." in posix_path.parts:
            raise ValueError(f"Image asset path cannot leave the images directory: '{relative_path}'")

        return posix_path

    def resolve(self, relative_path: str | os.PathLike[str]) -> Path:
        """Resolve one image, preferring Japan and falling back to Global per filename."""
        normalized = self._normalize_relative_path(relative_path)
        global_path = self.images_root.joinpath(*normalized.parts)

        if self.game_version is GameVersion.JAPAN:
            japan_path = self.images_root.joinpath("japan", *normalized.parts)
            if japan_path.is_file():
                return japan_path

        return global_path


@lru_cache(maxsize=1)
def get_default_image_asset_resolver() -> ImageAssetResolver:
    """Return the process-scoped resolver used by default by every Vision instance."""
    return ImageAssetResolver(get_saved_game_version())
