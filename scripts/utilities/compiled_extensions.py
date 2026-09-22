"""Discovery and validation for separately licensed compiled extensions."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
from pathlib import Path, PurePosixPath


CORE_EXTENSION_API_VERSION = 1
SUPPORTED_SCHEMA_VERSION = 2
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_HEX_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ARG_TYPES = frozenset({"text", "secret", "checkbox", "dropdown", "multiselect"})


class ExtensionValidationError(ValueError):
    """Raised when an extension bundle does not satisfy the public contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required(mapping: dict, key: str, expected_type, context: str):
    value = mapping.get(key)
    if not isinstance(value, expected_type):
        type_name = getattr(expected_type, "__name__", str(expected_type))
        raise ExtensionValidationError(f"{context}.{key} must be {type_name}")
    return value


def _required_string(mapping: dict, key: str, context: str) -> str:
    value = _required(mapping, key, str, context).strip()
    if not value:
        raise ExtensionValidationError(f"{context}.{key} cannot be empty")
    return value


def _validate_relative_path(relative_path: str, context: str = "Bundle path") -> PurePosixPath:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ExtensionValidationError(f"{context} must be a non-empty string")
    if "\\" in relative_path:
        raise ExtensionValidationError(f"{context} must use forward slashes: {relative_path!r}")

    pure_path = PurePosixPath(relative_path)
    if (
        not pure_path.parts
        or pure_path.is_absolute()
        or ".." in pure_path.parts
        or ":" in pure_path.parts[0]
    ):
        raise ExtensionValidationError(f"Unsafe {context.lower()}: {relative_path!r}")
    return pure_path


def resolve_bundle_path(bundle_dir: Path, relative_path: str, *, must_exist: bool = True) -> Path:
    """Resolve a manifest path while preventing absolute paths and traversal."""
    pure_path = _validate_relative_path(relative_path)

    bundle_root = bundle_dir.resolve()
    resolved = bundle_root.joinpath(*pure_path.parts).resolve()
    try:
        resolved.relative_to(bundle_root)
    except ValueError as exc:
        raise ExtensionValidationError(f"Bundle path escapes its directory: {relative_path!r}") from exc
    if must_exist and not resolved.is_file():
        raise ExtensionValidationError(f"Referenced bundle file does not exist: {relative_path}")
    return resolved


def _validate_arg(arg: object, index: int) -> dict:
    context = f"args[{index}]"
    if not isinstance(arg, dict):
        raise ExtensionValidationError(f"{context} must be an object")

    normalized = dict(arg)
    name = _required_string(arg, "name", context)
    if not name.startswith("--") or len(name) < 3:
        raise ExtensionValidationError(f"{context}.name must be a long command-line option")
    _required_string(arg, "label", context)
    arg_type = _required_string(arg, "type", context)
    if arg_type not in _ARG_TYPES:
        raise ExtensionValidationError(f"{context}.type is unsupported: {arg_type}")

    if "false_name" in arg:
        false_name = _required_string(arg, "false_name", context)
        if arg_type != "checkbox" or not false_name.startswith("--"):
            raise ExtensionValidationError(f"{context}.false_name is only valid for checkboxes")

    if arg_type in ("dropdown", "multiselect"):
        choices = _required(arg, "choices", list, context)
        if not choices or any(not isinstance(choice, str) or not choice for choice in choices):
            raise ExtensionValidationError(f"{context}.choices must contain non-empty strings")
        if "labels" in arg:
            labels = _required(arg, "labels", list, context)
            if len(labels) != len(choices) or any(not isinstance(label, str) for label in labels):
                raise ExtensionValidationError(f"{context}.labels must match choices")

    default = arg.get("default")
    if arg_type == "checkbox" and not isinstance(default, bool):
        raise ExtensionValidationError(f"{context}.default must be boolean")
    if arg_type == "multiselect" and not isinstance(default, list):
        raise ExtensionValidationError(f"{context}.default must be a list")
    if arg_type in ("text", "secret", "dropdown") and not isinstance(default, str):
        raise ExtensionValidationError(f"{context}.default must be a string")
    return normalized


def _validate_license(manifest: dict, normalized_args: list[dict]) -> dict:
    license_declaration = _required(manifest, "license", dict, "manifest")
    scope = _required_string(license_declaration, "scope", "license")
    key_argument = _required_string(license_declaration, "key_argument", "license")
    matching_args = [arg for arg in normalized_args if arg["name"] == key_argument]
    if len(matching_args) != 1 or matching_args[0]["type"] != "secret":
        raise ExtensionValidationError(
            "license.key_argument must reference exactly one secret argument"
        )
    secret_args = [arg for arg in normalized_args if arg["type"] == "secret"]
    if len(secret_args) != 1:
        raise ExtensionValidationError(
            "Licensed extensions must declare exactly one secret argument"
        )
    return {"scope": scope, "key_argument": key_argument}


def _compatibility_error(manifest: dict) -> str | None:
    artifact = manifest["artifact"]
    if manifest["core_api_version"] != CORE_EXTENSION_API_VERSION:
        return (
            f"Requires AutoFarmers extension API {manifest['core_api_version']}; "
            f"this version provides API {CORE_EXTENSION_API_VERSION}."
        )
    if artifact["python_tag"] != "cp312":
        return f"Unsupported Python artifact {artifact['python_tag']}; CPython 3.12 is required."
    if artifact["platform_tag"] != "win_amd64":
        return f"Unsupported platform artifact {artifact['platform_tag']}; 64-bit Windows is required."
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        return "This compiled extension requires 64-bit CPython 3.12."
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        return "This compiled extension requires 64-bit Windows."
    return None


def load_extension_manifest(bundle_dir: Path | str, *, verify_hash: bool = True) -> dict:
    """Load and validate a single extension manifest and its referenced files."""
    bundle_dir = Path(bundle_dir).resolve()
    manifest_path = bundle_dir / "extension.json"
    if not manifest_path.is_file():
        raise ExtensionValidationError(f"Missing extension manifest: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtensionValidationError(f"Cannot read {manifest_path.name}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ExtensionValidationError("extension.json must contain an object")

    schema_version = _required(manifest, "schema_version", int, "manifest")
    if isinstance(schema_version, bool) or schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ExtensionValidationError(f"Unsupported extension schema version: {schema_version}")
    extension_id = _required_string(manifest, "id", "manifest")
    if not _ID_PATTERN.fullmatch(extension_id):
        raise ExtensionValidationError("manifest.id must use lowercase letters, digits, and underscores")
    _required_string(manifest, "display_name", "manifest")
    _required_string(manifest, "version", "manifest")
    core_api_version = _required(manifest, "core_api_version", int, "manifest")
    if isinstance(core_api_version, bool) or core_api_version < 1:
        raise ExtensionValidationError("manifest.core_api_version must be a positive integer")
    _required_string(manifest, "placement_after", "manifest")
    _required(manifest, "accepts_game_password", bool, "manifest")
    _required(manifest, "requirements_html", str, "manifest")

    image_path = resolve_bundle_path(bundle_dir, _required_string(manifest, "image", "manifest"))

    source = _required(manifest, "source", dict, "manifest")
    source_path = _required_string(source, "submodule_path", "source")
    _validate_relative_path(source_path, "source.submodule_path")
    source_commit = _required_string(source, "commit", "source").lower()
    if not _COMMIT_PATTERN.fullmatch(source_commit):
        raise ExtensionValidationError("source.commit must be a 40-character Git commit ID")

    artifact = _required(manifest, "artifact", dict, "manifest")
    _required_string(artifact, "python_tag", "artifact")
    _required_string(artifact, "platform_tag", "artifact")
    wheel_path = resolve_bundle_path(bundle_dir, _required_string(artifact, "wheel", "artifact"))
    expected_hash = _required_string(artifact, "sha256", "artifact").lower()
    if not _HEX_SHA256_PATTERN.fullmatch(expected_hash):
        raise ExtensionValidationError("artifact.sha256 must be a lowercase SHA-256 digest")
    module_name = _required_string(artifact, "module", "artifact")
    callable_name = _required_string(artifact, "callable", "artifact")
    if not all(part.isidentifier() for part in module_name.split(".")) or not callable_name.isidentifier():
        raise ExtensionValidationError("artifact module and callable must be valid Python identifiers")
    if verify_hash:
        actual_hash = sha256_file(wheel_path)
        if actual_hash != expected_hash:
            raise ExtensionValidationError(
                f"Wheel hash mismatch for {wheel_path.name}: expected {expected_hash}, got {actual_hash}"
            )

    args = _required(manifest, "args", list, "manifest")
    normalized_args = [_validate_arg(arg, index) for index, arg in enumerate(args)]
    arg_names = [arg["name"] for arg in normalized_args]
    if len(arg_names) != len(set(arg_names)):
        raise ExtensionValidationError("Extension argument names must be unique")
    normalized_license = _validate_license(manifest, normalized_args)

    normalized = dict(manifest)
    normalized["source"] = dict(source)
    normalized["source"]["commit"] = source_commit
    normalized["artifact"] = dict(artifact)
    normalized["artifact"]["sha256"] = expected_hash
    normalized["args"] = normalized_args
    normalized["license"] = normalized_license
    normalized["bundle_dir"] = str(bundle_dir)
    normalized["image_path"] = str(image_path)
    normalized["wheel_path"] = str(wheel_path)
    normalized["availability_error"] = _compatibility_error(normalized)
    return normalized


def discover_compiled_extensions(vendor_dir: Path | str) -> tuple[list[dict], list[str]]:
    """Discover valid direct-child bundles without allowing one bad bundle to break the GUI."""
    vendor_dir = Path(vendor_dir)
    if not vendor_dir.is_dir():
        return [], []

    extensions = []
    warnings = []
    seen_ids = set()
    seen_names = set()
    for bundle_dir in sorted((path for path in vendor_dir.iterdir() if path.is_dir()), key=lambda path: path.name):
        manifest_path = bundle_dir / "extension.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = load_extension_manifest(bundle_dir)
            extension_id = manifest["id"]
            display_name = manifest["display_name"]
            if extension_id in seen_ids:
                raise ExtensionValidationError(f"Duplicate extension id: {extension_id}")
            if display_name in seen_names:
                raise ExtensionValidationError(f"Duplicate extension display name: {display_name}")
            seen_ids.add(extension_id)
            seen_names.add(display_name)
            extensions.append(manifest)
        except ExtensionValidationError as exc:
            warnings.append(f"Skipping compiled extension at {bundle_dir}: {exc}")
    return extensions, warnings


def extension_farmer_definition(manifest: dict) -> dict:
    """Convert a validated manifest into the GUI's normalized farmer definition."""
    return {
        "name": manifest["display_name"],
        "args": manifest["args"],
        "compiled_extension": True,
        "extension_id": manifest["id"],
        "bundle_dir": manifest["bundle_dir"],
        "image_path": manifest["image_path"],
        "requirements_html": manifest["requirements_html"],
        "accepts_game_password": manifest["accepts_game_password"],
        "placement_after": manifest["placement_after"],
        "availability_error": manifest["availability_error"],
        "license": manifest["license"],
    }


def merge_compiled_extensions(farmers: list[dict], vendor_dir: Path | str) -> tuple[list[dict], list[str]]:
    """Return built-ins plus valid extensions, placed after their requested anchors."""
    manifests, warnings = discover_compiled_extensions(vendor_dir)
    merged = list(farmers)
    existing_names = {farmer["name"] for farmer in merged}
    for manifest in manifests:
        farmer = extension_farmer_definition(manifest)
        if farmer["name"] in existing_names:
            warnings.append(f"Skipping compiled extension with duplicate farmer name: {farmer['name']}")
            continue
        anchor = farmer.pop("placement_after")
        insert_at = next((index + 1 for index, item in enumerate(merged) if item["name"] == anchor), len(merged))
        merged.insert(insert_at, farmer)
        existing_names.add(farmer["name"])
    return merged, warnings


def default_extension_cache_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AutoFarmers" / "extensions"
    return Path.home() / ".autofarmers" / "extensions"
