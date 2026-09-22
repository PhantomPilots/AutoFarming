"""Release-time verification for public compiled-extension bundles."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

from utilities.compiled_extensions import discover_compiled_extensions


_PROHIBITED_WHEEL_SUFFIXES = (".py", ".pyx", ".pxi", ".c", ".pdb", ".html")


def _gitlink_commit(repo_root: Path, submodule_path: str) -> str:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--", submodule_path],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError(f"Missing submodule gitlink: {submodule_path}")
    fields = result.stdout.split(None, 3)
    if len(fields) < 4 or fields[0] != "160000":
        raise ValueError(f"Expected a submodule gitlink at {submodule_path}")
    return fields[1].lower()


def _verify_private_ancestry(
    repo_root: Path,
    submodule_path: str,
    source_commit: str,
    gitlink_commit: str,
):
    """Verify private history when a maintainer has initialized the submodule."""
    checkout = repo_root / submodule_path
    if not (checkout / ".git").exists():
        return

    for commit, label in ((source_commit, "artifact source"), (gitlink_commit, "suite gitlink")):
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=checkout,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise ValueError(f"Private checkout does not contain {label} commit {commit}")

    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, gitlink_commit],
        cwd=checkout,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(
            f"Artifact source {source_commit} is not an ancestor of suite gitlink {gitlink_commit}"
        )


def _verify_wheel(manifest: dict):
    wheel_path = Path(manifest["wheel_path"])
    with zipfile.ZipFile(wheel_path) as archive:
        members = [member.filename for member in archive.infolist() if not member.is_dir()]
    prohibited = [name for name in members if name.lower().endswith(_PROHIBITED_WHEEL_SUFFIXES)]
    if prohibited:
        raise ValueError(f"{manifest['id']} wheel contains prohibited source/debug files: {prohibited}")
    native_modules = [name for name in members if name.lower().endswith(".pyd")]
    if len(native_modules) != 1:
        raise ValueError(f"{manifest['id']} wheel must contain exactly one native .pyd module")


def verify_repository(repo_root: Path) -> list[dict]:
    vendor_dir = repo_root / "scripts" / "vendor"
    manifests, warnings = discover_compiled_extensions(vendor_dir)
    if warnings:
        raise ValueError("\n".join(warnings))
    if not manifests:
        raise ValueError(f"No compiled extensions were found in {vendor_dir}")

    for manifest in manifests:
        _verify_wheel(manifest)
        source = manifest["source"]
        gitlink_commit = _gitlink_commit(repo_root, source["submodule_path"])
        _verify_private_ancestry(
            repo_root,
            source["submodule_path"],
            source["commit"],
            gitlink_commit,
        )
    return manifests


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify committed compiled-extension releases")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifests = verify_repository(args.repo_root.resolve())
        if args.self_test:
            from compiled_extension_runner import run_bundle

            for manifest in manifests:
                return_code = run_bundle(Path(manifest["bundle_dir"]), [], self_test=True)
                if return_code:
                    raise ValueError(f"{manifest['id']} self-test returned {return_code}")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Compiled extension verification failed: {exc}", file=sys.stderr)
        return 1

    for manifest in manifests:
        print(
            f"Verified {manifest['id']} {manifest['version']} "
            f"from {manifest['source']['commit']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
