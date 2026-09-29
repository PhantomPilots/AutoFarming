"""Behavioral security checks for compiled extension paths and wheel extraction."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
import types
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiled_extension_runner import (  # noqa: E402
    _extract_wheel_safely,
    _consume_extension_game_password,
    _load_module,
    _prepare_cache,
    _remove_path_safely,
    _remove_stale_caches,
)
from utilities.compiled_extensions import (  # noqa: E402
    ExtensionValidationError,
    _validate_relative_path,
    load_extension_manifest,
)


def _write_bundle(bundle_dir: Path, version: str) -> Path:
    bundle_dir.mkdir()
    (bundle_dir / "image.png").write_bytes(b"image")
    wheel_path = bundle_dir / "extension.whl"
    wheel_path.write_bytes(b"wheel")
    manifest = {
        "schema_version": 2,
        "id": "test_extension",
        "display_name": "Test Extension",
        "version": version,
        "core_api_version": 1,
        "placement_after": "Rat Farmer",
        "accepts_game_password": False,
        "requirements_html": "",
        "image": "image.png",
        "source": {
            "submodule_path": "private_sources/test_extension",
            "commit": "0123456789abcdef0123456789abcdef01234567",
        },
        "artifact": {
            "python_tag": "cp312",
            "platform_tag": "win_amd64",
            "wheel": "extension.whl",
            "sha256": hashlib.sha256(b"wheel").hexdigest(),
            "module": "test_extension",
            "callable": "main",
        },
        "license": {"scope": "test", "key_argument": "--license-key"},
        "args": [
            {
                "name": "--license-key",
                "label": "License Key",
                "type": "secret",
                "default": "",
            }
        ],
    }
    (bundle_dir / "extension.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_dir


def _write_wheel(wheel_path: Path, files: dict[str, bytes]) -> str:
    with zipfile.ZipFile(wheel_path, "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    return hashlib.sha256(wheel_path.read_bytes()).hexdigest()


class ExtensionPathSecurityTests(unittest.TestCase):
    def test_manifest_rejects_versions_that_are_not_safe_path_components(self):
        invalid_versions = (
            "../outside",
            "C:outside",
            "1.2/3",
            "1:2",
            "CON",
            "version.",
            "version with spaces",
        )
        for version in invalid_versions:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temporary:
                bundle_dir = _write_bundle(Path(temporary) / "bundle", version)
                with self.assertRaises(ExtensionValidationError):
                    load_extension_manifest(bundle_dir)

    def test_manifest_paths_reject_windows_drives_streams_and_reserved_names(self):
        invalid_paths = (
            "C:/outside.txt",
            "C:relative.txt",
            "assets/file.txt:secret",
            "NUL.txt",
            "folder/trailing. ",
            "folder//file.txt",
            "folder/./file.txt",
            "folder\\file.txt",
        )
        for relative_path in invalid_paths:
            with self.subTest(relative_path=relative_path):
                with self.assertRaises(ExtensionValidationError):
                    _validate_relative_path(relative_path)

    def test_wheel_rejects_unsafe_members_before_writing_any_content(self):
        unsafe_members = (
            "../escaped.py",
            "/absolute.py",
            "C:/escaped.py",
            "C:escaped.py",
            "package/module.py:payload",
            "NUL.txt",
            "package/trailing.",
            "package//module.py",
        )
        for member_name in unsafe_members:
            with self.subTest(member_name=member_name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                wheel_path = root / "malicious.whl"
                destination = root / "extracted"
                with zipfile.ZipFile(wheel_path, "w") as archive:
                    archive.writestr("safe.py", b"must not be written")
                    archive.writestr(member_name, b"malicious")

                with self.assertRaises(ExtensionValidationError):
                    _extract_wheel_safely(wheel_path, destination)

                self.assertEqual(list(destination.iterdir()), [])
                self.assertFalse((root / "escaped.py").exists())

    def test_wheel_rejects_symlink_members_before_writing_any_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel_path = root / "symlink.whl"
            destination = root / "extracted"
            symlink = zipfile.ZipInfo("linked.py")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(wheel_path, "w") as archive:
                archive.writestr("safe.py", b"must not be written")
                archive.writestr(symlink, "outside.py")

            with self.assertRaises(ExtensionValidationError):
                _extract_wheel_safely(wheel_path, destination)

            self.assertEqual(list(destination.iterdir()), [])

    def test_prepare_cache_rejects_a_version_before_creating_or_removing_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {
                "id": "test_extension",
                "version": "../outside",
                "artifact": {"sha256": "a" * 64},
            }
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "preserve.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with patch("compiled_extension_runner.default_extension_cache_root", return_value=root / "cache"):
                with self.assertRaises(ExtensionValidationError):
                    _prepare_cache(manifest)

            self.assertTrue(sentinel.is_file())
            self.assertFalse((root / "cache").exists())

    def test_cache_cleanup_refuses_to_remove_its_root_or_follow_an_external_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extension_root = root / "cache" / "test_extension"
            extension_root.mkdir(parents=True)
            root_sentinel = extension_root / "preserve.txt"
            root_sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaises(ExtensionValidationError):
                _remove_path_safely(extension_root, extension_root)
            self.assertTrue(root_sentinel.is_file())

            outside = root / "outside"
            outside.mkdir()
            outside_sentinel = outside / "preserve.txt"
            outside_sentinel.write_text("keep", encoding="utf-8")
            external_link = extension_root / "stale-cache"
            try:
                external_link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlinks are unavailable: {exc}")

            _remove_stale_caches(extension_root, extension_root / "current-cache")
            self.assertTrue(outside_sentinel.is_file())

    def test_compiled_extension_consumes_the_environment_password_without_native_execution(self):
        environment_name = "AUTOFARMERS_GAME_PASSWORD"
        manifest = {"accepts_game_password": True}
        with patch.dict(os.environ, {environment_name: "test-password"}):
            args, password = _consume_extension_game_password(manifest, ["--mode", "fast"])
            self.assertNotIn(environment_name, os.environ)

        self.assertEqual(args, ["--mode", "fast"])
        self.assertEqual(password, "test-password")

    def test_compiled_extension_retains_cli_password_compatibility_with_a_warning(self):
        manifest = {"accepts_game_password": True}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            args, password = _consume_extension_game_password(
                manifest,
                ["--mode", "fast", "--password", "legacy-cli-value"],
            )

        self.assertEqual(args, ["--mode", "fast"])
        self.assertEqual(password, "legacy-cli-value")
        self.assertTrue(any("process listings" in str(item.message) for item in caught))

    def test_cache_repairs_modified_extra_missing_and_symlink_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel_path = root / "extension.whl"
            module_contents = b"verified module"
            resource_contents = b"verified resource"
            wheel_hash = _write_wheel(
                wheel_path,
                {
                    "extension_module.py": module_contents,
                    "assets/data.bin": resource_contents,
                },
            )
            manifest = {
                "id": "cache_test",
                "version": "1.0.0",
                "wheel_path": str(wheel_path),
                "artifact": {"sha256": wheel_hash},
            }
            cache_root = root / "cache"
            with patch("compiled_extension_runner.default_extension_cache_root", return_value=cache_root):
                cache_dir = _prepare_cache(manifest)
                module_path = cache_dir / "extension_module.py"
                resource_path = cache_dir / "assets" / "data.bin"
                self.assertEqual(module_path.read_bytes(), module_contents)
                self.assertEqual(resource_path.read_bytes(), resource_contents)

                module_path.write_bytes(b"tampered module")
                _prepare_cache(manifest)
                self.assertEqual(module_path.read_bytes(), module_contents)

                (cache_dir / "extra.py").write_bytes(b"extra")
                _prepare_cache(manifest)
                self.assertFalse((cache_dir / "extra.py").exists())

                resource_path.unlink()
                _prepare_cache(manifest)
                self.assertEqual(resource_path.read_bytes(), resource_contents)

                marker = cache_dir / ".autofarmers-extension.json"
                marker.write_text("{\"wheel_sha256\":\"wrong\"}", encoding="utf-8")
                _prepare_cache(manifest)
                self.assertEqual(module_path.read_bytes(), module_contents)

                outside = root / "outside.txt"
                outside.write_bytes(b"keep")
                link = cache_dir / "linked.py"
                try:
                    link.symlink_to(outside)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"file symlinks are unavailable: {exc}")
                _prepare_cache(manifest)
                self.assertEqual(outside.read_bytes(), b"keep")
                self.assertFalse(link.exists())
                self.assertFalse(link.is_symlink())

    def test_cache_rechecks_the_wheel_hash_before_snapshot_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel_path = root / "extension.whl"
            original_hash = _write_wheel(wheel_path, {"module.py": b"verified"})
            wheel_path.write_bytes(b"replacement after manifest verification")
            manifest = {
                "id": "snapshot_test",
                "version": "1.0.0",
                "wheel_path": str(wheel_path),
                "artifact": {"sha256": original_hash},
            }
            cache_root = root / "cache"
            with patch("compiled_extension_runner.default_extension_cache_root", return_value=cache_root):
                with self.assertRaises(ExtensionValidationError):
                    _prepare_cache(manifest)

            self.assertFalse((cache_root / "snapshot_test" / f"1.0.0-{original_hash[:12]}").exists())

    def test_import_uses_a_module_from_the_verified_cache_even_if_preloaded_elsewhere(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel_path = root / "extension.whl"
            source_commit = "0123456789abcdef0123456789abcdef01234567"
            module_source = (
                "__version__ = '1.0.0'\n"
                "CORE_API_VERSION = 1\n"
                f"def self_test(): return {{'source_commit': '{source_commit}'}}\n"
                "def main(args): return None\n"
            ).encode("utf-8")
            wheel_hash = _write_wheel(wheel_path, {"verified_extension.py": module_source})
            manifest = {
                "version": "1.0.0",
                "source": {"commit": source_commit},
                "artifact": {"sha256": wheel_hash, "module": "verified_extension"},
            }
            outside_module = types.ModuleType("verified_extension")
            outside_module.__file__ = str(root / "outside.py")
            sys.modules["verified_extension"] = outside_module
            cache_path_prefix = str((root / "cache").resolve()) + os.sep
            try:
                with patch("compiled_extension_runner.default_extension_cache_root", return_value=root / "cache"):
                    cache_dir = _prepare_cache({
                        "id": "import_test",
                        "version": "1.0.0",
                        "wheel_path": str(wheel_path),
                        "artifact": {"sha256": wheel_hash},
                    })
                    module, contract = _load_module(manifest, cache_dir)

                self.assertIsNot(module, outside_module)
                self.assertEqual(contract["source_commit"], source_commit)
                self.assertTrue(Path(module.__file__).resolve().is_relative_to(cache_dir.resolve()))
            finally:
                sys.modules.pop("verified_extension", None)
                sys.path[:] = [entry for entry in sys.path if not entry.startswith(cache_path_prefix)]


if __name__ == "__main__":
    unittest.main()
