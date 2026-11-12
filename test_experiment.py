"""Focused checks for descriptor alignment and evaluation denominators."""
import unittest

import numpy as np
from PIL import Image
from tempfile import TemporaryDirectory
from pathlib import Path

from experiment import decode_scan, descriptor, similarity, score_results, validate_frames, ROOT


class ExperimentTests(unittest.TestCase):
    def test_similarity_recovers_circular_shift(self):
        rng = np.random.default_rng(4)
        a = rng.random((60, 32))
        a /= np.linalg.norm(a)
        b = np.roll(a, 17, axis=0)
        score, shift = similarity(a, b)
        self.assertAlmostEqual(score, 1.0, places=6)
        self.assertEqual(shift, 17)

    def test_recall_excludes_uncovered_queries_but_reports_coverage(self):
        rankings = [np.array([1, 0]), np.array([0, 1])]
        distances = np.array([[2.0, 50.0], [100.0, 150.0]])
        result = score_results(rankings, distances, 5)
        self.assertEqual(result["eligible_queries"], 1)
        self.assertEqual(result["no_positive_queries"], 1)
        self.assertEqual(result["recall_at_1"], 0)
        self.assertEqual(result["recall_at_5"], 1)
        self.assertEqual(result["coverage"], 0.5)

    def test_no_eligible_query_has_no_recall(self):
        result = score_results([np.array([0])], np.array([[90.0]]), 5)
        self.assertIsNone(result["recall_at_1"])
        self.assertIsNone(result["recall_at_5"])

    def test_radar_header_is_not_used_as_signal(self):
        with TemporaryDirectory() as directory:
            raw = np.zeros((2, 31), dtype=np.uint8)
            raw[:, 10] = 255
            raw[0, 8:10] = np.array([1400], dtype="<u2").view("uint8")
            raw[:, 11:] = 128
            path = Path(directory) / "scan.png"
            Image.fromarray(raw).save(path)
            angles, values = decode_scan(path)
            self.assertEqual(values.shape, (2, 20))
            self.assertAlmostEqual(float(angles[0]), np.pi / 2)
            self.assertTrue(np.allclose(values, 128 / 255))

    def test_unused_boreas_byte_does_not_remove_rows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.png"
            Image.fromarray(np.zeros((4, 30), dtype=np.uint8)).save(path)
            angles, power = decode_scan(path)
            self.assertEqual(len(angles), 4)
            self.assertEqual(power.shape, (4, 19))


    def test_range_offset_excludes_near_field_bins(self):
        angles = np.linspace(0, 2 * np.pi, 60, endpoint=False)
        power = np.zeros((60, 1800), dtype=np.float32)
        power[:, 100] = 0.5
        baseline = descriptor(angles, power)
        power[:, 44] = 1.0
        # Bin 44 is 2.3124 m after the documented -0.31 m offset.
        np.testing.assert_allclose(descriptor(angles, power), baseline)

    def test_duplicate_ids_are_rejected(self):
        frames = [{"id": "same", "x": 0, "y": 0}] * 2
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_frames(frames)

    def test_nonfinite_coordinates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_frames([{"id": "q", "x": float("nan"), "y": 0}])

    @unittest.skipUnless(
        (ROOT / "data/boreas-2021-08-05-13-34/sensor_poses.csv").exists(),
        "Run download_sample.py to enable the real-data pose integration check",
    )
    def test_manifest_uses_exact_current_sensor_poses(self):
        import csv
        import json
        from experiment import ROOT
        manifest = json.loads((ROOT / "data/manifest.json").read_text())
        for sequence in {f["sequence"] for f in manifest["frames"]}:
            with (ROOT / "data" / sequence / "sensor_poses.csv").open() as source:
                rows = {int(row["GPSTime"]): row for row in csv.DictReader(source)}
            for frame in manifest["frames"]:
                if frame["sequence"] != sequence:
                    continue
                row = rows[frame["timestamp_us"]]
                self.assertEqual(frame["x"], float(row["easting"]))
                self.assertEqual(frame["y"], float(row["northing"]))
                self.assertEqual(frame["pose_time_offset_s"], 0)


if __name__ == "__main__":
    unittest.main()
