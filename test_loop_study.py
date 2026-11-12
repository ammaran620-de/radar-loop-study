"""Checks for geometric transforms and abstaining decision accounting."""
import unittest

import numpy as np

from geometric_verification import rigid_fit, verify_pair
from loop_closure_study import evaluate_decisions, candidate_packet
from learned_descriptor import load_model, EXPECTED_CHECKPOINT_SHA256
from experiment import similarity


class LoopStudyTests(unittest.TestCase):
    def test_frozen_checkpoint_outputs_finite_256_vector(self):
        import torch
        model, checksum = load_model()
        self.assertEqual(checksum, EXPECTED_CHECKPOINT_SHA256)
        with torch.inference_mode():
            result = model({"radar_batch": torch.zeros((1, 1, 128, 384))})
        self.assertEqual(tuple(result.shape), (1, 256))
        self.assertTrue(torch.isfinite(result).all())

    def test_sector_yaw_has_query_to_reference_sign(self):
        query = np.zeros((60, 32))
        query[2, 7] = 1
        reference = np.roll(query, 5, axis=0)
        _, shift = similarity(query, reference)
        self.assertEqual(shift, 5)

    def test_packet_excludes_ground_truth_labels(self):
        packet = candidate_packet({"id": "q", "timestamp_us": 123, "x": 999,
            "y": 888, "nearest_reference_distance_m": 500, "candidates": [{
            "reference_id": "r", "score": 0.9, "distance_m": 500,
            "verification": {"accepted": True, "yaw_rad": 0.1,
                             "translation_xy_m": [1, 2]}}]})
        self.assertEqual(packet["decision"], "provisional_candidate")
        self.assertNotIn("distance_m", packet["evidence"][0])
        self.assertNotIn("x", packet)

    def test_rigid_transform_recovers_known_rotation_translation(self):
        rng = np.random.default_rng(7)
        source = rng.normal(size=(80, 2)) * 10
        yaw = 0.4
        rotation = np.array([[np.cos(yaw), -np.sin(yaw)],
                             [np.sin(yaw), np.cos(yaw)]])
        translation = np.array([2.0, -1.5])
        target = source @ rotation.T + translation
        estimated_r, estimated_t = rigid_fit(source, target)
        np.testing.assert_allclose(estimated_r, rotation, atol=1e-10)
        np.testing.assert_allclose(estimated_t, translation, atol=1e-10)

    def test_registration_accepts_known_alignment(self):
        rng = np.random.default_rng(8)
        theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
        radius = rng.uniform(10, 40, size=200)
        source = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
        yaw = 0.3
        rotation = np.array([[np.cos(yaw), -np.sin(yaw)],
                             [np.sin(yaw), np.cos(yaw)]])
        translation = np.array([2.0, -1.0])
        target = source @ rotation.T + translation
        result = verify_pair(source, target, yaw)
        self.assertTrue(result["accepted"])
        np.testing.assert_allclose(result["translation_xy_m"], translation, atol=1e-5)

    def test_insufficient_returns_abstains(self):
        result = verify_pair(np.zeros((3, 2)), np.zeros((30, 2)), 0)
        self.assertFalse(result["accepted"])

    def test_policy_does_not_use_labels_to_pick_later_true_match(self):
        queries = [{
            "nearest_reference_distance_m": 1,
            "candidates": [
                {"distance_m": 500, "verification": {"accepted": True}},
                {"distance_m": 1, "verification": {"accepted": True}},
            ],
        }]
        result = evaluate_decisions(queries, 25)
        self.assertEqual(result["false_accepted"], 1)
        self.assertEqual(result["correct_accepted"], 0)

    def test_all_rejected_has_undefined_precision(self):
        result = evaluate_decisions([{
            "nearest_reference_distance_m": 1,
            "candidates": [{"distance_m": 1, "verification": {"accepted": False}}],
        }], 25)
        self.assertIsNone(result["precision"])
        self.assertEqual(result["eligible_query_recall"], 0)


if __name__ == "__main__":
    unittest.main()
