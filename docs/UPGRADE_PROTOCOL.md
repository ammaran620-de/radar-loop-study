# Version 4 protocol, fixed before held-out processing

Development data: the existing 120 August references and 40 September-02 queries. These examples have already been inspected, so they are development data, not an unbiased test set.

Held-out data: boreas-2021-09-07-09-35, forty uniformly spaced radar-pose rows. Use the existing August reference database. Do not choose frames by matching performance. Freeze extraction, registration and gate selection on development outputs before running this session. This is another session on the same dataset/routes, not an unseen-city benchmark.

Primary registration labels: translation error <=2 m and planar rotation error <=5 degrees, comparing estimated query-to-reference transforms with exact-time supplied sensor poses. Nearby place labels at 5/10/25/50 m are retained separately. Pose-error thresholds are engineering evaluation criteria, not safety requirements supplied by the lab.

Ground-truth transforms are constructed using the pinned pyboreas rotation convention. Planar evaluation projects the relative sensor rotation onto SO(2); out-of-plane motion remains a limitation. Ground truth is evaluation-only. An explicitly labelled oracle-initialization ablation may use true transforms for diagnosis; it must never supply deployable outputs.

Compare frozen retrieval with old geometry and a coarse-to-fine geometry implementation. Calibrate overlap/residual gates only on development pairs, report retention and transform error, and apply the frozen choice to held-out pairs. Retain the old results and label them v3.

Trajectory demonstration: select a short returning segment in the development run using supplied positions only to define the benchmark window. Compute sequential radar motion exclusively from scans. Evaluate the integrated trajectory against supplied poses. Compare no-loop, unverified-loop and checked-loop pose graphs if the segment supplies non-adjacent loop candidates. Never manufacture odometry from noisy ground truth. If no useful loop or improvement is observed, report that outcome rather than choosing a successful segment after inspecting results.

No claim of lab sensor compatibility, target-device real-time operation, novel neural architecture, complete sensor calibration, or state-of-the-art performance is permitted.

Availability amendment before any held-out radar processing: September-08 and September-09 radar pose URLs returned HTTP 404; September-07 returned 200. The held-out session is therefore September-07, chosen for public ground-truth availability. No matching outcomes informed this substitution. The first qualifying returning segment is September-02 rows 141–222 inclusive: >=100 m travel, <=5 m endpoint separation, and 20–150 s duration. This window is fixed before odometry is computed.
