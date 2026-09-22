"""Generic child-process runner for validated native AutoFarmers extensions."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import stat
import sys
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from utilities.compiled_extensions import (
    CORE_EXTENSION_API_VERSION,
    ExtensionValidationError,
    default_extension_cache_root,
    load_extension_manifest,
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
    for member in archive.infolist():
        name = member.filename
        if "\\" in name:
            raise ExtensionValidationError(f"Wheel member uses unsafe separators: {name!r}")
        pure_path = PurePosixPath(name)
        if pure_path.is_absolute() or any(part in ("", ".", "..") for part in pure_path.parts):
            raise ExtensionValidationError(f"Unsafe wheel member: {name!r}")
        unix_mode = member.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            raise ExtensionValidationError(f"Wheel contains a symbolic link: {name!r}")
        yield member, pure_path


def _extract_wheel_safely(wheel_path: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(wheel_path) as archive:
        for member, pure_path in _safe_wheel_members(archive):
            target = destination.joinpath(*pure_path.parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
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
    extension_root = default_extension_cache_root() / manifest["id"]
    extension_root.mkdir(parents=True, exist_ok=True)
    cache_dir = extension_root / f"{manifest['version']}-{expected_hash[:12]}"

    if cache_dir.is_dir() and _cache_marker_matches(cache_dir, expected_hash):
        _remove_stale_caches(extension_root, cache_dir)
        return cache_dir
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
        if cache_dir.exists():
            raise ExtensionValidationError(f"Cannot replace invalid extension cache: {cache_dir}")

    temp_dir = extension_root / f".{cache_dir.name}.{uuid.uuid4().hex}.tmp"
    try:
        _extract_wheel_safely(Path(manifest["wheel_path"]), temp_dir)
        marker_path = temp_dir / ".autofarmers-extension.json"
        marker_path.write_text(json.dumps({"wheel_sha256": expected_hash}), encoding="utf-8")
        try:
            os.replace(temp_dir, cache_dir)
        except FileExistsError:
            if not _cache_marker_matches(cache_dir, expected_hash):
                raise
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    if not _cache_marker_matches(cache_dir, expected_hash):
        raise ExtensionValidationError("Compiled extension cache did not pass verification")
    _remove_stale_caches(extension_root, cache_dir)
    return cache_dir


def _remove_stale_caches(extension_root: Path, current_cache: Path):
    for candidate in extension_root.iterdir():
        if candidate == current_cache or not candidate.is_dir():
            continue
        try:
            shutil.rmtree(candidate)
        except OSError:
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
    except (ExtensionValidationError, ImportError, OSError, zipfile.BadZipFile) as exc:
        print(f"Compiled extension could not start: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Compiled extension failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
