"""Fetch a fixed, uniformly spaced sample from two public Boreas runs."""
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen

import numpy as np

ROOT = Path(__file__).resolve().parent
SEQUENCES = {
    "reference": ("boreas-2021-08-05-13-34", 120),
    "query": ("boreas-2021-09-02-11-42", 40),
}


def download(url, path):
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urlopen(url, timeout=25) as response:
                data = response.read()
            temporary = path.with_suffix(path.suffix + ".partial")
            temporary.write_bytes(data)
            temporary.replace(path)
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def records(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def main():
    manifest = {"dataset": "Boreas", "license": "CC BY 4.0", "frames": [],
                "position_source": "Boreas S3 applanix/radar_poses.csv, shared ENU_ref coordinates at exact scan timestamps",
                "sampling": "Uniform row indices within each complete run; no selection by descriptor score or geographic match",
                "reference_sequence": SEQUENCES["reference"][0],
                "query_sequence": SEQUENCES["query"][0]}
    jobs = []
    for split, (sequence, count) in SEQUENCES.items():
        meta = ROOT / "data" / sequence
        raw_url = f"https://boreas.s3.amazonaws.com/{sequence}/applanix/radar_poses.csv"
        metadata_bytes = download(raw_url, meta / "sensor_poses.csv")
        sensor = records(meta / "sensor_poses.csv")
        for index in np.linspace(0, len(sensor) - 1, count, dtype=int):
            row = sensor[index]
            timestamp_us = int(row["GPSTime"])
            relative = f"data/{sequence}/radar/{timestamp_us}.png"
            url = f"https://boreas.s3.amazonaws.com/{sequence}/radar/{timestamp_us}.png"
            frame = {"id": f"{split}_{index}", "split": split, "sequence": sequence,
                     "timestamp_us": timestamp_us, "path": relative,
                     "x": float(row["easting"]), "y": float(row["northing"]),
                     "pose_time_offset_s": 0.0, "source_url": url,
                     "pose_source_url": raw_url,
                     "pose_file_sha256": hashlib.sha256(metadata_bytes).hexdigest()}
            jobs.append((frame, ROOT / relative))
    def get_frame(job):
        frame, path = job
        raw = download(frame["source_url"], path)
        frame["sha256"] = hashlib.sha256(raw).hexdigest()
        return frame
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, frame in enumerate(pool.map(get_frame, jobs), 1):
            manifest["frames"].append(frame)
            if index % 20 == 0:
                print(f"Downloaded {index}/{len(jobs)} scans", flush=True)
    # Sorting preserves chronological ordering within each split.
    manifest["frames"].sort(key=lambda r: (r["split"], r["timestamp_us"]))
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Saved {len(jobs)} real scans and their provenance", flush=True)


if __name__ == "__main__":
    main()
