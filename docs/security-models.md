# Model and dataset files

The bundled scikit-learn models use dill, a pickle-based format. Loading a
pickle can run code, so the bot now verifies a model's exact SHA-256 bytes
against the source-pinned entries in
[`scripts/utilities/artifact_hashes.py`](../scripts/utilities/artifact_hashes.py)
before deserializing it. Model and dataset paths are resolved from the
repository location, independent of the current working directory. Paths
outside `scripts/models` or `scripts/data`, modified bundled files, and legacy
pickle files absent from the pinned list are rejected.

The bundled `.npy` dataset files are legacy dill pickles despite their
extension. They remain readable only when their exact bytes match the pinned
hash. New data collection writes `.npz` files containing `data` and `labels`;
the loader uses `numpy.load(..., allow_pickle=False)` and rejects object arrays.
Unknown legacy files are not deserialized or converted automatically.

Training can still save a model with `save_model`, but a newly generated model
is not loadable until a maintainer reviews its provenance and explicitly adds
its SHA-256 digest to the source allowlist. Never add a digest automatically
from a file presented at runtime. This integrity check protects the bundled
assets against replacement and current-directory shadowing; it is not a
signature and does not protect against a code change that also changes the
allowlist. Keep model and allowlist changes in reviewed source control.

The [scikit-learn model persistence guide](https://scikit-learn.org/stable/model_persistence.html)
explains that pickle-based persistence can execute arbitrary code when loaded
and discusses safer alternatives such as `skops.io`.
