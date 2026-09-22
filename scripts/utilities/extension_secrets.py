"""Read suite credentials written by validated compiled extensions."""

from __future__ import annotations

import os
from pathlib import Path


_DPAPI_MAGIC = b"AFDP1\x00"
_SUITE_LICENSE_FILE = "suite_license.bin"


def load_suite_license_key() -> str:
    """Return the CurrentUser-DPAPI protected suite key, or an empty string."""
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return ""
    path = Path(local_app_data) / "AutoFarmers" / "Licensing" / _SUITE_LICENSE_FILE
    try:
        protected = path.read_bytes()
        if not protected.startswith(_DPAPI_MAGIC):
            return ""
        import win32crypt

        _description, plaintext = win32crypt.CryptUnprotectData(
            protected[len(_DPAPI_MAGIC):], None, None, None, 0x1
        )
        value = plaintext.decode("ascii")
        return value if value and len(value) <= 512 else ""
    except Exception:
        return ""
