# Experiment report — v4

The experimental question is whether scan-only verification of learned radar proposals can preserve usable constraints and improve a real estimated trajectory.

Development query selection: original v3 11/40 pose-correct selections; v4 18/40. Relative-pose criteria: <=2 m translation error and <=5 degrees rotation error. These are fixed evaluation choices.

Frozen held-out query selection: original v3 12/40 pose-correct selections; v4 13/40. The held-out improvement is one query, materially smaller than the development gain. Both methods have no observed wrong selected poses under these criteria, but most queries abstain. This does not establish safety or significance.

The held-out v4 selected-pose median translation error is 0.0707 m; median rotation error is 0.1587 degrees. These are conditional on selection, not overall localization accuracy.

On 41 development pairs whose supplied positions are within 25 m, v4 scan-only registration has 36 pose-correct results. An explicitly separated ground-truth-initialized diagnostic recovers 41. Five initialization-limited pairs remain. This oracle never creates perception outputs.

The real-radar motion experiment uses 82 consecutive scans over 20.25 s and about 122 m. Consecutive registration supplies motion estimates. Six learned temporally separated candidates are proposed; three pass fixed checks. The initial pose anchors all trajectories; no fitted global alignment is performed.

| Method | Position RMSE | Endpoint position error | Solver |
|---|---:|---:|---|
| Radar odometry | 1.0250 m | 2.1372 m | Not applicable |
| Unchecked linear graph | 42.5629 m | 5.4738 m | Converged |
| Checked linear graph | 0.5900 m | 0.1961 m | Converged |
| Unchecked robust graph | 19.3576 m | 0.9469 m | Evaluation limit reached |
| Checked robust graph | 0.5895 m | 0.1966 m | Converged |

The unchecked linear graph is a negative control. The unchecked robust graph reaches its solver limit and is not a converged benchmark. No state-of-the-art superiority claim follows. The supported trajectory result is the converged checked-graph versus odometry comparison on this short development segment.

The return map fuses estimated poses and radar observations into 0.5 m cells with repeated support, with a PLY export. It does not model free space or establish map accuracy. Dynamic clutter remains.

## Image-to-decision replay

development: median 175.7 ms; p95 207.1 ms.

heldout: median 178.0 ms; p95 190.7 ms.

These file-replay measurements include query image I/O, preprocessing, model inference, retrieval and sequential candidate checks. Reference preparation is outside the measured query path. Sensor acquisition, target hardware and middleware are unmeasured.

## Remaining limits

A single additional session on the same dataset/region is not cross-city or weather generalization. The trajectory is not held out and is too short for long-term drift conclusions. Graph uncertainty is not calibrated. Motion distortion, multipath and dynamic objects are not comprehensively handled. The lab's hardware and architecture remain unknown. The neural model is the author's frozen checkpoint with an adapted Boreas preprocessing domain, not original training or a validated new architecture.

See docs/UPGRADE_PROTOCOL.md for the fixed protocol and public-label availability amendment. See source and JSON for complete candidate errors and graph diagnostics.
