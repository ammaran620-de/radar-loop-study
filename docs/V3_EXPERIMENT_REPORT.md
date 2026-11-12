# Experiment report — Radar Loop Study v3

## Question
Can frozen learned radar descriptors propose cross-run revisits, while independent geometry exposes misleading matches? This corresponds to the public project's feature extraction, place recognition, and loop-closure components. The lab's actual stack and current bottleneck remain unknown.

## Method
The fixed sample contains 120 August references and 40 September queries from Boreas. Exact radar timestamps match S3 applanix/radar_poses.csv. Positions are shared ENU_ref, used only for evaluation. Every scan is hashed. Learned retrieval uses the released RadarLoc checkpoint with strict loading and no training. Its documented preprocessing is adapted to Boreas full range; domain shift is explicit.

Each query's top three learned candidates undergo strongest-return, multiple-start trimmed ICP. Coarse yaw comes from an independent ring-sector descriptor. Fixed gates require symmetric nearest-return overlap, residual, angular coverage and bounded translation. The first passing candidate is selected without looking at ground truth. The system abstains if all fail.

## Results
At 25 m, 33/40 queries have a nearby reference. Ring-sector top-1 retrieves 19/33; RadarLoc retrieves 21/33 and top-5 retrieves 25/33. All-query learned top-1 is 21/40. The two-hit difference is descriptive, not statistical evidence of a general improvement.

| Evaluation radius | Eligible queries | Learned top-1 | Correct selected / selected | Correct selected / eligible |
|---|---:|---:|---:|---:|
| 5 m | 11/40 | 11/11 | 10/11 | 10/11 |
| 10 m | 16/40 | 15/16 | 10/11 | 10/16 |
| 25 m | 33/40 | 21/33 | 11/11 | 11/33 |
| 50 m | 40/40 | 23/40 | 11/11 | 11/40 |

The same eleven decisions appear at every radius. Label sensitivity exposes an accepted candidate beyond 10 m. Twenty-nine queries abstain, including true revisits: the main cost of conservative checks. At 25 m, zero observed false acceptances among eleven selected is weak evidence; it is not a guarantee.

A high-similarity false match for query_423 is approximately 2165 m away at 0.939 cosine. Registration rejects it. Inspect its evidence in the explorer; this is a concrete failure-analysis example rather than an accuracy slogan.

## Runtime
Frozen model CPU forward median 16.15 ms and p95 32.86 ms across one 160-frame pass, two threads, portable kernels. These exclude file decoding, preprocessing, retrieval, and verification. Candidate-specific verification times are recorded in JSON; no end-to-end or embedded real-time claim is made.

## What a radar team can assess
They can inspect a useful boundary between learned proposals and provisional geometric evidence, compare the baseline, reproduce labels, and examine abstentions. JSONL packets expose estimated query-to-reference SE(2) without supplying ground truth. No calibrated covariance or temporal consistency is provided, so graph integration requires further engineering.

## Main weaknesses and next experiment
Sparse reference coverage, correlated routes, an adapted pretrained domain, strongest-return clutter, uncalibrated gates, and no temporal checks limit the conclusion. Freeze this snapshot, add a different held-out session, calibrate on separate validation data, and measure false positives versus revisit recall. Add sequential consistency and pose-graph optimization only after that, and report trajectory error with and without verified loops on an actual odometry chain. No drift reduction has yet been measured.
