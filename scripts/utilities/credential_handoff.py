"""Short-lived, child-process handoff for secrets supplied by the GUI."""

import os
import warnings


GAME_PASSWORD_ENV = "AUTOFARMERS_GAME_PASSWORD"


def consume_game_password(cli_password: str | None = None) -> str | None:
    """Read and remove a GUI-supplied password from this process environment.

    The legacy CLI option remains available for direct script users, but the
    value is visible in process listings when passed as an argument.
    """
    handed_off_password = os.environ.pop(GAME_PASSWORD_ENV, None)
    if cli_password is not None:
        warnings.warn(
            "Passing --password may expose the password in process listings; "
            "use the GUI password setting for a private handoff.",
            UserWarning,
            stacklevel=2,
        )
        return cli_password
    return handed_off_password
