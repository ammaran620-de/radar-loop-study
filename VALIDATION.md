# Validation record — 12 November 2026

## Executed work

The complete reproduction workflow ran successfully from the existing cached public data. The additional original-v3 held-out comparator also ran successfully. Both historical explorers, the new measured report, real-radar trajectory, return maps and PLY export were generated.

- 26 Python tests passed, covering the previous data/metric contracts plus sensor rotation convention, planar projection, transform-error criteria, phase-correlation sign, known-motion ICP, missing-evidence rejection, graph consistency, map fusion and development-only calibration accounting.
- The frozen RadarLoc model strictly loads the hash-checked author checkpoint and returns a finite 256-dimensional descriptor. No training occurs.
- 120 development and 120 held-out candidate registrations evaluated with exact-time supplied relative poses. The original v3 geometry was also evaluated on identical held-out candidates.
- Development v4: 18 selected, all meeting the pose criteria. Held-out v4: 13 selected, all meeting the criteria; 27 abstentions. Held-out original v3: 12 selected, all meeting criteria. This one-query held-out gain is modest.
- A fixed 82-scan development segment supplied actual radar odometry and six loop proposals. Three passed checks. Linear and robust checked graphs converged; the unchecked robust comparison reached its 300-evaluation limit, which is displayed.
- Image-to-decision file replay measured preprocessing, file I/O, model inference and sequential verification with a warm reference database. No target-device or live acquisition claim follows.
- Scientific figures were rendered and visually inspected. Dashboard/report DOM tests exercise controls, static result tables, embedded chart and explicit limitation text. DOM tests do not establish all browser layouts.

## Reproduction

    python run_upgrade.py
    python -m unittest -v
    npm ci
    npm test

Install requirements-validation.txt and an appropriate CPU PyTorch wheel first. Public pose files are required for the exact-time fixture test; without data that test is skipped in a source-only checkout. The report requires matplotlib. Tests use synthetic data only for numerical implementation contracts; the reported trajectory is real radar registration, not noisy supplied poses.

## Open evidence boundaries

Relative-pose criteria are <=2 m translation and <=5 degrees planar rotation error, not calibrated safety requirements. Supplied poses are planar-projected and have their own uncertainty. No confidence guarantee follows from thirteen selected held-out examples. The short trajectory is development data and not an independent long-route benchmark.

The map is radar-return support, not probabilistic occupancy or independently validated map accuracy. Dynamic/multipath/motion-distortion handling, uncertainty calibration and long-route temporal checks are incomplete. The pretrained Boreas domain adaptation remains unvalidated beyond this small study. The lab's hardware/middleware and embedded execution are unknown. Publication novelty is not established.
