# Radar Loop Study

**A reproducible radar-SLAM component study with relative-pose validation, a separate-session test, real radar odometry, loop-factor optimization and return-map fusion.**

The question: when learned radar descriptors propose revisits, can scan-only geometric checks retain useful constraints and prevent damaging ones? This is aligned with the public IST project's feature extraction, place recognition, localization, mapping and drift-reduction objectives. The lab's internal stack and hardware remain unknown.

The neural network is the **authors' frozen RadarLoc checkpoint**. It is not a new network trained here. The original work here is the integration, the registration and validation code, and the experiments. Model and data credits are in `SOURCES.md`.

## Measured results

| Experiment | Result | Important denominator/boundary |
|---|---|---|
| Original development gate | 11 selected queries with correct poses | 40 queries |
| New initialization + coarse-to-fine registration | 18 selected queries with correct poses | Same 40 development queries; gate tuned here |
| Separate September-07 session | Original gate: 12 correct selections; v4: 13/13 | 27/40 queries abstain; no held-out tuning |
| Short real-radar trajectory | Position RMSE 1.025 m → 0.590 m after checked loops | 82 consecutive scans; 20.25 s; approximately 122 m |
| Endpoint position error | 2.137 m → 0.196 m | Same short development segment, first pose anchored |

Pose criteria are <=2 m translation error and <=5° planar rotation error relative to exact-time supplied sensor poses. They are evaluation choices, not lab-provided safety requirements. Small correlated samples do not establish production reliability or broad generalization.

**Open Radar_Validation_Report.html for the current results.** Radar_Loop_Study.html and Radar_Revisit_Lab.html retain the historical v3 retrieval explorers. Their distance labels are not the new relative-pose validation.

## Reproduce

Use Python 3.11/3.12 with a compatible PyTorch wheel. The recorded run uses Python 3.12 on CPU.

    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    python -m pip install -r requirements-validation.txt
    python run_upgrade.py
    python -m unittest -v

On Windows, use py if appropriate. Public downloads are reused when cached. There are 282 frame entries (one scan is reused) across the three sessions and the short trajectory segment, plus pose files; allow roughly 150 MB of scan/metadata downloads and additional installed dependency space. The author checkpoint is downloaded on first use and checked against its pinned SHA-256. No GPU is required for this small study.

The pipeline generates all JSON, the scientific figure, the offline report, historical explorers and a PLY radar-return map. For source-only users, the data-dependent pose regression is skipped until data is downloaded.

## What changed in v4

- Exact relative-pose errors using the pinned pyboreas passive roll/pitch/yaw convention and planar projection.
- Radar-only raster phase-correlation translation proposals, coarse ICP and full-resolution refinement; coarse angular initialization still comes from an independent ring-sector descriptor.
- Development-only overlap/residual gate selection, followed by a frozen separate-session evaluation. The registration source hash and development manifest hash are recorded.
- An explicitly labelled ground-truth-initialized oracle ablation for diagnosis, excluded from perception and exported decisions.
- Consecutive-scan radar odometry on a fixed 82-frame returning segment. The trajectory is never created from noisy ground truth.
- Linear and robust soft-L1 pose-graph comparisons with unchecked and checked loop factors; convergence status is retained.
- Voxelized radar-return map and PLY export using estimated checked-graph poses.
- Warm-reference image-to-decision replay timing, including query file I/O and preprocessing; label-free prediction boundary in online_replay.predict.

## Protocol, not a performance slogan

Development: 120 August reference scans and 40 September-02 queries. The new gate was chosen on these inspected examples. Held-out: forty uniformly sampled September-07 queries against the same August database. Gate settings were frozen before held-out radar processing; September-07 was selected for public pose-label availability after the initially planned session returned 404.

The trajectory window is September-02 rows 141–222, the first segment satisfying the predeclared return/travel/time rule. Supplied positions define the window and evaluate results only. Radar estimates, loop proposals and graph factors do not use those positions. This is a short development example, not an independent long-route benchmark.

The frozen gate uses >=0.70 overlap, <=1.5 m inlier residual, >=6/12 angular sectors and <=40 m estimated translation. It is an empirical engineering gate, not calibrated probability. Ground truth is absent from the measured online perception API. The diagnostic oracle is clearly separated and cannot create deployment proposals.

## Scope and remaining work

Implemented: small-scale learned place recognition, pairwise geometric checks, relative-pose evaluation, sequential radar odometry, a short planar pose graph and radar-return fusion. This is a runnable research prototype, not a production autonomous navigation system.

Still unverified or limited:

- The lab's radar, coordinate conventions, middleware and hardware; see docs/SENSOR_INTEGRATION.md.
- Long-route drift, held-out trajectory optimization, new cities, adverse-weather robustness and long-running temporal consistency.
- Dynamic-object rejection, motion distortion, multipath mitigation and robust occupancy/free-space modelling.
- Covariance calibration and principled uncertainty weighting; graph scales are fixed engineering choices.
- Embedded latency/power/memory and live sensor acquisition. File-replay timing is not a target-device guarantee.
- Pretrained domain mismatch: full-range Boreas resizing is an adaptation of author preprocessing, with no fine-tuning here.

Unchecked graphs are negative controls, not state-of-the-art baselines. The robust comparator and any solver limit are shown. There is no comparison against the lab's private implementation.

## Key files

- pose_evaluation.py — exact supplied-pose convention and relative-transform errors.
- registration_v4.py — scan-only initialization and coarse-to-fine registration.
- validation_study.py — development calibration and frozen held-out evaluation.
- diagnose_rejections.py — development-only oracle analysis.
- trajectory_study.py — real odometry and pose-graph experiments.
- build_radar_map.py — radar-return fusion and PLY export.
- online_replay.py — image-to-decision timing and label-free inference interface.
- docs/UPGRADE_PROTOCOL.md — protocol and availability amendment.
- results/frozen_gate.json, *_v4.json — settings and inspectable recorded results.
- build_validation_report.py — scientific figure and self-contained HTML report.

For historical dashboard DOM tests: npm ci, then npm test after generating all HTML files. A report DOM test is included. Scientific figures were rendered and inspected; DOM tests do not establish every browser layout.

## Attribution

Boreas: University of Toronto ASRL, CC BY 4.0. RadarLoc: Komorowski, Wysoczanska and Trzcinski (2021), author code/weights with MIT licence retained under third_party/radarloc. Original integration: MIT. See SOURCES.md, DATA_LICENSE.md and third_party/radarloc/PROVENANCE.json. Independent of IST. No publication or GitHub push occurs merely by generating this package.

## Browser deployment

The `site/` folder contains the inspection interface. Run `python run_upgrade.py` and `python build_field_console.py` to generate its recorded data file. Serve that folder with any static host. It displays final offline estimates and the full-segment map, not a causal online SLAM replay. Radar previews retain their full 2:1 aspect ratio.

The Pages workflow rebuilds the public-data experiment and uploads the generated site. GitHub Pages must be enabled for this repository with GitHub Actions as its source. Source publication and successful deployment are separate states; check Actions before assuming the site is live.
