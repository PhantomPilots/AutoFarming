import hashlib
import os
import pickle
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utilities import artifact_security as security
from utilities.artifact_hashes import TRUSTED_LEGACY_DATA_SHA256, TRUSTED_MODEL_SHA256
from utilities.card_data import CardTypes


class ArtifactSecurityTests(unittest.TestCase):
    def temporary_data_path(self, suffix):
        return security.DATA_ROOT / f"codex_security_{uuid.uuid4().hex}{suffix}"

    def test_all_pinned_bundled_artifacts_match_and_legacy_data_loads(self):
        for name in TRUSTED_MODEL_SHA256:
            with self.subTest(model=name):
                path = security.model_path_for(name)
                self.assertTrue(path.is_file())
                raw_bytes = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), TRUSTED_MODEL_SHA256[name])

        for name in TRUSTED_LEGACY_DATA_SHA256:
            with self.subTest(dataset=name):
                path = security.DATA_ROOT / name
                data, labels = security.load_dataset_file(path)
                self.assertGreater(len(labels), 0)
                self.assertGreater(len(data), 0)

    def test_trusted_model_loads_from_repository_when_cwd_contains_shadow(self):
        with tempfile.TemporaryDirectory() as directory:
            shadow_root = Path(directory)
            (shadow_root / "models").mkdir()
            (shadow_root / "data").mkdir()
            (shadow_root / "models" / "card_type_predictor.svm").write_bytes(b"untrusted cwd shadow")
            (shadow_root / "data" / "card_types_data_0.npy").write_bytes(b"untrusted cwd shadow")
            original_cwd = Path.cwd()
            try:
                os.chdir(shadow_root)
                model_path = security.model_path_for("card_type_predictor.svm")
                self.assertEqual(model_path, security.MODEL_ROOT / "card_type_predictor.svm")
                model = security.load_trusted_model("card_type_predictor.svm")
                self.assertTrue(callable(model.predict))
                dataset_path, = security.dataset_paths("data/card_types_data_0.npy")
                self.assertEqual(dataset_path, security.DATA_ROOT / "card_types_data_0.npy")
                _, labels = security.load_dataset_file("data/card_types_data_0.npy")
                self.assertGreater(len(labels), 0)
            finally:
                os.chdir(original_cwd)

    def test_tampered_trusted_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tampered_path = Path(directory) / "card_type_predictor.svm"
            tampered_path.write_bytes(b"tampered bytes")
            with self.assertRaisesRegex(security.UnsafeArtifactError, "failed its SHA-256"):
                security._verified_pickle_bytes(tampered_path, TRUSTED_MODEL_SHA256, "model")

    def test_unknown_malicious_legacy_pickle_is_rejected_before_execution(self):
        marker = security.DATA_ROOT / f"pickle_was_executed_{uuid.uuid4().hex}"

        class MaliciousPayload:
            def __reduce__(self):
                return os.mkdir, (str(marker),)

        malicious_path = self.temporary_data_path(".npy")
        try:
            malicious_path.write_bytes(pickle.dumps(MaliciousPayload()))
            with self.assertRaisesRegex(security.UnsafeArtifactError, "SHA-256 is not pinned"):
                security.load_dataset_file(malicious_path)
            self.assertFalse(marker.exists())
        finally:
            malicious_path.unlink(missing_ok=True)
            if marker.exists():
                marker.rmdir()

    def test_paths_outside_artifact_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            outside_path = Path(directory) / "outside.bin"
            with self.assertRaises(security.UnsafeArtifactError):
                security.model_path_for(outside_path)
            with self.assertRaises(security.UnsafeArtifactError):
                security.dataset_path_for(outside_path)

    def test_new_npz_round_trip_uses_numeric_arrays(self):
        expected_data = np.arange(24, dtype=np.uint8).reshape(2, 3, 4)
        expected_labels = np.asarray([0, 1], dtype=np.int64)
        enum_labels = [CardTypes.ATTACK, CardTypes.STANCE]
        target = self.temporary_data_path(".npz")
        try:
            saved_path = security.save_dataset_file(target, expected_data, enum_labels)
            data, labels = security.load_dataset_file(saved_path)
        finally:
            target.unlink(missing_ok=True)
        np.testing.assert_array_equal(data, expected_data)
        np.testing.assert_array_equal(labels, expected_labels)
        self.assertEqual(labels.dtype.kind, "i")

    def test_card_type_enum_and_numeric_labels_normalize_for_training(self):
        legacy_labels = np.asarray([CardTypes.ULTIMATE, CardTypes.GROUND], dtype=object)
        expected_values = np.asarray([-1, 10], dtype=np.int64)

        normalized_legacy = security.labels_to_numpy_values(legacy_labels)
        normalized_numeric = security.labels_to_numpy_values(expected_values)

        self.assertEqual(normalized_legacy.dtype.kind, "i")
        np.testing.assert_array_equal(normalized_legacy, expected_values)
        np.testing.assert_array_equal(normalized_numeric, expected_values)

    def test_object_arrays_are_rejected_for_new_npz_data(self):
        target = self.temporary_data_path(".npz")
        with self.assertRaisesRegex(ValueError, "object arrays"):
            security.save_dataset_file(target, np.asarray([object()], dtype=object), np.asarray([1]))


if __name__ == "__main__":
    unittest.main()
