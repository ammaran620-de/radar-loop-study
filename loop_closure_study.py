"""Learned radar retrieval and experimental geometric loop-candidate verification."""
import hashlib
import json
import time

import numpy as np

from experiment import ROOT, decode_scan, descriptor, similarity, score_results, image_uri, validate_frames
from learned_descriptor import extract_descriptors
from geometric_verification import CONFIG, scan_points, verify_pair


def candidate_packet(query):
    """Position-label-free proposal interface; not an optimized SLAM constraint."""
    selected = next((c for c in query["candidates"] if c["verification"]["accepted"]), None)
    return {
        "schema_version": 1,
        "query_id": query["id"],
        "query_timestamp_us": query["timestamp_us"],
        "decision": "provisional_candidate" if selected else "abstain",
        "reference_id": selected["reference_id"] if selected else None,
        "estimated_query_to_reference_se2": {
            "yaw_rad": selected["verification"]["yaw_rad"],
            "translation_xy_m": selected["verification"]["translation_xy_m"],
        } if selected else None,
        "evidence": [{"reference_id": c["reference_id"], "learned_cosine": c["score"],
                      "registration": c["verification"]} for c in query["candidates"]],
        "integration_warning": "Experimental gate; no calibrated covariance or temporal consistency check",
    }


def evaluate_decisions(queries, radius):
    available = sum(q["nearest_reference_distance_m"] <= radius for q in queries)
    accepted = []
    for query in queries:
        chosen = next((c for c in query["candidates"] if c["verification"]["accepted"]), None)
        if chosen is not None:
            accepted.append(chosen)
    correct = sum(c["distance_m"] <= radius for c in accepted)
    return {
        "accepted_queries": len(accepted),
        "correct_accepted": correct,
        "false_accepted": len(accepted) - correct,
        "precision": correct / len(accepted) if accepted else None,
        "eligible_query_recall": correct / available if available else None,
        "eligible_queries": available,
        "total_queries": len(queries),
        "policy": "First candidate passing experimental checks among top 3 learned retrievals",
    }


def main():
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    validate_frames(manifest["frames"])
    for frame in manifest["frames"]:
        actual = hashlib.sha256((ROOT / frame["path"]).read_bytes()).hexdigest()
        if actual != frame["sha256"]:
            raise ValueError("Input checksum mismatch: " + frame["id"])
    references = [f for f in manifest["frames"] if f["split"] == "reference"]
    queries = [f for f in manifest["frames"] if f["split"] == "query"]
    if {f["sequence"] for f in references} & {f["sequence"] for f in queries}:
        raise ValueError("Query and reference runs overlap")
    if {f["sha256"] for f in references} & {f["sha256"] for f in queries}:
        raise ValueError("Identical-content scans occur across splits")
    print("Extracting frozen learned radar descriptors", flush=True)
    learned, provenance = extract_descriptors(manifest["frames"])
    vectors = np.array([learned[f["id"]] for f in references])
    ref_xy = np.array([[f["x"], f["y"]] for f in references])
    query_xy = np.array([[f["x"], f["y"]] for f in queries])
    distances = np.linalg.norm(query_xy[:, None, :] - ref_xy[None, :, :], axis=2)
    rankings = []
    scores = []
    for query in queries:
        score = vectors @ learned[query["id"]]
        rankings.append(np.argsort(-score, kind="stable"))
        scores.append(score)
    print("Preparing point returns and sector initialization", flush=True)
    points, sectors, previews = {}, {}, {}
    for frame in manifest["frames"]:
        points[frame["id"]] = scan_points(ROOT / frame["path"])
        angle, power = decode_scan(ROOT / frame["path"])
        sectors[frame["id"]] = descriptor(angle, power)
        previews[frame["id"]] = image_uri(power[:, :1678])
    output_queries = []
    for i, query in enumerate(queries):
        candidates = []
        for j in rankings[i][:3]:
            reference = references[j]
            _, angular_shift = similarity(sectors[query["id"]], sectors[reference["id"]])
            start = time.perf_counter()
            verification = verify_pair(points[query["id"]], points[reference["id"]],
                                       angular_shift / 60 * 2 * np.pi)
            verification["elapsed_ms"] = (time.perf_counter() - start) * 1000
            candidates.append({
                "reference_id": reference["id"],
                "score": float(scores[i][j]),
                "distance_m": float(distances[i, j]),
                "verification": verification,
            })
        output_queries.append({
            **query,
            "nearest_reference_distance_m": float(distances[i].min()),
            "candidates": candidates,
        })
        if (i + 1) % 5 == 0:
            print(f"Verified top-three candidates for {i + 1}/{len(queries)} queries", flush=True)
    output = {
        "version": "3.0",
        "scope": "Frozen learned radar retrieval with experimental 2D geometric verification",
        "model": provenance,
        "verification_config": CONFIG,
        "reference_count": len(references),
        "query_count": len(queries),
        "reference_sequence": manifest["reference_sequence"],
        "query_sequence": manifest["query_sequence"],
        "retrieval": {str(r): score_results(rankings, distances, r) for r in [5, 10, 25, 50]},
        "decisions": {str(r): evaluate_decisions(output_queries, r) for r in [5, 10, 25, 50]},
        "references": references, "queries": output_queries,
        "images": previews,
        "points": {key: value.tolist() for key, value in points.items()},
        "sector_baseline": json.loads((ROOT / "results/metrics.json").read_text())["sensitivity"],
    }
    (ROOT / "results/learned_loop_study.json").write_text(json.dumps(output, indent=2, allow_nan=False))
    (ROOT / "results/candidate_packets.jsonl").write_text("".join(
        json.dumps(candidate_packet(q), allow_nan=False) + "\n" for q in output_queries
    ))
    compact = {k: v for k, v in output.items() if k not in ["images", "queries", "references", "points"]}
    (ROOT / "results/learned_metrics.json").write_text(json.dumps(compact, indent=2))
    print(json.dumps(compact, indent=2))
    template = (ROOT / "web/loop_study.html").read_text()
    (ROOT / "Radar_Loop_Study.html").write_text(
        template.replace("__STUDY_JSON__", json.dumps(output).replace("</", "<\\/"))
    )


if __name__ == "__main__":
    main()
