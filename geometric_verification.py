"""Experimental 2D scan-registration checks, independent of reference positions."""
import numpy as np
from scipy.spatial import cKDTree

from experiment import decode_scan, RANGE_RESOLUTION_M, RANGE_OFFSET_M

CONFIG = {
    "range_m": [5, 80],
    "points": 400,
    "max_correspondence_m": 4.0,
    "trim_fraction": 0.75,
    "max_iterations": 20,
    "accept_overlap": 0.50,
    "accept_rmse_m": 1.5,
    "accept_sector_coverage": 6,
    "coverage_sectors": 12,
    "max_translation_m": 40.0,
}


def scan_points(path):
    angles, power = decode_scan(path)
    ranges = np.arange(power.shape[1]) * RANGE_RESOLUTION_M + RANGE_OFFSET_M
    keep = (ranges >= CONFIG["range_m"][0]) & (ranges <= CONFIG["range_m"][1])
    values = power[:, keep]
    # One strongest range return per azimuth. This limits clutter and preserves
    # angular coverage, but may select moving objects and multipath reflections.
    strongest = np.argmax(values, axis=1)
    strength = values[np.arange(len(angles)), strongest]
    mask = strength > np.median(values)
    r = ranges[keep][strongest][mask]
    theta = angles[mask]
    points = np.column_stack([r * np.cos(theta), r * np.sin(theta)])
    if len(points) > CONFIG["points"]:
        indexes = np.linspace(0, len(points) - 1, CONFIG["points"], dtype=int)
        points = points[indexes]
    return points


def rigid_fit(source, target):
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    u, _, vt = np.linalg.svd((source - source_center).T @ (target - target_center))
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1] *= -1
        rotation = vt.T @ u.T
    translation = target_center - rotation @ source_center
    return rotation, translation


def alignment_statistics(source, target, rotation, translation):
    aligned = source @ rotation.T + translation
    forward, _ = cKDTree(target).query(aligned)
    backward, _ = cKDTree(aligned).query(target)
    threshold = CONFIG["max_correspondence_m"]
    forward_mask = forward <= threshold
    backward_mask = backward <= threshold
    overlap = float(min(forward_mask.mean(), backward_mask.mean()))
    errors = np.concatenate([forward[forward_mask], backward[backward_mask]])
    rmse = float(np.sqrt(np.mean(errors ** 2))) if len(errors) else None
    # Require inlier source points to span several directions around the sensor.
    theta = np.arctan2(source[forward_mask, 1], source[forward_mask, 0])
    sectors = np.floor((theta % (2 * np.pi)) / (2 * np.pi) *
                       CONFIG["coverage_sectors"]).astype(int)
    return {"overlap": overlap, "rmse_m": rmse,
            "sector_coverage": int(len(np.unique(sectors)))}


def verify_pair(source, target, initial_yaw):
    if len(source) < 20 or len(target) < 20:
        return {"accepted": False, "reason": "insufficient_returns"}
    tree = cKDTree(target)
    candidates = []
    for offset in [-np.pi / 30, 0, np.pi / 30]:
        yaw = initial_yaw + offset
        rotation0 = np.array([[np.cos(yaw), -np.sin(yaw)],
                              [np.sin(yaw), np.cos(yaw)]])
        rotated = source @ rotation0.T
        starts = [
            np.zeros(2),
            np.median(target, axis=0) - np.median(rotated, axis=0),
            target.mean(axis=0) - rotated.mean(axis=0),
        ]
        for translation0 in starts:
            rotation = rotation0.copy()
            translation = translation0.copy()
            for _ in range(CONFIG["max_iterations"]):
                aligned = source @ rotation.T + translation
                distance, matches = tree.query(aligned)
                selected = np.flatnonzero(distance <= CONFIG["max_correspondence_m"])
                if len(selected) < 12:
                    break
                ordered = selected[np.argsort(distance[selected])]
                count = max(12, int(len(ordered) * CONFIG["trim_fraction"]))
                selected = ordered[:count]
                delta_r, delta_t = rigid_fit(aligned[selected], target[matches[selected]])
                rotation = delta_r @ rotation
                translation = delta_r @ translation + delta_t
                if np.linalg.norm(delta_t) < 1e-3 and abs(delta_r[1, 0]) < 1e-4:
                    break
            stats = alignment_statistics(source, target, rotation, translation)
            stats.update({
                "yaw_rad": float(np.arctan2(rotation[1, 0], rotation[0, 0])),
                "translation_xy_m": translation.tolist(),
            })
            candidates.append(stats)
    # Selection uses registration evidence, never reference positions.
    best = max(candidates, key=lambda c: (
        c["overlap"], -(c["rmse_m"] if c["rmse_m"] is not None else 1e6)
    ))
    reasons = []
    if best["overlap"] < CONFIG["accept_overlap"]:
        reasons.append("low_overlap")
    if best["rmse_m"] is None or best["rmse_m"] > CONFIG["accept_rmse_m"]:
        reasons.append("high_residual")
    if best["sector_coverage"] < CONFIG["accept_sector_coverage"]:
        reasons.append("limited_angular_support")
    if np.linalg.norm(best["translation_xy_m"]) > CONFIG["max_translation_m"]:
        reasons.append("large_translation")
    best["accepted"] = not reasons
    best["reason"] = ", ".join(reasons) if reasons else "passed_experimental_checks"
    return best
