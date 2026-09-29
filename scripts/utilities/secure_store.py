"""Current-user DPAPI storage for AutoFarmers credentials."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


class CredentialStoreError(RuntimeError):
    """Raised when credentials cannot be safely read or saved."""


_STORE_LOCK = threading.RLock()
_STORE_VERSION = 1


def _get_store_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise CredentialStoreError("The Windows per-user application data directory is unavailable.")
    return Path(local_app_data) / "AutoFarmers"


def get_game_password_store_path() -> Path:
    return _get_store_directory() / "game_password.dpapi"


def get_accounts_store_path() -> Path:
    return _get_store_directory() / "accounts.dpapi"


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise CredentialStoreError("Windows current-user credential protection is unavailable.")
    try:
        import win32crypt

        return win32crypt.CryptProtectData(data, "AutoFarmers credentials", None, None, None, 0)
    except Exception as exc:
        raise CredentialStoreError("Windows could not protect the credential data for this user.") from exc


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise CredentialStoreError("Windows current-user credential protection is unavailable.")
    try:
        import win32crypt

        return win32crypt.CryptUnprotectData(data, None, None, None, 0)[1]
    except Exception as exc:
        raise CredentialStoreError("Windows could not decrypt the credential data for this user.") from exc


def _normalize_store(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CredentialStoreError("The protected credential store has an invalid format.")
    if value.get("version") != _STORE_VERSION:
        raise CredentialStoreError("The protected credential store has an unsupported version.")

    normalized: dict[str, Any] = {"version": _STORE_VERSION}
    password = value.get("game_password")
    if password is not None:
        if not isinstance(password, str):
            raise CredentialStoreError("The protected credential store has an invalid password entry.")
        if password:
            normalized["game_password"] = password

    accounts = value.get("accounts")
    if accounts is not None:
        if not isinstance(accounts, list) or any(not isinstance(account, dict) for account in accounts):
            raise CredentialStoreError("The protected credential store has invalid account entries.")
        normalized_accounts: list[dict[str, str]] = []
        for account in accounts:
            if any(not isinstance(account.get(key), str) for key in ("user", "sync", "password")):
                raise CredentialStoreError("The protected credential store has an invalid account entry.")
            normalized_accounts.append(
                {
                    "user": account["user"],
                    "sync": account["sync"],
                    "password": account["password"],
                }
            )
        if normalized_accounts:
            normalized["accounts"] = normalized_accounts
    return normalized


def load_credentials(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Read and decrypt the credential store; an absent store is an empty one."""
    store_path = Path(path) if path is not None else get_credential_store_path()
    with _STORE_LOCK:
        try:
            encrypted = store_path.read_bytes()
        except FileNotFoundError:
            return {"version": _STORE_VERSION}
        except OSError as exc:
            raise CredentialStoreError("The protected credential store could not be read.") from exc

        try:
            decoded = _unprotect(encrypted).decode("utf-8")
            return _normalize_store(json.loads(decoded))
        except CredentialStoreError:
            raise
        except Exception as exc:
            raise CredentialStoreError("The protected credential store is invalid or unreadable.") from exc


def save_credentials(
    credentials: dict[str, Any],
    path: str | os.PathLike[str] | None = None,
) -> None:
    """Protect credentials before writing, then atomically replace the store."""
    store_path = Path(path) if path is not None else get_credential_store_path()
    value = dict(credentials)
    value["version"] = _STORE_VERSION
    normalized = _normalize_store(value)
    plaintext = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = _protect(plaintext)

    with _STORE_LOCK:
        temporary_path: str | None = None
        try:
            store_path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_path = tempfile.mkstemp(
                prefix=".credentials-",
                suffix=".tmp",
                dir=str(store_path.parent),
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, store_path)
            temporary_path = None
        except OSError as exc:
            raise CredentialStoreError("The protected credential store could not be saved.") from exc
        finally:
            if temporary_path is not None:
                with contextlib.suppress(OSError):
                    os.remove(temporary_path)


def load_game_password(path: str | os.PathLike[str] | None = None) -> str:
    store_path = Path(path) if path is not None else get_game_password_store_path()
    return str(load_credentials(store_path).get("game_password", ""))


def save_game_password(password: str, path: str | os.PathLike[str] | None = None) -> None:
    store_path = Path(path) if path is not None else get_game_password_store_path()
    with _STORE_LOCK:
        credentials = load_credentials(store_path)
        if password:
            credentials["game_password"] = password
        else:
            credentials.pop("game_password", None)
        save_credentials(credentials, store_path)


def load_accounts(path: str | os.PathLike[str] | None = None) -> list[dict[str, str]]:
    store_path = Path(path) if path is not None else get_accounts_store_path()
    return list(load_credentials(store_path).get("accounts", []))


def save_accounts(accounts: list[dict[str, str]], path: str | os.PathLike[str] | None = None) -> None:
    store_path = Path(path) if path is not None else get_accounts_store_path()
    with _STORE_LOCK:
        credentials = load_credentials(store_path)
        if accounts:
            credentials["accounts"] = accounts
        else:
            credentials.pop("accounts", None)
        save_credentials(credentials, store_path)
