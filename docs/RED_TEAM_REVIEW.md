# Red-team review and resolution

## Verdict
Suitable for discussion of a radar place-recognition baseline and experimental practice. The artefact does not establish expertise in a complete deep-learning SLAM implementation.

## Corrected findings

1. Position source: replaced old example pose files with current S3 sensor poses in documented shared ENU_ref, at exact frame timestamps. Recomputed all results.
2. Radar range: included the documented -0.31 m offset.
3. Radar metadata: stopped treating Boreas byte 10 as a validity flag.
4. Radius: CLI accepts the supported presets, and the dashboard initializes and compares methods at the actual radius.
5. Metrics: show hits, eligible denominator, total-query success, and coverage together.
6. Input checks: reject duplicate IDs, nonfinite coordinates, split overlap, duplicate scan hashes, and corrupted scans.
7. UI: empty filters hide the detail panel. Representative failures are selected by explicit rules.
8. Provenance: retain source URLs, source pose hashes, scan hashes, and an immutable documentation commit.
9. Packaging: raw scans and generated image-heavy outputs are excluded from Git. Download/reproduction instructions are included.
10. Claims: descriptor similarity, retrieval proximity, and supplied positions are distinguished from calibrated confidence and estimated pose.

## Remaining limits
No deep network, odometry, geometric loop validation, pose graph, mapping, or embedded deployment. Small correlated sample and sparse references. The next useful comparison is a verified learned descriptor under the same fixed protocol.

Full browser visual rendering needs a manual check. DOM regression tests execute the dashboard controls but do not assess layout.

## Interview use
Present one successful case and one false candidate. Explain why candidate retrieval needs verification. Discuss what you personally reviewed and ran, including AI assistance. Treat the experiment as supporting evidence alongside your own previous work.

## Version 3 adversarial review: useful to an existing radar team?

**Objection: another generic place-recognition visualizer adds little.** Added an actual frozen learned radar network, an independently computed registration gate, explicit abstention policy, a provisional transform interface, and failure inspection. This is a focused module, not a claim to replace the team's stack.

**Objection: claiming “deep learning” without a working model.** The author's checkpoint is loaded strictly with weights_only=True, its SHA-256 is enforced, and a finite 256-dimensional output is tested. The published architecture and MIT licence are retained. There is no training or model-novelty claim.

**Objection: hidden ground-truth alignment makes geometry look good.** Initialization uses only radar descriptor shift. Registration uses scan returns. The synthetic transform test verifies sign/convention. Output selection takes the first passing candidate, not the closest labelled candidate. Exported packets exclude positional ground truth.

**Objection: 11/11 is marketing.** At 25 m it describes only eleven selected queries out of forty. Twenty-nine abstain. At 10 m, one selected match is false. Both the dashboard and report expose this. The study does not estimate deployment safety.

**Objection: thresholds were optimized on a tiny test set.** Fixed engineering settings were selected without label-based tuning and are kept constant across radius sensitivity. They are uncalibrated. Any subsequent tuning must use a separate validation set; this snapshot must not be reused as an unbiased test.

**Objection: registration is a false-confidence generator.** Nearest-return overlap, low residual and angular support can all pass in repeated structures. Strongest-return selection is not semantic static filtering. Multiple starts reduce some initialization failures but do not establish a unique, correct transform. Temporal consistency, robust graph policies and covariance remain missing.

**Objection: pretrained preprocessing is mismatched.** Correct: Boreas full-range resizing differs from the documented MulRan domain. This is an explicit adaptation experiment, not a faithful reproduction of the paper benchmark. Physical range resampling, rotation robustness, and held-out domain evaluation need controlled experiments.

**Objection: this is complete SLAM.** It is not. No sequential odometry, pose graph, mapping or measured drift reduction is implemented. A provisional candidate packet is not an approved graph edge.

**Objection: this is exactly the lab's need.** Published objectives support relevance; the team's actual code, radar, middleware, datasets, bottlenecks and acceptance criteria are unknown. The presenter must ask about them rather than assert a missing capability.

**Remaining review:** full browser visual rendering was unavailable in this environment. Both dashboards have passing DOM/script tests, which do not prove layout quality. Open the offline HTML manually before presenting. A source-only rerun is still dependent on public dataset downloads and compatible package wheels.

## Version 4 response to the comparison review

Closed with measured evidence: relative-transform evaluation; old place-label ambiguity; scan-only initialization ablation; development/held-out separation; measured query image-to-decision latency; consecutive real-radar odometry; short pose-graph comparison; voxelized return-map export; explicit author/model attribution.

The v3 “false accepted at 10 m” example is not a demonstrated registration failure. Its reference is 11.24 m away, but its relative translation error is approximately 0.14 m. Version 4 reports these as different questions.

Registration improves development query selection from 11 to 18 pose-correct selections. Frozen separate-session evaluation selects 13 pose-correct queries and abstains on 27. No held-out tuning is performed. These counts do not establish safety or cross-city/weather generalization.

The first qualifying returning development segment, selected before odometry, has 82 scans and about 122 m of travel. Its checked graph improves estimated trajectory error. It is only 20.25 seconds long; no long-route or held-out trajectory claim follows. Ground truth is not used to manufacture motion estimates.

The unchecked linear graph is a negative control. A robust soft-L1 comparison is supplied; its solver limit is visible in both report and figure. Do not claim superiority to a converged, carefully tuned state-of-the-art robust SLAM baseline on this evidence.

The map is observed radar-return fusion with estimated poses, not a calibrated occupancy grid or independently measured map-quality result. Fixed graph residual scales are not covariance. Time exclusion between loop candidates does not establish long-route temporal consistency.

Still open by design: unknown lab sensor/SDK/middleware, physical deployment, dynamic-return/multipath/motion-distortion robustness, longer independent routes, uncertainty calibration, original model training and publication novelty. These cannot be honestly closed by renaming features or adding screenshots.

A frozen original-v3 comparator on the same held-out candidate list selects 12 correct poses versus v4's 13. Report this modest one-query held-out improvement alongside the larger development gain. Omitting that comparison would overstate generalization.
