# Explain the upgraded study

## What to say in 45 seconds
“I focused on the connection between radar place recognition and useful loop constraints. I integrated the authors' frozen RadarLoc network, then evaluated estimated relative poses rather than relying only on distance-based place labels. A scan-only initialization change increased correct selected development queries from eleven to eighteen. With settings frozen, a separate session selected thirteen correct relative poses and abstained on twenty-seven queries. I also ran actual radar odometry and pose-graph optimization on a short returning segment; checked loops reduced position RMSE from about 1.02 to 0.59 metres. The segment is only twenty seconds, so I would not claim general SLAM reliability. The next step is a longer held-out trajectory and your sensor's data.”

## Your two-minute demonstration

Open Radar_Validation_Report.html. Explain the trajectory plot and its initial-pose anchor. Show the development and held-out selection table, including abstentions. Explain that the registration criteria are 2 m translation and 5° rotation error; these differ from the earlier place-distance label. Show unchecked and checked graph results, including the robust comparison and convergence status. Finish with the fused return map and the remaining uncertainty/sensor limitations.

## Questions to prepare for

**What is your contribution?** The integration, scan-only raster translation initialization, coarse-to-fine registration, controlled protocol, relative-pose validation, abstention analysis, real-radar trajectory experiment, measured replay boundary and failure explanations. These are a research prototype, not a claim to have invented ICP, phase correlation, pose graphs or RadarLoc.

**How do you know a transform is correct?** Compare query-to-reference estimated SE(2) with the planar projection of the relative exact-time supplied sensor poses. Report translation and rotation errors separately. A nearby reference alone does not establish correct registration.

**Why is the 11.24 m candidate not necessarily wrong?** It can still be accurately registered. Its estimated translation differs by about 0.14 m from the supplied relative transform. A 10 m place-recognition threshold is a different evaluation question.

**What changed registration?** Rasterize query/reference returns, use phase correlation to propose translation under coarse yaw hypotheses, run cheap coarse ICP, then refine the best two starts. All proposals use scans only. The original initialization and single-scale method missed alignments this method recovers.

**What is an oracle?** An ablation initialized with ground truth to diagnose whether failures are caused by initialization. It is forbidden as a deployment input. On 41 nearby development pairs, normal registration recovers 36 poses within criteria; the oracle recovers 41. Five initialization-limited pairs remain.

**How is the held-out set protected?** Freeze algorithm/gate on the old development session; verify the source hash before processing another session. Do not tune using held-out outcomes. Both sessions share a dataset/region, so this is not cross-city generalization.

**Where does odometry come from?** Consecutive real radar scans, registered with the preceding radar-only motion estimate as initialization. No ground-truth speed, heading or artificial perturbation supplies the trajectory.

**How does the graph work?** Each node is a planar pose. Odometry and candidate loop factors constrain relative poses. The first node fixes gauge freedom. Solve least squares; compare linear and soft-L1 loss with fixed engineering residual scales. Those scales are not calibrated covariance.

**Is that complete mapping?** It fuses observed returns into 0.5 m support cells and exports PLY. It does not estimate free-space occupancy, reliably remove dynamic clutter or independently measure map accuracy.

**Can it run on their Jetson?** Not yet established. The recorded CPU file replay includes query I/O and preprocessing with a warm reference database. Sensor capture, middleware and target-device measurements remain missing.

**Why should an existing team care?** A reproducible component experiment can expose errors at the retrieval-to-registration boundary and show their trajectory effects. Ask about their actual radar, baseline and evaluation before claiming this solves their bottleneck.

## Own the explanation

Read pose_evaluation.py, registration_v4.py, validation_study.py and trajectory_study.py. Be able to explain the query-to-reference transform convention, cosine similarity, ICP, graph anchoring, abstention and held-out settings. Credit the pretrained network and AI assistance. Connect your Magic QC experience to sensor calibration and validation using specific work you actually performed, without presenting it as prior radar-SLAM experience.
