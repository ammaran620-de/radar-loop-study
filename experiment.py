"""Radar descriptor retrieval. Positions are evaluation labels, never model inputs."""
import argparse
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
RANGE_RESOLUTION_M = 0.0596
RANGE_OFFSET_M = -0.31
MIN_RANGE_M = 2.5
MAX_RANGE_M = 100.0
RINGS = 32
SECTORS = 60


def validate_frames(frames):
    ids = [frame["id"] for frame in frames]
    if len(set(ids)) != len(ids):
        raise ValueError("Frame IDs must be unique")
    coordinates = np.array([[frame["x"], frame["y"]] for frame in frames])
    if not np.isfinite(coordinates).all():
        raise ValueError("Reference coordinates must be finite")


def decode_scan(path):
    """Boreas PNG: 8 timestamp bytes, 2 encoder bytes, 1 unused byte."""
    with Image.open(path) as image:
        if image.mode != "L":
            raise ValueError(f"Expected an 8-bit grayscale radar PNG: {path}")
        raw = np.array(image)
    if raw.ndim != 2 or raw.shape[1] <= 11:
        raise ValueError("Radar image is missing metadata or range measurements")
    angles = raw[:, 8:10].copy().view("<u2").ravel() / 5600 * 2 * np.pi
    power = raw[:, 11:].astype(np.float32) / 255.0
    if raw.shape[0] == 0:
        raise ValueError("Radar scan has no azimuth readings")
    return angles, power


def descriptor(angles, power):
    """Hand-engineered ring-sector means with a constant background removed."""
    ranges = np.arange(power.shape[1]) * RANGE_RESOLUTION_M + RANGE_OFFSET_M
    keep = (ranges >= MIN_RANGE_M) & (ranges < MAX_RANGE_M)
    values = power[:, keep]
    values = np.maximum(values - np.median(values), 0)
    ring_ids = np.floor((ranges[keep] - MIN_RANGE_M) /
                        (MAX_RANGE_M - MIN_RANGE_M) * RINGS).astype(int)
    sector_ids = np.floor((angles % (2 * np.pi)) / (2 * np.pi) * SECTORS).astype(int)
    bins = sector_ids[:, None] * RINGS + ring_ids[None, :]
    sums = np.bincount(bins.ravel(), weights=values.ravel(), minlength=RINGS * SECTORS)
    counts = np.bincount(bins.ravel(), minlength=RINGS * SECTORS)
    result = (sums / np.maximum(counts, 1)).reshape(SECTORS, RINGS)
    norm = np.linalg.norm(result)
    if norm < 1e-9:
        raise ValueError("Radar descriptor has no usable signal")
    return (result / norm).astype(np.float32)


def similarity(query, reference):
    """Maximum cosine over all circular azimuth shifts, computed by FFT."""
    correlation = np.fft.ifft(
        np.fft.fft(query, axis=0).conj() *
        np.fft.fft(reference, axis=0), axis=0
    ).real.sum(axis=1)
    shift = int(np.argmax(correlation))
    return float(np.clip(correlation[shift], -1, 1)), shift


def rank_references(query, reference_descriptors):
    scores = [similarity(query, reference) for reference in reference_descriptors]
    order = np.argsort([-score[0] for score in scores], kind="stable")
    return order, scores


def score_results(rankings, distances, radius):
    """Recall denominator contains only queries with an available true match."""
    eligible = (distances <= radius).any(axis=1)
    best_errors = np.array([distances[i, order[0]] for i, order in enumerate(rankings)])
    hits1 = int(((best_errors <= radius) & eligible).sum())
    hits5 = sum(bool((distances[i, order[:5]] <= radius).any())
                for i, order in enumerate(rankings) if eligible[i])
    denominator = int(eligible.sum())
    return {
        "eligible_queries": denominator, "queries": len(rankings),
        "coverage": denominator / len(rankings),
        "recall_at_1": hits1 / denominator if denominator else None,
        "recall_at_5": hits5 / denominator if denominator else None,
        "hits_at_1": hits1, "hits_at_5": hits5,
        "top1_within_radius_all_queries": int((best_errors <= radius).sum()) / len(rankings),
        "median_top1_position_error_m": float(np.median(best_errors)),
        "no_positive_queries": int((~eligible).sum()),
    }


def image_uri(array, color=True):
    a = np.asarray(array, dtype=float)
    a = np.clip(a / max(float(np.percentile(a, 99.5)), 1e-9), 0, 1)
    if color:
        # Warm amber on charcoal, identical scale within each displayed image.
        rgb = np.stack([18 + 230*a, 24 + 150*a, 32 + 35*a], axis=-1).astype("uint8")
        image = Image.fromarray(rgb)
    else:
        image = Image.fromarray((a * 255).astype("uint8"))
    image = image.resize((480, 240))
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    parser.add_argument("--radius", type=int, choices=[5, 10, 25, 50], default=25)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    frames = manifest["frames"]
    validate_frames(frames)
    references = [f for f in frames if f["split"] == "reference"]
    queries = [f for f in frames if f["split"] == "query"]
    if not references or not queries:
        raise ValueError("Both reference and query splits are required")
    if {f["sequence"] for f in references} & {f["sequence"] for f in queries}:
        raise ValueError("This experiment requires separate runs for query and reference")
    if {f["sha256"] for f in references} & {f["sha256"] for f in queries}:
        raise ValueError("Identical scan content occurs in both splits")
    descriptors, previews = {}, {}
    preprocessing_start = time.perf_counter()
    for frame in frames:
        actual_hash = hashlib.sha256((ROOT / frame["path"]).read_bytes()).hexdigest()
        if actual_hash != frame["sha256"]:
            raise ValueError(f"Radar file checksum mismatch: {frame['id']}")
        angles, power = decode_scan(ROOT / frame["path"])
        descriptors[frame["id"]] = descriptor(angles, power)
        cropped = power[:, :int(MAX_RANGE_M / RANGE_RESOLUTION_M)]
        previews[frame["id"]] = image_uri(cropped)
    preprocessing_ms = (time.perf_counter() - preprocessing_start) * 1000 / len(frames)
    ref_desc = [descriptors[f["id"]] for f in references]
    rankings, all_scores, times = [], [], []
    ring_rankings = []
    ref_rings = np.array([d.mean(axis=0) for d in ref_desc])
    ref_rings /= np.maximum(np.linalg.norm(ref_rings, axis=1, keepdims=True), 1e-9)
    for query in queries:
        start = time.perf_counter()
        order, scores = rank_references(descriptors[query["id"]], ref_desc)
        times.append((time.perf_counter() - start) * 1000)
        rankings.append(order)
        all_scores.append(scores)
        query_ring = descriptors[query["id"]].mean(axis=0)
        query_ring /= max(np.linalg.norm(query_ring), 1e-9)
        ring_rankings.append(np.argsort(-(ref_rings @ query_ring), kind="stable"))
    # Coordinates only enter after ranking has completed.
    ref_xy = np.array([[f["x"], f["y"]] for f in references])
    query_xy = np.array([[f["x"], f["y"]] for f in queries])
    distances = np.linalg.norm(query_xy[:, None, :] - ref_xy[None, :, :], axis=2)
    result = {
        "title": "Radar Revisit Lab", "dataset": manifest["dataset"],
        "method": "Ring-sector mean descriptor with circular-shift cosine similarity",
        "learned_model": False, "radius_m": args.radius,
        "reference_sequence": manifest["reference_sequence"],
        "query_sequence": manifest["query_sequence"],
        "reference_count": len(references), "query_count": len(queries),
        "sampling": manifest["sampling"],
        "mean_retrieval_ms": float(np.mean(times)),
        "median_retrieval_ms": float(np.median(times)),
        "p95_retrieval_ms": float(np.percentile(times, 95)),
        "mean_decode_descriptor_preview_ms": preprocessing_ms,
        "position_source": manifest["position_source"],
        "max_pose_offset_s": max(f["pose_time_offset_s"] for f in frames),
        "radar_range_resolution_m": RANGE_RESOLUTION_M,
        "radar_range_offset_m": RANGE_OFFSET_M,
        "version": "2.0",
        "coordinate_frame": "Shared Boreas ENU_ref; supplied reference positions",
        "metrics": score_results(rankings, distances, args.radius),
        "ring_mean_baseline": score_results(ring_rankings, distances, args.radius),
        "ring_sensitivity": {str(r): score_results(ring_rankings, distances, r)
                             for r in [5, 10, 25, 50]},
        "sensitivity": {str(r): score_results(rankings, distances, r)
                        for r in [5, 10, 25, 50]},
        "references": references, "queries": [],
    }
    for i, query in enumerate(queries):
        candidates = []
        for j in rankings[i][:5]:
            score, shift = all_scores[i][j]
            candidates.append({
                "reference_id": references[j]["id"], "score": score,
                "sector_shift": shift, "distance_m": float(distances[i, j]),
                "preview": previews[references[j]["id"]],
            })
        result["queries"].append({
            **query, "preview": previews[query["id"]],
            "descriptor_preview": image_uri(descriptors[query["id"]].T),
            "eligible": bool((distances[i] <= args.radius).any()),
            "nearest_reference_distance_m": float(distances[i].min()),
            "retrieval_ms": times[i], "candidates": candidates,
        })
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    serialized = json.dumps(result, indent=2, allow_nan=False)
    (output / "results.json").write_text(serialized)
    template = (ROOT / "web/template.html").read_text()
    (ROOT / "Radar_Revisit_Lab.html").write_text(
        template.replace("__RESULTS_JSON__", serialized.replace("</", "<\\/"))
    )
    summary = {key: value for key, value in result.items()
               if key not in ["queries", "references"]}
    (output / "metrics.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
