"""Migration and import helpers for encrypted multi-account credentials."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

import yaml

from utilities.app_config import get_config_yaml_path
from utilities.secure_store import CredentialStoreError, load_accounts, save_accounts


class AccountCredentialsError(RuntimeError):
    """Raised when account credentials cannot be migrated without data loss."""


_PLACEHOLDER_VALUES = {"", "..."}


def get_legacy_accounts_path() -> Path:
    return Path(get_config_yaml_path()).with_name("accounts.yaml")


def _read_legacy_accounts(path: str | os.PathLike[str] | None = None) -> tuple[dict, list]:
    source = Path(path) if path is not None else get_legacy_accounts_path()
    try:
        with source.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except FileNotFoundError:
        return {}, []
    except (OSError, yaml.YAMLError) as exc:
        raise AccountCredentialsError("The legacy accounts file could not be read safely.") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise AccountCredentialsError("The legacy accounts file has an invalid format.")
    rows = data.get("accounts", [])
    if not isinstance(rows, list):
        raise AccountCredentialsError("The legacy accounts file has an invalid account list.")
    return data, rows


def _extract_legacy_accounts(rows: list) -> list[dict[str, str]]:
    accounts: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise AccountCredentialsError("The legacy accounts file has an invalid account entry.")
        sync = str(row.get("sync") or "").strip()
        password = str(row.get("password") or "").strip()
        if sync in _PLACEHOLDER_VALUES and password in _PLACEHOLDER_VALUES:
            continue
        user = str(row.get("user") or "").strip()
        if not user or sync in _PLACEHOLDER_VALUES or password in _PLACEHOLDER_VALUES:
            raise AccountCredentialsError(
                "A legacy account is incomplete. The file was left unchanged; complete it or use ImportAccounts.py."
            )
        accounts.append({"user": user, "sync": sync, "password": password})
    return accounts


def _atomic_write_accounts_yaml(data: dict, path: str | os.PathLike[str]) -> None:
    destination = Path(path)
    temp_path: str | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix="accounts_",
            suffix=".yaml.tmp",
            dir=str(destination.parent),
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            yaml.safe_dump(data, stream, default_flow_style=False, sort_keys=False, allow_unicode=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
        temp_path = None
    except Exception as exc:
        raise AccountCredentialsError(
            "Protected accounts were saved, but the legacy accounts file could not be cleared."
        ) from exc
    finally:
        if temp_path is not None:
            with contextlib.suppress(OSError):
                os.remove(temp_path)


def _clear_legacy_accounts(data: dict, path: str | os.PathLike[str]) -> None:
    sanitized = dict(data)
    sanitized["accounts"] = []
    _atomic_write_accounts_yaml(sanitized, path)


def _merge_accounts(
    protected: list[dict[str, str]],
    legacy: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged = list(protected)
    by_user = {account["user"]: account for account in protected}
    for account in legacy:
        previous = by_user.get(account["user"])
        if previous is None:
            merged.append(account)
            by_user[account["user"]] = account
        elif previous != account:
            raise AccountCredentialsError(
                "A saved account conflicts with a legacy account. The legacy file was preserved; "
                "use ImportAccounts.py --replace to choose the account list."
            )
    return merged


def load_accounts_with_migration(
    accounts_path: str | os.PathLike[str] | None = None,
    store_path: str | os.PathLike[str] | None = None,
) -> list[dict[str, str]]:
    """Load encrypted accounts, migrating configured legacy YAML only after DPAPI succeeds."""
    legacy_path = Path(accounts_path) if accounts_path is not None else get_legacy_accounts_path()
    data, rows = _read_legacy_accounts(legacy_path)
    legacy_accounts = _extract_legacy_accounts(rows)
    protected_accounts = load_accounts(store_path)

    if protected_accounts:
        merged_accounts = _merge_accounts(protected_accounts, legacy_accounts)
        if merged_accounts != protected_accounts:
            save_accounts(merged_accounts, store_path)
        if legacy_accounts:
            _clear_legacy_accounts(data, legacy_path)
        return merged_accounts

    if legacy_accounts:
        save_accounts(legacy_accounts, store_path)
        _clear_legacy_accounts(data, legacy_path)
        return legacy_accounts

    return []


def save_accounts_and_clear_legacy(
    accounts: list[dict[str, str]],
    accounts_path: str | os.PathLike[str] | None = None,
    store_path: str | os.PathLike[str] | None = None,
) -> None:
    """Protect a user-confirmed account list before clearing legacy YAML."""
    legacy_path = Path(accounts_path) if accounts_path is not None else get_legacy_accounts_path()
    data, _ = _read_legacy_accounts(legacy_path)
    normalized = _extract_legacy_accounts(accounts)
    if len(normalized) != len(accounts):
        raise AccountCredentialsError("Every imported account must include a label, sync code, and password.")
    save_accounts(normalized, store_path)
    _clear_legacy_accounts(data, legacy_path)
