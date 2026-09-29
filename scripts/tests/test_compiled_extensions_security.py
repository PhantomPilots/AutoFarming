"""Behavioral security checks for compiled extension paths and wheel extraction."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiled_extension_runner import (  # noqa: E402
    _extract_wheel_safely,
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


if __name__ == "__main__":
    unittest.main()
