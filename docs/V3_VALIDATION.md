# Validation record — 11 November 2026

## Executed

- Python 3.12.14, NumPy 2.3.5, Pillow 13.0.0, PyTorch 2.15.0+cpu, OpenCV 5.0.0.93, SciPy 1.17.0.
- Frozen RadarLoc checkpoint strictly loaded; safe weights-only load; SHA-256 checked before loading; finite output shape 1 × 256 verified.
- Complete 160-scan learned study and 120 pairwise registration evaluations executed on CPU. Heavy output, compact metrics, candidate packets and offline HTML generated.
- 17 Python tests passed: decoding/data contract, supplied-pose timestamp match, coverage accounting, circular shift, known rigid transform, synthetic registration, abstention, selection without label-based cherry picking, packet exclusion of labels, and model smoke test.
- Both dashboards passed jsdom control/script tests. Learned dashboard tests cover candidate selection, query selection, point overlay generation, 11 accepted/29 abstained queries, empty false-filter at 25 m, one false acceptance at 10 m, sensitivity updates and export handler.
- Source ZIP packaging excludes data, caches, dependencies and generated heavy outputs; includes the author checkpoint/licence, source, compact metrics and instructions.

## What this does not validate

DOM tests do not render browser layout. Full browser visual verification was blocked in the environment, so a manual visual review remains necessary. This limitation is separate from successful numerical/script tests.

Synthetic registration confirms implementation conventions, not real-world radar registration correctness. Supplied-position proximity labels do not validate the estimated transform. No registration pose-error metric, temporal consistency, odometry trajectory, map, drift reduction, graph optimization, target-device profiling or independent held-out benchmark is claimed.

The small sample has one false acceptance under a 10 m label, despite none among eleven accepted at 25 m. Gate calibration, cross-route generalization and pretrained-domain mismatch remain open.

## Commands

    python -m unittest -v
    python experiment.py
    python loop_closure_study.py
    npm ci
    npm test

The manifest/pose-file regression requires downloaded pose files. Without raw data, the source-only suite reports that fixture check as skipped. The model smoke test requires the learned dependencies and bundled weights. Timing values vary between runs and exclude preprocessing/registration where specified.
