"""Generic child-process runner for validated native AutoFarmers extensions."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
import zipfile
from pathlib import Path

from utilities.compiled_extensions import (
    CORE_EXTENSION_API_VERSION,
    ExtensionValidationError,
    _validate_relative_path,
    default_extension_cache_root,
    load_extension_manifest,
    validate_extension_version,
)


_SECRETS_ENVIRONMENT_VARIABLE = "AUTOFARMERS_EXTENSION_SECRETS"
_MAX_SECRETS_PAYLOAD_LENGTH = 8192


def _consume_extension_secrets(manifest: dict) -> list[str]:
    raw_payload = os.environ.pop(_SECRETS_ENVIRONMENT_VARIABLE, "")
    if not raw_payload:
        return []
    if len(raw_payload) > _MAX_SECRETS_PAYLOAD_LENGTH:
        raise ExtensionValidationError("Extension secrets payload is too large")
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ExtensionValidationError("Extension secrets payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ExtensionValidationError("Extension secrets payload must be an object")

    secret_names = {arg["name"] for arg in manifest["args"] if arg["type"] == "secret"}
    if set(payload) - secret_names:
        raise ExtensionValidationError("Extension secrets payload contains an unknown field")

    secret_args = []
    for arg in manifest["args"]:
        if arg["type"] != "secret" or arg["name"] not in payload:
            continue
        value = payload[arg["name"]]
        if not isinstance(value, str):
            raise ExtensionValidationError("Extension secret values must be strings")
        if value:
            secret_args.extend((arg["name"], value))
    return secret_args


def _reject_secret_command_line_args(manifest: dict, extension_args: list[str]):
    secret_names = {arg["name"] for arg in manifest["args"] if arg["type"] == "secret"}
    if any(arg in secret_names for arg in extension_args):
        raise ExtensionValidationError(
            "Secret extension arguments must be transferred through the protected environment payload"
        )


def _safe_wheel_members(archive: zipfile.ZipFile):
    seen_members = set()
    member_kinds = {}
    required_directories = set()
    for member in archive.infolist():
        name = member.filename
        is_directory = member.is_dir()
        path_name = name[:-1] if is_directory and name.endswith("/") else name
        pure_path = _validate_relative_path(path_name, "Wheel member")
        normalized_parts = tuple(part.casefold() for part in pure_path.parts)
        if normalized_parts == (".autofarmers-extension.json",):
            raise ExtensionValidationError("Wheel uses the reserved extension cache marker name")
        if normalized_parts in seen_members:
            raise ExtensionValidationError(f"Wheel contains a duplicate path: {name!r}")
        if any(member_kinds.get(normalized_parts[:index]) == "file" for index in range(1, len(normalized_parts))):
            raise ExtensionValidationError(f"Wheel member is nested below a file: {name!r}")
        if not is_directory and normalized_parts in required_directories:
            raise ExtensionValidationError(f"Wheel file conflicts with a directory: {name!r}")
        for index in range(1, len(normalized_parts)):
            parent = normalized_parts[:index]
            required_directories.add(parent)
            if member_kinds.get(parent) == "file":
                raise ExtensionValidationError(f"Wheel member is nested below a file: {name!r}")

        seen_members.add(normalized_parts)
        member_kinds[normalized_parts] = "directory" if is_directory else "file"
        unix_mode = member.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            raise ExtensionValidationError(f"Wheel contains a symbolic link: {name!r}")
        yield member, pure_path


def _ensure_contained(root: Path, candidate: Path, context: str) -> Path:
    """Resolve a path and ensure it stays below its designated filesystem root."""
    try:
        resolved_root = root.resolve()
        resolved_candidate = candidate.resolve(strict=False)
        resolved_candidate.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ExtensionValidationError(f"{context} escapes its managed directory") from exc
    return resolved_candidate


def _is_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction()) if is_junction is not None else False


def _remove_path_safely(root: Path, path: Path) -> None:
    resolved_root = root.resolve()
    resolved_path = _ensure_contained(root, path, "Extension cache path")
    if resolved_path == resolved_root:
        raise ExtensionValidationError("Refusing to remove the extension cache root")
    if path.is_symlink():
        path.unlink()
    elif _is_junction(path):
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _extract_wheel_safely(wheel_path: Path, destination: Path):
    parent_root = destination.parent.resolve()
    _ensure_contained(parent_root, destination, "Extension extraction path")
    destination.mkdir(parents=True, exist_ok=False)
    destination_root = destination.resolve()
    with zipfile.ZipFile(wheel_path) as archive:
        safe_members = list(_safe_wheel_members(archive))
        for member, pure_path in safe_members:
            target = destination.joinpath(*pure_path.parts)
            _ensure_contained(destination_root, target, "Wheel extraction target")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            _ensure_contained(destination_root, target.parent, "Wheel extraction parent")
            _ensure_contained(destination_root, target, "Wheel extraction target")
            with archive.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def _cache_marker_matches(cache_dir: Path, expected_hash: str) -> bool:
    marker_path = cache_dir / ".autofarmers-extension.json"
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return marker == {"wheel_sha256": expected_hash}


def _prepare_cache(manifest: dict) -> Path:
    artifact = manifest["artifact"]
    expected_hash = artifact["sha256"]
    if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(
        character not in "0123456789abcdef" for character in expected_hash
    ):
        raise ExtensionValidationError("Compiled extension cache needs a valid wheel hash")
    extension_id = manifest["id"]
    if not isinstance(extension_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", extension_id):
        raise ExtensionValidationError("Compiled extension cache needs a safe extension id")
    version = validate_extension_version(manifest["version"])
    cache_root = default_extension_cache_root()
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_root = cache_root.resolve()
    extension_root = cache_root / extension_id
    _ensure_contained(cache_root, extension_root, "Extension cache root")
    extension_root.mkdir(parents=True, exist_ok=True)
    _ensure_contained(cache_root, extension_root, "Extension cache root")
    cache_dir = extension_root / f"{version}-{expected_hash[:12]}"
    _ensure_contained(extension_root, cache_dir, "Extension cache path")

    if cache_dir.is_dir() and _cache_marker_matches(cache_dir, expected_hash):
        _remove_stale_caches(extension_root, cache_dir)
        return cache_dir
    if cache_dir.exists():
        _remove_path_safely(extension_root, cache_dir)
        if cache_dir.exists() or cache_dir.is_symlink() or _is_junction(cache_dir):
            raise ExtensionValidationError(f"Cannot replace invalid extension cache: {cache_dir}")

    temp_dir = extension_root / f".{cache_dir.name}.{uuid.uuid4().hex}.tmp"
    try:
        _extract_wheel_safely(Path(manifest["wheel_path"]), temp_dir)
        marker_path = temp_dir / ".autofarmers-extension.json"
        _ensure_contained(extension_root, marker_path, "Extension cache marker")
        marker_path.write_text(json.dumps({"wheel_sha256": expected_hash}), encoding="utf-8")
        try:
            _ensure_contained(extension_root, cache_dir, "Extension cache path")
            os.replace(temp_dir, cache_dir)
        except FileExistsError:
            _ensure_contained(extension_root, cache_dir, "Extension cache path")
            if not _cache_marker_matches(cache_dir, expected_hash):
                raise
    finally:
        if temp_dir.exists() or temp_dir.is_symlink() or _is_junction(temp_dir):
            _remove_path_safely(extension_root, temp_dir)

    if not _cache_marker_matches(cache_dir, expected_hash):
        raise ExtensionValidationError("Compiled extension cache did not pass verification")
    _remove_stale_caches(extension_root, cache_dir)
    return cache_dir


def _remove_stale_caches(extension_root: Path, current_cache: Path):
    for candidate in extension_root.iterdir():
        if candidate == current_cache or not (
            candidate.is_dir() or candidate.is_symlink() or _is_junction(candidate)
        ):
            continue
        try:
            _remove_path_safely(extension_root, candidate)
        except (ExtensionValidationError, OSError):
            pass


def _load_module(manifest: dict, cache_dir: Path):
    sys.path.insert(0, str(cache_dir))
    importlib.invalidate_caches()
    module = importlib.import_module(manifest["artifact"]["module"])
    if getattr(module, "__version__", None) != manifest["version"]:
        raise ExtensionValidationError(
            f"Compiled module version {getattr(module, '__version__', None)!r} "
            f"does not match manifest version {manifest['version']!r}"
        )
    if getattr(module, "CORE_API_VERSION", None) != CORE_EXTENSION_API_VERSION:
        raise ExtensionValidationError(
            f"Compiled module API {getattr(module, 'CORE_API_VERSION', None)!r} "
            f"does not match core API {CORE_EXTENSION_API_VERSION}"
        )
    test_callable = getattr(module, "self_test", None)
    if not callable(test_callable):
        raise ExtensionValidationError("Compiled module does not expose self_test()")
    contract = test_callable()
    if not isinstance(contract, dict):
        raise ExtensionValidationError("Compiled module self_test() did not return an object")
    if contract.get("source_commit") != manifest["source"]["commit"]:
        raise ExtensionValidationError(
            f"Compiled source commit {contract.get('source_commit')!r} "
            f"does not match manifest source commit {manifest['source']['commit']!r}"
        )
    return module, contract


def run_bundle(bundle_dir: Path, extension_args: list[str], *, self_test: bool = False) -> int:
    manifest = load_extension_manifest(bundle_dir, verify_hash=True)
    if manifest["availability_error"]:
        raise ExtensionValidationError(manifest["availability_error"])
    _reject_secret_command_line_args(manifest, extension_args)
    secret_args = _consume_extension_secrets(manifest)

    cache_dir = _prepare_cache(manifest)
    repo_root = Path(__file__).resolve().parents[1]
    os.environ["AUTOFARMERS_ROOT"] = str(repo_root)
    os.environ["AUTOFARMERS_EXTENSION_DIR"] = str(Path(manifest["bundle_dir"]))
    module, contract = _load_module(manifest, cache_dir)

    if self_test:
        print(json.dumps(contract, sort_keys=True))
        return 0

    callable_name = manifest["artifact"]["callable"]
    entrypoint = getattr(module, callable_name, None)
    if not callable(entrypoint):
        raise ExtensionValidationError(f"Compiled module does not expose callable {callable_name!r}")
    result = entrypoint(extension_args + secret_args)
    return 0 if result is None else int(result)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run a compiled AutoFarmers extension")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("extension_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.extension_args[:1] == ["--"]:
        args.extension_args = args.extension_args[1:]
    return args


def main(argv=None) -> int:
    args = _parse_args(argv)
    try:
        return run_bundle(args.bundle, args.extension_args, self_test=args.self_test)
    except (ExtensionValidationError, ImportError, OSError, zipfile.BadZipFile):
        print("This Farmer couldn't start. Update AutoFarmers and try again.", file=sys.stderr)
        return 2
    except Exception:
        print("This Farmer stopped unexpectedly. Please try again.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
