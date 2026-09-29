"""Repository-anchored access for serialized models and training datasets."""

from __future__ import annotations

import glob
import hashlib
import hmac
from enum import Enum
from pathlib import Path

import numpy as np

from utilities.artifact_hashes import TRUSTED_LEGACY_DATA_SHA256, TRUSTED_MODEL_SHA256


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
MODEL_ROOT = SCRIPTS_ROOT / "models"
DATA_ROOT = SCRIPTS_ROOT / "data"


class UnsafeArtifactError(ValueError):
    """Raised when an artifact is outside the repository or is not trusted."""


def labels_to_numpy_values(labels) -> np.ndarray:
    """Convert Enum labels to their values while preserving numeric labels."""
    if isinstance(labels, Enum):
        labels = [labels]

    object_array = np.asarray(labels, dtype=object)
    values = [value.value if isinstance(value, Enum) else value for value in object_array.flat]
    numeric_array = np.asarray(values).reshape(object_array.shape)
    if numeric_array.dtype.hasobject:
        raise ValueError("Labels must contain values NumPy can store without pickle")
    return numeric_array


def _canonical_asset_root(root: Path) -> Path:
    repository_root = REPOSITORY_ROOT.resolve()
    scripts_root = SCRIPTS_ROOT.resolve(strict=False)
    if scripts_root.parent != repository_root:
        raise UnsafeArtifactError("The scripts directory resolves outside the repository")

    resolved_root = root.resolve(strict=False)
    if root.parent.resolve(strict=False) != scripts_root or resolved_root.parent != scripts_root:
        raise UnsafeArtifactError(f"The {root.name} directory must be a direct repository scripts subdirectory")
    return resolved_root


def _resolve_under(path: str | Path, root: Path, *, relative_to_scripts: bool = False) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        candidate = raw_path
    elif relative_to_scripts:
        candidate = SCRIPTS_ROOT / raw_path
    else:
        candidate = root / raw_path

    if candidate.is_symlink():
        raise UnsafeArtifactError(f"Refusing symlinked artifact path: {path}")
    resolved = candidate.resolve(strict=False)
    resolved_root = _canonical_asset_root(root)
    if not resolved.is_relative_to(resolved_root):
        raise UnsafeArtifactError(f"Artifact path is outside the repository {root.name} directory: {path}")
    return resolved


def model_path_for(filename: str | Path) -> Path:
    """Resolve a model filename under the bundled models directory."""
    path = _resolve_under(filename, MODEL_ROOT)
    if path.parent != MODEL_ROOT.resolve():
        raise UnsafeArtifactError(f"Model must be a file directly inside {MODEL_ROOT}: {filename}")
    return path


def dataset_path_for(filepath: str | Path) -> Path:
    """Resolve a dataset path under the repository's data directory."""
    path = _resolve_under(filepath, DATA_ROOT, relative_to_scripts=True)
    if path.parent != _canonical_asset_root(DATA_ROOT):
        raise UnsafeArtifactError(f"Dataset must be a file directly inside {DATA_ROOT}: {filepath}")
    return path


def dataset_paths(pattern: str | Path) -> list[Path]:
    """Expand a dataset glob under scripts/data and reject escaping matches."""
    pattern_path = _resolve_under(pattern, DATA_ROOT, relative_to_scripts=True)
    matches = []
    data_root = _canonical_asset_root(DATA_ROOT)
    for match in glob.glob(str(pattern_path)):
        match_path = Path(match)
        if match_path.is_symlink():
            raise UnsafeArtifactError(f"Refusing symlinked dataset: {match_path}")
        path = match_path.resolve(strict=False)
        if not path.is_relative_to(data_root):
            raise UnsafeArtifactError(f"Dataset path is outside the repository data directory: {match}")
        if path.parent != data_root:
            raise UnsafeArtifactError(f"Dataset must be a file directly inside {DATA_ROOT}: {match}")
        if path.is_file() and path.suffix.lower() in {".npy", ".npz"}:
            matches.append(path)
    return sorted(set(matches))


def _verified_pickle_bytes(path: Path, trusted_hashes: dict[str, str], kind: str) -> bytes:
    if path.is_symlink():
        raise UnsafeArtifactError(f"Refusing symlinked {kind}: {path}")
    expected_hash = trusted_hashes.get(path.name)
    if expected_hash is None:
        raise UnsafeArtifactError(f"Untrusted {kind}; its SHA-256 is not pinned in source: {path.name}")

    raw_bytes = path.read_bytes()
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    if not hmac.compare_digest(actual_hash, expected_hash):
        raise UnsafeArtifactError(f"The bundled {kind} failed its SHA-256 check: {path.name}")
    return raw_bytes


def load_trusted_model(filename: str | Path):
    """Verify the exact bundled model bytes before dill deserialization."""
    path = model_path_for(filename)
    raw_bytes = _verified_pickle_bytes(path, TRUSTED_MODEL_SHA256, "model")

    # Import dill only after the source-pinned digest has been verified.
    import dill

    return dill.loads(raw_bytes)


def load_dataset_file(filepath: str | Path) -> tuple[np.ndarray | list, np.ndarray]:
    """Load a dataset, using pinned verification for legacy pickle files."""
    path = dataset_path_for(filepath)
    if path.suffix.lower() == ".npy":
        raw_bytes = _verified_pickle_bytes(path, TRUSTED_LEGACY_DATA_SHA256, "legacy dataset")
        import dill

        payload = dill.loads(raw_bytes)
        if not isinstance(payload, dict) or set(payload) != {"data", "labels"}:
            raise UnsafeArtifactError(f"Legacy dataset has an invalid structure: {path.name}")
        # Keep legacy data as stored: some trusted batches are ragged lists that
        # cannot be represented by one NumPy array without changing their shape.
        return payload["data"], np.asarray(payload["labels"])

    if path.suffix.lower() != ".npz":
        raise UnsafeArtifactError(f"Unsupported dataset format: {path.suffix}")
    if path.is_symlink():
        raise UnsafeArtifactError(f"Refusing symlinked dataset: {path}")

    try:
        with np.load(path, allow_pickle=False) as payload:
            if set(payload.files) != {"data", "labels"}:
                raise UnsafeArtifactError(f"Dataset must contain exactly 'data' and 'labels': {path.name}")
            data = np.asarray(payload["data"])
            labels = np.asarray(payload["labels"])
    except ValueError as exc:
        raise UnsafeArtifactError(f"Dataset contains data that NumPy cannot safely load: {path.name}") from exc

    if data.dtype.hasobject or labels.dtype.hasobject:
        raise UnsafeArtifactError(f"Object arrays are not allowed in datasets: {path.name}")
    return data, labels


def save_dataset_file(filepath: str | Path, data: np.ndarray, labels: np.ndarray) -> Path:
    """Write a numeric dataset in the safe NPZ format."""
    path = dataset_path_for(filepath)
    if path.suffix.lower() != ".npz":
        raise ValueError("New datasets must use the .npz extension")
    if path.exists():
        raise FileExistsError(path)

    data_array = np.asarray(data)
    labels_array = labels_to_numpy_values(labels)
    if data_array.dtype.hasobject or labels_array.dtype.hasobject:
        raise ValueError("Datasets may not contain object arrays")
    np.savez_compressed(path, data=data_array, labels=labels_array)
    return path

