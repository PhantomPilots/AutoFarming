"""Generic child-process runner for validated native AutoFarmers extensions."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.machinery
import importlib.util
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
from utilities.credential_handoff import consume_game_password


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


def _remove_game_password_argument(extension_args: list[str]) -> tuple[list[str], str | None]:
    cleaned_args = []
    cli_password = None
    saw_password = False
    index = 0
    while index < len(extension_args):
        argument = extension_args[index]
        if argument in ("--password", "-p"):
            if saw_password or index + 1 >= len(extension_args):
                raise ExtensionValidationError("Compiled extension --password needs exactly one value")
            saw_password = True
            cli_password = extension_args[index + 1]
            index += 2
            continue
        if argument.startswith("--password="):
            if saw_password:
                raise ExtensionValidationError("Compiled extension --password may only be supplied once")
            saw_password = True
            cli_password = argument.partition("=")[2]
            index += 1
            continue
        cleaned_args.append(argument)
        index += 1
    return cleaned_args, cli_password


def _consume_extension_game_password(manifest: dict, extension_args: list[str]) -> tuple[list[str], str | None]:
    if manifest["accepts_game_password"]:
        cleaned_args, cli_password = _remove_game_password_argument(extension_args)
        return cleaned_args, consume_game_password(cli_password)
    consume_game_password()
    return extension_args, None


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
        file_type = stat.S_IFMT(unix_mode)
        if stat.S_ISLNK(unix_mode):
            raise ExtensionValidationError(f"Wheel contains a symbolic link: {name!r}")
        if file_type not in (0, stat.S_IFDIR if is_directory else stat.S_IFREG):
            raise ExtensionValidationError(f"Wheel contains an unsupported file type: {name!r}")
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


def _copy_verified_wheel_snapshot(wheel_path: Path, snapshot_path: Path, expected_hash: str):
    _ensure_contained(snapshot_path.parent, snapshot_path, "Verified wheel snapshot")
    digest = hashlib.sha256()
    try:
        with wheel_path.open("rb") as source, snapshot_path.open("xb") as destination:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError as exc:
        raise ExtensionValidationError("Cannot create a verified extension wheel snapshot") from exc
    if digest.hexdigest() != expected_hash:
        raise ExtensionValidationError("Compiled extension wheel changed after manifest verification")


def _wheel_inventory(wheel_path: Path):
    """Return exact extracted file digests and directories from one wheel snapshot."""
    files = {}
    directories = set()
    with zipfile.ZipFile(wheel_path) as archive:
        safe_members = list(_safe_wheel_members(archive))
        for member, pure_path in safe_members:
            parts = tuple(pure_path.parts)
            if member.is_dir():
                directories.add(parts)
            for index in range(1, len(parts)):
                directories.add(parts[:index])
            if member.is_dir():
                continue
            digest = hashlib.sha256()
            size = 0
            with archive.open(member) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            files[parts] = (size, digest.hexdigest())
    return files, directories


def _is_reparse_point(file_stat) -> bool:
    return bool(getattr(file_stat, "st_file_attributes", 0) & 0x400)


def _same_file_identity(first, second) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_size,
        getattr(first, "st_mtime_ns", None),
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_size,
        getattr(second, "st_mtime_ns", None),
    )


def _hash_cache_file(root: Path, path: Path):
    _ensure_contained(root, path, "Cached extension file")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or _is_reparse_point(before):
            raise ExtensionValidationError("Extension cache contains a non-regular file")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as file_obj:
            opened = os.fstat(file_obj.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or _is_reparse_point(opened)
                or not _same_file_identity(before, opened)
            ):
                raise ExtensionValidationError("Extension cache file changed while being checked")
            digest = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
            after = path.lstat()
            if (
                _is_reparse_point(after)
                or not _same_file_identity(opened, after)
            ):
                raise ExtensionValidationError("Extension cache file changed while being checked")
        _ensure_contained(root, path, "Cached extension file")
        return size, digest.hexdigest()
    except ExtensionValidationError:
        raise
    except OSError as exc:
        raise ExtensionValidationError("Cannot safely read an extension cache file") from exc


def _cache_contents_match(cache_dir: Path, expected_hash: str, expected_files: dict, expected_directories: set) -> bool:
    marker_name = ".autofarmers-extension.json"
    marker_path = cache_dir / marker_name
    try:
        _ensure_contained(cache_dir.parent, cache_dir, "Extension cache path")
        if cache_dir.is_symlink() or _is_junction(cache_dir) or not cache_dir.is_dir():
            return False

        actual_files = {}
        actual_directories = set()
        pending = [cache_dir]
        while pending:
            current_dir = pending.pop()
            _ensure_contained(cache_dir, current_dir, "Extension cache directory")
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    if entry.is_symlink() or _is_junction(path):
                        return False
                    _ensure_contained(cache_dir, path, "Extension cache entry")
                    relative = path.relative_to(cache_dir)
                    parts = tuple(relative.parts)
                    _validate_relative_path("/".join(parts), "Extension cache path")
                    if entry.is_dir(follow_symlinks=False):
                        actual_directories.add(parts)
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        actual_files[parts] = _hash_cache_file(cache_dir, path)
                    else:
                        return False

        expected_marker = json.dumps({"wheel_sha256": expected_hash}).encode("utf-8")
        marker_parts = (marker_name,)
        if actual_directories != expected_directories:
            return False
        if set(actual_files) != set(expected_files) | {marker_parts}:
            return False
        for parts, expected_digest in expected_files.items():
            if actual_files[parts] != expected_digest:
                return False
        return _hash_cache_file(cache_dir, marker_path) == (
            len(expected_marker),
            hashlib.sha256(expected_marker).hexdigest(),
        )
    except (OSError, ExtensionValidationError, ValueError, RuntimeError):
        return False


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
    wheel_path = Path(manifest["wheel_path"])
    token = uuid.uuid4().hex
    temp_dir = extension_root / f".{cache_dir.name}.{token}.tmp"
    snapshot_path = extension_root / f".{cache_dir.name}.{token}.wheel.tmp"
    try:
        _copy_verified_wheel_snapshot(wheel_path, snapshot_path, expected_hash)
        expected_files, expected_directories = _wheel_inventory(snapshot_path)

        if cache_dir.is_dir() and _cache_contents_match(
            cache_dir, expected_hash, expected_files, expected_directories
        ):
            _remove_stale_caches(extension_root, cache_dir)
            return cache_dir
        if cache_dir.exists() or cache_dir.is_symlink() or _is_junction(cache_dir):
            _remove_path_safely(extension_root, cache_dir)
            if cache_dir.exists() or cache_dir.is_symlink() or _is_junction(cache_dir):
                raise ExtensionValidationError(f"Cannot replace invalid extension cache: {cache_dir}")

        _extract_wheel_safely(snapshot_path, temp_dir)
        marker_path = temp_dir / ".autofarmers-extension.json"
        _ensure_contained(extension_root, marker_path, "Extension cache marker")
        marker_path.write_bytes(json.dumps({"wheel_sha256": expected_hash}).encode("utf-8"))
        if not _cache_contents_match(temp_dir, expected_hash, expected_files, expected_directories):
            raise ExtensionValidationError("Extracted extension cache does not match its wheel")
        try:
            _ensure_contained(extension_root, cache_dir, "Extension cache path")
            os.replace(temp_dir, cache_dir)
        except FileExistsError:
            _ensure_contained(extension_root, cache_dir, "Extension cache path")
            if not _cache_contents_match(cache_dir, expected_hash, expected_files, expected_directories):
                raise
    finally:
        if temp_dir.exists() or temp_dir.is_symlink() or _is_junction(temp_dir):
            _remove_path_safely(extension_root, temp_dir)
        if snapshot_path.exists() or snapshot_path.is_symlink() or _is_junction(snapshot_path):
            _remove_path_safely(extension_root, snapshot_path)

    if not _cache_contents_match(cache_dir, expected_hash, expected_files, expected_directories):
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


def _validate_module_spec(spec, cache_dir: Path, module_name: str):
    if spec is None:
        raise ImportError(f"Compiled module {module_name!r} is not present in the verified wheel")
    if spec.origin and spec.origin not in {"built-in", "frozen"}:
        origin = Path(spec.origin)
        if origin.is_symlink() or _is_junction(origin):
            raise ExtensionValidationError("Compiled module origin is a link")
        resolved_origin = _ensure_contained(cache_dir, origin, "Compiled module origin")
        if not resolved_origin.is_file():
            raise ExtensionValidationError("Compiled module origin is not a file in the extension cache")
    elif spec.submodule_search_locations:
        for location in spec.submodule_search_locations:
            _ensure_contained(cache_dir, Path(location), "Compiled package origin")
    else:
        raise ExtensionValidationError("Compiled module has no filesystem origin in the extension cache")


def _import_module_from_cache(module_name: str, cache_dir: Path):
    """Load each module component from this cache, without sys.path fallback."""
    module_parts = module_name.split(".")
    qualified_names = [".".join(module_parts[:index]) for index in range(1, len(module_parts) + 1)]
    for qualified_name in qualified_names:
        sys.modules.pop(qualified_name, None)

    cache_path = cache_dir.resolve()
    search_locations = [str(cache_path)]
    imported_module = None
    importlib.invalidate_caches()
    for index, qualified_name in enumerate(qualified_names):
        spec = importlib.machinery.PathFinder.find_spec(qualified_name, search_locations)
        _validate_module_spec(spec, cache_path, qualified_name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        if spec.loader is not None:
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(qualified_name, None)
                raise
        imported_module = module
        if index < len(qualified_names) - 1:
            locations = spec.submodule_search_locations
            if not locations:
                raise ImportError(f"Compiled module parent {qualified_name!r} is not a package")
            search_locations = list(locations)
    return imported_module


def _validate_imported_module_origin(module, cache_dir: Path) -> None:
    module_file = getattr(module, "__file__", None)
    module_spec = getattr(module, "__spec__", None)
    spec_origin = getattr(module_spec, "origin", None)
    if not module_file or not spec_origin or spec_origin in {"built-in", "frozen"}:
        raise ExtensionValidationError("Compiled module has no verified cache origin")
    module_path = Path(module_file)
    spec_path = Path(spec_origin)
    if module_path.is_symlink() or _is_junction(module_path) or spec_path.is_symlink() or _is_junction(spec_path):
        raise ExtensionValidationError("Compiled module origin is a link")
    resolved_module = _ensure_contained(cache_dir, module_path, "Compiled module file")
    resolved_spec = _ensure_contained(cache_dir, spec_path, "Compiled module specification")
    if resolved_module != resolved_spec or not resolved_module.is_file():
        raise ExtensionValidationError("Imported compiled module did not originate in its verified cache")


def _load_module(manifest: dict, cache_dir: Path):
    cache_dir = cache_dir.resolve()
    if cache_dir.is_symlink() or _is_junction(cache_dir):
        raise ExtensionValidationError("Compiled extension cache directory is a link")
    _ensure_contained(cache_dir.parent, cache_dir, "Extension cache path")
    sys.path.insert(0, str(cache_dir))
    module = _import_module_from_cache(manifest["artifact"]["module"], cache_dir)
    _validate_imported_module_origin(module, cache_dir)
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
    extension_args, game_password = _consume_extension_game_password(manifest, extension_args)
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
    password_args = ["--password", game_password] if game_password else []
    result = entrypoint(extension_args + password_args + secret_args)
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
