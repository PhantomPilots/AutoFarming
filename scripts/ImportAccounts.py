"""Interactively import multi-account credentials into the current-user DPAPI store."""

import argparse
from getpass import getpass

from utilities.account_credentials import (
    AccountCredentialsError,
    load_accounts_with_migration,
    save_accounts_and_clear_legacy,
)
from utilities.secure_store import CredentialStoreError, load_accounts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import game accounts into the encrypted per-user store.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the saved account list after re-entering the complete list.",
    )
    args = parser.parse_args(argv)

    try:
        saved_accounts = load_accounts_with_migration()
    except AccountCredentialsError:
        if not args.replace:
            print(
                "The legacy account file could not be combined safely. "
                "Review it, then rerun with --replace to enter the complete list."
            )
            return 1
        try:
            saved_accounts = load_accounts()
        except CredentialStoreError as exc:
            print(f"Could not read the protected account store: {exc}")
            return 1
    except CredentialStoreError as exc:
        print(f"Could not read the protected account store: {exc}")
        return 1

    if args.replace:
        accounts = []
        print("Enter the complete account list to replace the saved list.")
    elif saved_accounts:
        choice = input("Choose Add to append accounts, Replace to enter a new list, or Quit [A/R/Q]: ").strip().lower()
        if choice in ("q", "quit"):
            return 0
        if choice in ("r", "replace"):
            accounts = []
        elif choice in ("", "a", "add"):
            accounts = list(saved_accounts)
        else:
            print("No accounts were changed.")
            return 1
    else:
        accounts = []

    known_users = {account["user"].casefold() for account in accounts}
    added_count = 0
    while True:
        user = input("Account label (blank to finish): ").strip()
        if not user:
            break
        if user.casefold() in known_users:
            print("That account label is already saved. Choose a unique label.")
            continue
        sync = getpass("Sync code (input hidden): ").strip()
        password = getpass("Game password (input hidden): ").strip()
        if not sync or not password:
            print("Both values are required; this account was not added.")
            continue
        accounts.append({"user": user, "sync": sync, "password": password})
        known_users.add(user.casefold())
        added_count += 1

    if not added_count:
        print("No accounts were changed.")
        return 0

    try:
        save_accounts_and_clear_legacy(accounts)
    except (AccountCredentialsError, CredentialStoreError) as exc:
        print(f"Could not save the protected account list: {exc}")
        return 1

    print(f"Saved {len(accounts)} account(s) in the current Windows user's protected store.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
