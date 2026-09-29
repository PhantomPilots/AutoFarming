"""Behavioral checks for DPAPI storage and safe legacy credential migration."""

from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utilities import account_credentials, app_config, secure_store  # noqa: E402


def _dpapi_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32crypt

        return hasattr(win32crypt, "CryptProtectData") and hasattr(win32crypt, "CryptUnprotectData")
    except ImportError:
        return False


class ProtectedStoreTests(unittest.TestCase):
    @unittest.skipUnless(_dpapi_available(), "Windows current-user DPAPI is required")
    def test_real_dpapi_round_trip_keeps_values_encrypted_on_disk(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = Path(directory) / "test-credentials.dpapi"
            sample_password = "dpapi-round-trip-probe"
            sample_accounts = [{"user": "test-label", "sync": "sync-probe", "password": "account-probe"}]

            secure_store.save_game_password(sample_password, path)
            self.assertTrue(secure_store.load_game_password(path) == sample_password)
            encrypted = path.read_bytes()
            self.assertTrue(sample_password.encode("utf-8") not in encrypted)

            secure_store.save_accounts(sample_accounts, path)
            self.assertTrue(secure_store.load_accounts(path) == sample_accounts)
            encrypted = path.read_bytes()
            self.assertTrue(b"sync-probe" not in encrypted)
            self.assertTrue(b"account-probe" not in encrypted)

    @unittest.skipUnless(_dpapi_available(), "Windows current-user DPAPI is required")
    def test_failed_atomic_replace_preserves_previous_protected_store(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = Path(directory) / "test-credentials.dpapi"
            secure_store.save_game_password("original-probe", path)
            original = path.read_bytes()

            with patch("utilities.secure_store.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(secure_store.CredentialStoreError):
                    secure_store.save_game_password("replacement-probe", path)

            self.assertTrue(path.read_bytes() == original)
            self.assertTrue(secure_store.load_game_password(path) == "original-probe")
            self.assertEqual(list(Path(directory).glob(".credentials-*.tmp")), [])


class GamePasswordMigrationTests(unittest.TestCase):
    def _config_file(self, directory: str, data: dict) -> Path:
        path = Path(directory) / "config.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    def test_legacy_password_is_protected_before_yaml_is_cleared(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._config_file(
                directory,
                {"game_password": "legacy-probe", "game_version": "global"},
            )
            protected_values = []

            def save_protected(value):
                self.assertTrue("legacy-probe" in path.read_text(encoding="utf-8"))
                protected_values.append(value)

            with (
                patch.object(app_config, "get_config_yaml_path", return_value=str(path)),
                patch.object(app_config, "load_protected_game_password", return_value=""),
                patch.object(app_config, "save_protected_game_password", side_effect=save_protected),
            ):
                result = app_config.load_game_password()

            self.assertTrue(result == "legacy-probe")
            self.assertTrue(protected_values == ["legacy-probe"])
            sanitized = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertNotIn("game_password", sanitized)
            self.assertEqual(sanitized["game_version"], "global")

    def test_failed_protection_preserves_legacy_config_byte_for_byte(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._config_file(directory, {"game_password": "legacy-probe"})
            original = path.read_bytes()
            with (
                patch.object(app_config, "get_config_yaml_path", return_value=str(path)),
                patch.object(app_config, "load_protected_game_password", return_value=""),
                patch.object(
                    app_config,
                    "save_protected_game_password",
                    side_effect=secure_store.CredentialStoreError("simulated DPAPI failure"),
                ),
            ):
                with self.assertRaises(secure_store.CredentialStoreError):
                    app_config.load_game_password()
            self.assertTrue(path.read_bytes() == original)

    def test_conflicting_protected_and_legacy_password_is_not_discarded(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._config_file(directory, {"game_password": "legacy-probe"})
            original = path.read_bytes()
            with (
                patch.object(app_config, "get_config_yaml_path", return_value=str(path)),
                patch.object(app_config, "load_protected_game_password", return_value="protected-probe"),
            ):
                with self.assertRaises(secure_store.CredentialStoreError):
                    app_config.load_game_password()
            self.assertTrue(path.read_bytes() == original)

    def test_malformed_config_is_preserved_on_load_and_save(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = Path(directory) / "config.yaml"
            path.write_text("game_password: [unfinished", encoding="utf-8")
            original = path.read_bytes()
            with patch.object(app_config, "get_config_yaml_path", return_value=str(path)):
                with self.assertRaises(secure_store.CredentialStoreError):
                    app_config.load_game_password()
                with self.assertRaises(secure_store.CredentialStoreError):
                    app_config.save_config_updates({"game_version": "japan"})
            self.assertTrue(path.read_bytes() == original)

    def test_gui_save_never_writes_password_to_yaml(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._config_file(directory, {"game_version": "global"})
            protected_values = []
            with (
                patch.object(app_config, "get_config_yaml_path", return_value=str(path)),
                patch.object(app_config, "save_protected_game_password", side_effect=protected_values.append),
                patch.object(app_config.config, "reload"),
            ):
                app_config.save_config_updates(
                    {"game_password": "new-password-probe", "game_version": "japan"}
                )
            saved_text = path.read_text(encoding="utf-8")
            self.assertTrue(protected_values == ["new-password-probe"])
            self.assertTrue("new-password-probe" not in saved_text)
            self.assertNotIn("game_password", yaml.safe_load(saved_text))

    def test_settings_save_omits_password_after_load_error_until_user_edits(self):
        gui_source = (SCRIPT_DIR / "AutoFarmers.py").read_text(encoding="utf-8")
        parsed = ast.parse(gui_source)
        settings = next(
            node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == "SettingsTab"
        )
        password_update = next(
            node
            for node in settings.body
            if isinstance(node, ast.FunctionDef) and node.name == "_password_update_for_save"
        )
        on_save = next(
            node for node in settings.body if isinstance(node, ast.FunctionDef) and node.name == "on_save"
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_password_update_for_save"
                for node in ast.walk(on_save)
            )
        )
        module = ast.Module(body=[password_update], type_ignores=[])
        namespace: dict[str, object] = {}
        exec(compile(ast.fix_missing_locations(module), "AutoFarmers.py", "exec"), namespace)

        settings_state = SimpleNamespace(
            _password_load_failed=True,
            _password_user_edited=False,
            password_edit=SimpleNamespace(text=lambda: ""),
        )
        self.assertEqual(namespace["_password_update_for_save"](settings_state), {})
        settings_state._password_user_edited = True
        settings_state.password_edit = SimpleNamespace(text=lambda: "explicit-choice")
        self.assertEqual(
            namespace["_password_update_for_save"](settings_state),
            {"game_password": "explicit-choice"},
        )


class MultiAccountMigrationTests(unittest.TestCase):
    def _accounts_file(self, directory: str, data: dict) -> Path:
        path = Path(directory) / "accounts.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    def test_placeholder_template_is_not_imported_or_stored(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._accounts_file(
                directory,
                {"accounts": [{"user": "example", "sync": "...", "password": "..."}]},
            )
            original = path.read_bytes()
            with (
                patch.object(account_credentials, "load_accounts", return_value=[]),
                patch.object(account_credentials, "save_accounts") as save_accounts,
            ):
                result = account_credentials.load_accounts_with_migration(
                    accounts_path=path,
                    store_path=Path(directory) / "account-store.dpapi",
                )
            self.assertEqual(result, [])
            save_accounts.assert_not_called()
            self.assertTrue(path.read_bytes() == original)

    def test_legacy_accounts_are_saved_before_yaml_is_cleared(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            accounts = [{"user": "legacy-label", "sync": "sync-probe", "password": "password-probe"}]
            path = self._accounts_file(directory, {"accounts": accounts})
            saved_values = []

            def save_protected(value, store_path):
                self.assertTrue("sync-probe" in path.read_text(encoding="utf-8"))
                saved_values.extend(value)

            with (
                patch.object(account_credentials, "load_accounts", return_value=[]),
                patch.object(account_credentials, "save_accounts", side_effect=save_protected),
            ):
                result = account_credentials.load_accounts_with_migration(
                    accounts_path=path,
                    store_path=Path(directory) / "account-store.dpapi",
                )

            self.assertTrue(result == accounts)
            self.assertTrue(saved_values == accounts)
            self.assertEqual(yaml.safe_load(path.read_text(encoding="utf-8"))["accounts"], [])

    def test_failed_account_protection_preserves_legacy_yaml_byte_for_byte(self):
        with tempfile.TemporaryDirectory(dir=SCRIPT_DIR) as directory:
            path = self._accounts_file(
                directory,
                {"accounts": [{"user": "legacy-label", "sync": "sync-probe", "password": "password-probe"}]},
            )
            original = path.read_bytes()
            with (
                patch.object(account_credentials, "load_accounts", return_value=[]),
                patch.object(
                    account_credentials,
                    "save_accounts",
                    side_effect=secure_store.CredentialStoreError("simulated DPAPI failure"),
                ),
            ):
                with self.assertRaises(secure_store.CredentialStoreError):
                    account_credentials.load_accounts_with_migration(
                        accounts_path=path,
                        store_path=Path(directory) / "account-store.dpapi",
                    )
            self.assertTrue(path.read_bytes() == original)


if __name__ == "__main__":
    unittest.main()
