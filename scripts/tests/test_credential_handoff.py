"""Regression checks for GUI game-password handoff."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utilities.credential_handoff import GAME_PASSWORD_ENV, consume_game_password  # noqa: E402


class CredentialHandoffTests(unittest.TestCase):
    def test_child_consumes_environment_password_and_removes_it(self):
        child_env = os.environ.copy()
        child_env[GAME_PASSWORD_ENV] = "handoff-test-value"
        old_pythonpath = child_env.get("PYTHONPATH", "")
        child_env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(SCRIPT_DIR), old_pythonpath)))
        child = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; from utilities.credential_handoff import GAME_PASSWORD_ENV, consume_game_password; "
                "value = consume_game_password(); "
                "assert value == 'handoff-test-value'; "
                "assert GAME_PASSWORD_ENV not in os.environ",
            ],
            cwd=REPOSITORY_ROOT,
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(child.returncode, 0, "child should consume and remove its handed-off password")

    def test_legacy_cli_password_warns_and_still_consumes_environment(self):
        with patch.dict(os.environ, {GAME_PASSWORD_ENV: "environment-test-value"}):
            with self.assertWarnsRegex(UserWarning, "process listings"):
                password = consume_game_password("legacy-cli-test-value")
            self.assertTrue(password == "legacy-cli-test-value")
            self.assertNotIn(GAME_PASSWORD_ENV, os.environ)

    def test_gui_argument_builder_never_adds_game_password(self):
        gui_source = (SCRIPT_DIR / "AutoFarmers.py").read_text(encoding="utf-8")
        parsed = ast.parse(gui_source)
        controller = next(
            node
            for node in parsed.body
            if isinstance(node, ast.ClassDef) and node.name == "FarmerController"
        )
        method = next(
            node
            for node in controller.body
            if isinstance(node, ast.FunctionDef) and node.name == "_build_cli_args"
        )
        module = ast.Module(body=[method], type_ignores=[])
        namespace: dict[str, object] = {}
        exec(compile(ast.fix_missing_locations(module), "AutoFarmers.py", "exec"), namespace)

        stub_controller = SimpleNamespace(
            farmer={"args": [], "accepts_game_password": True, "script": "BirdFarmer.py"},
            _arg_values={},
        )
        self.assertEqual(namespace["_build_cli_args"](stub_controller), [])


if __name__ == "__main__":
    unittest.main()
