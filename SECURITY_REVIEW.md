# Security review — 2026-09-29

Quick source review of the Windows desktop application, its model/training-data loaders,
compiled-extension runner, credential handling, and repository workflow. Work belongs
to the personal fork `Telepatya/AutoFarming`, on `codex/security-revamp`.

## Confirmed findings

| Finding | Impact and prerequisite | Fix direction |
| --- | --- | --- |
| Unverified pickle/dill model and dataset loading | A substituted artifact can execute Python code when loaded. Relative paths also permit working-directory substitution. | Anchor paths and verify exact legacy bytes against source-pinned hashes; collect new data in numeric NPZ format. |
| Unsafe extension filesystem paths | Malformed manifest versions or Windows archive names can escape the intended write/cleanup location. | Validate path components and enforce containment before filesystem operations. |
| Marker-only extension cache trust | Modified extracted executable files can be imported despite verification of the original wheel. | Verify the extracted inventory and bytes against the wheel and check import origin. |
| Game passwords in process arguments | GUI-launched passwords are visible to observers with access to process command lines. | Hand off passwords outside argv and remove the child environment value after consumption. |
| Plaintext credentials in tracked configuration | User-entered passwords and account sync codes can enter repository copies and accidental commits. | Use per-user Windows-protected storage and safe migration from legacy configuration. |

The committed multi-account secret fields contain `...` placeholders. This review
does **not** establish exposure of real credentials from that file. Users who previously
published real values must rotate them; removing current values cannot erase Git history.

## Scope limits

This is a quick pass, not an exhaustive security audit. Native extension binaries and
their private source were not independently audited. No complete dependency advisory
scan was performed. Opt-in notification screenshots are documented external transfers.

Legacy pickle artifacts remain executable trusted code. Hash pinning rejects substituted
artifacts but does not protect an installation whose source code or pinned hashes an
attacker can also change. The same-user process environment and filesystem are not an
isolation boundary against malware running as that user or an administrator.

See [scikit-learn's model persistence guidance](https://scikit-learn.org/stable/model_persistence.html)
for the risks of pickle-based formats.
