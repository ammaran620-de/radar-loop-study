# Radar Loop Study

**Learned radar place recognition with independent geometric checks and inspectable failure cases.**

A focused research prototype for a radar-SLAM team: propose a revisited place, estimate a local query-to-reference transform, and expose the evidence for accepting or rejecting that proposal. It addresses the learned-feature and loop-closure stages of the published IST Radar-SLAM project. It is independent work, not a reproduction of the lab's private system.

The network is the **authors' frozen RadarLoc checkpoint**, not a newly trained model. The original work here is its Boreas integration, an independent registration gate, explicit abstention accounting, a label-free candidate interface, and an offline failure explorer. Prepared with AI assistance.

## What actually ran

160 real Boreas radar scans: 120 references from August 2021, 40 queries from September 2021. The same fixed sample is used for every comparison. At a 25 m supplied-position evaluation radius, 33 queries have a nearby reference.

| Stage | Observed result | Interpretation |
|---|---:|---|
| Ring-sector retrieval baseline | 19/33 top-1 hits | Hand-engineered comparison |
| Frozen RadarLoc retrieval | 21/33 top-1; 25/33 top-5 | Small descriptive improvement; no significance claim |
| First passing candidate among learned top three | 11 correct / 11 selected | 29/40 queries abstain |
| Accepted eligible-query recall | 11/33 | Precision comes with substantial missed revisits |
| Same fixed decisions evaluated at 10 m | 10 correct / 11 selected | One false acceptance; gates are imperfect |

An illustrative failure: query_423's top learned match scores approximately **0.939 cosine similarity but is 2.17 km away** by supplied positions. The geometric checks reject it. Similarity alone is not evidence of a valid loop closure.

These are exploratory subset results, not the official Boreas benchmark. A 25 m label is place proximity, not 25 m pose accuracy. No claim of 100% accuracy or production reliability is justified.

## Run it

Python 3.11 or 3.12 is recommended; the recorded run used Python 3.12 on CPU. In the extracted repository directory:

    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    python -m pip install -r requirements-study.txt
    python download_sample.py
    python experiment.py
    python loop_closure_study.py
    python -m unittest -v

On Windows, use `py` if that is your Python launcher. A compatible PyTorch wheel is required for your OS/Python combination. CPU execution is sufficient for this sample. The bundled pretrained checkpoint is 6.4 MB; scans total roughly 65 MB plus pose files. Downloads are public and retried, with SHA-256 provenance recorded. Install recorded wheel versions from requirements-study-tested.txt only if available for your platform; SciPy's recorded version is in VALIDATION.md.

Open **Radar_Loop_Study.html** in Chrome or Edge after generation. The separately distributed HTML is already generated and works offline without Python. Radar_Revisit_Lab.html retains the hand-engineered baseline explorer.

## Pipeline and interface

1. Strip the 11 radar metadata columns, transpose to range-by-angle, area-resize to 128 × 384, and apply the authors' normalization.
2. Extract and L2-normalize 256-dimensional frozen RadarLoc descriptors. Rank reference observations by cosine similarity.
3. For each top-three candidate, obtain a coarse angular initialization from a separate ring-sector descriptor.
4. Extract up to 400 strongest azimuth returns at 5–80 m. Run multiple-start trimmed 2D ICP.
5. Check symmetric overlap, inlier residual, angular support, and translation magnitude. Select the first passing candidate in learned rank order, or abstain.
6. Evaluate using supplied positions only after proposals are computed. Inspect scans, local alignment, candidates, and rejection reasons in the offline explorer.

`results/candidate_packets.jsonl` contains one packet per query: IDs, timestamp, provisional query-to-reference SE(2), and the top-three diagnostic records. It deliberately excludes supplied positions and ground-truth distance labels. Translation uses metres; yaw uses radians. Column-vector convention: `p_reference = R(yaw) @ p_query + t`. There is no calibrated covariance, temporal consistency, or graph insertion policy. A packet is a research integration boundary, not a ready-to-insert SLAM factor.

## Fixed checks, honest limits

The gate settings in geometric_verification.py are engineering starting points selected without label-based tuning: 4 m correspondence distance, 75% trimmed correspondences, at least 50% symmetric overlap, at most 1.5 m inlier RMSE, support in at least 6/12 angular sectors, and at most 40 m estimated translation. They are not probabilities or a safety guarantee. Repeated structures, dynamic returns, multipath, and poor initialization can defeat registration.

The learned preprocessing follows the authors' procedure, but full-range Boreas scans have a different sensor/range domain from the documented MulRan training. There is **no Boreas fine-tuning** here and no reproduction claim for the original paper. Frozen weights and vendor files are content-pinned; upstream MIT attribution is retained.

Reference and query dates are separate. Identical-content scans across splits are rejected. Exact S3 radar-pose timestamps and shared ENU_ref coordinates avoid estimated cross-run alignment. Ground truth does not rank candidates, initialize registration, or select the first passing candidate. Radii 5/10/25/50 m change evaluation labels only; the checks remain fixed.

This is **not a complete SLAM system**: no sequential odometry, temporal loop consistency, pose graph optimization, map reconstruction, or drift-reduction measurement. There is no Jetson/Raspberry Pi deployment claim. Small correlated samples cannot establish generalization. A new held-out route/session and a fixed validation/calibration protocol are needed before trusting gates.

## Reproducibility and review

- `learned_descriptor.py`: safe strict checkpoint loading, model preprocessing and inference.
- `geometric_verification.py`: points, registration, diagnostic gates.
- `loop_closure_study.py`: cross-run experiment, decisions, packet and HTML exports.
- `experiment.py`: hand-engineered comparison and shared evaluation.
- `data/manifest.json`: source URLs, scan hashes, exact pose coordinates and timestamps.
- `results/learned_metrics.json`: compact recorded results; candidate_packets.jsonl: label-free proposals.
- `third_party/radarloc/PROVENANCE.json`: upstream source and file checksums; LICENSE: upstream MIT terms.
- `EXPERIMENT_REPORT.md`, `docs/RED_TEAM_REVIEW.md`, `INTERVIEW_GUIDE.md`: findings, criticism, and explanation.
- `VALIDATION.md`: numerical/model/DOM checks and remaining visual review.

Optional DOM checks, after both HTML files have been generated:

    npm ci
    npm test

These exercise scripts and controls; they do not establish visual rendering quality.

Original integration code: MIT. Boreas data: CC BY 4.0, Keenan Burnett et al., IJRR 2023. RadarLoc: Komorowski, Wysoczanska and Trzcinski, 2021; upstream MIT licence. See SOURCES.md and DATA_LICENSE.md. Presenters should explain the implementation and acknowledge the pretrained network and AI assistance.
