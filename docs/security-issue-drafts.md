# Security issues for Telepatya/AutoFarming

All five issues were created in the personal fork and linked to their separate fix
commits on `codex/security-revamp`. They remain open for tracking until integration.
The accidental upstream issues 34–38 were closed.

| Issue | Fix commit |
| --- | --- |
| [#1: Serialized artifacts](https://github.com/Telepatya/AutoFarming/issues/1) | `225688b` |
| [#2: Extension paths](https://github.com/Telepatya/AutoFarming/issues/2) | `95dd9f6` |
| [#3: Extension cache integrity](https://github.com/Telepatya/AutoFarming/issues/3) | `28569cf` |
| [#4: Password arguments](https://github.com/Telepatya/AutoFarming/issues/4) | `e4b2166` |
| [#5: Credential storage](https://github.com/Telepatya/AutoFarming/issues/5) | `90505fb` |

## Security: verify serialized models and training data before loading

Runtime models and training datasets deserialize dill/pickle without verifying provenance. Substituted files can execute code as the user.

Fix: anchor bundled paths, pin trusted legacy hashes and verify exact bytes before deserialization, reject unknown/modified legacy files, use non-executable numeric storage for new datasets, and add tampering/path tests. Trusted pickle remains executable; hashes are not a sandbox.

## Security: confine compiled-extension cache and archive paths

Manifest and archive path components reach filesystem writes and cleanup without complete Windows validation.

Fix: validate cache components, reject unsafe Windows archive paths and enforce resolved destination containment before filesystem operations. Add negative path regression tests.

## Security: verify extracted extension code before import

The runner verifies the source wheel but trusts extracted caches based only on a marker. Modified cached code may be imported without matching the verified artifact.

Fix: check file contents and inventory against the verified wheel, reject links/unexpected files, and ensure import origin matches the validated cache. Add tampering regression tests.

## Security: keep game passwords out of process command lines

The GUI passes game passwords to farmers in process arguments. Display masking does not hide OS command lines.

Fix: transfer GUI passwords outside argv, consume and remove the child payload promptly, cover built-in and compiled farmers, and test argument secrecy.

## Security: protect persisted credentials outside tracked YAML

The GUI writes game passwords to tracked YAML and multi-account setup directs users to store sync codes/passwords in tracked YAML. This exposes user-entered plaintext credentials to repository copies or accidental commits. Current committed account secrets are ellipsis placeholders, not confirmed real credentials.

Fix: use per-user OS-protected storage, migrate legacy settings safely without data loss, retain non-secret repository templates, and test persistence/migration failure cases.

