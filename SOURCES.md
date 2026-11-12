# Sources and provenance

Boreas data documentation was checked at pyboreas commit 8e100ff82ecd4992511da61b016398dbd230f205.

- Data format, range offset, shared ENU reference https://github.com/utiasASRL/pyboreas/blob/8e100ff82ecd4992511da61b016398dbd230f205/DATA_REFERENCE.md
- Dataset licence https://github.com/utiasASRL/pyboreas/blob/8e100ff82ecd4992511da61b016398dbd230f205/DATA_LICENSE.md
- Dataset https://www.boreas.utias.utoronto.ca/
- Dataset paper https://doi.org/10.1177/02783649231160195
- Public scans and sensor pose files https://boreas.s3.amazonaws.com/

The source data is mutable public storage. The packaged manifest contains file hashes and selected coordinates so changes can be detected and the exact sample can be audited. Existing cached scans are verified against that manifest during evaluation.

The baseline implements ring-sector means and does not reproduce the original Scan Context algorithm. Version 3 additionally integrates the authors' released RadarLoc pretrained model.

## Version 2 correction
Version 1 unnecessarily used older example UTM pose files and treated the S3 pose coordinates as run-local. Official documentation establishes that S3 sensor poses share ENU_ref across runs. Version 2 uses those exact per-frame poses, treats byte 10 as unused, and applies the documented range offset. Version 1 metrics are superseded.

## Learned descriptor and registration

- RadarLoc author code and pretrained weights: https://github.com/jac99/RadarLoc
- Author checkpoint: https://github.com/jac99/RadarLoc/blob/main/weights/radarloc.pth
- Author preprocessing: https://github.com/jac99/RadarLoc/blob/main/scripts/downsample_radar_scans.py
- Author normalization: https://github.com/jac99/RadarLoc/blob/main/datasets/augmentation.py
- Paper: J. Komorowski, M. Wysoczanska and T. Trzcinski, Large-Scale Topological Radar Localization Using Learned Descriptors, 2021. See the upstream README for paper and documented MulRan training split.

Only radar inference dependencies and weights are vendored. Upstream MIT LICENSE is retained. PROVENANCE.json pins every downloaded source file by content hash; it does not claim an immutable Git commit. The wrapper checks the checkpoint hash before safe weights-only loading.

The local geometric module implements multiple-start trimmed point-to-point ICP with SVD rigid fitting and engineering gates. It is not claimed as a new registration algorithm or a reproduction of a published full SLAM pipeline. The known risk of erroneous loop associations motivates checking geometry; the actual lab bottleneck is unknown.

## Version 4 references and provenance

Relative pose construction follows get_transform and yawPitchRollToRot in pyboreas/utils/utils.py at the same pinned commit, plus DATA_REFERENCE.md. The rotation convention is passive roll @ pitch @ yaw. Sensor world transforms are composed as inv(T_world_reference) @ T_world_query; the 2D rotation block is projected onto SO(2). This evaluation is planar, not a full 6-DoF claim.

Additional public data: boreas-2021-09-07-09-35 (forty uniform held-out scan rows); boreas-2021-09-02-11-42 rows 141–222 (contiguous short trajectory). Source URLs and SHA-256 values for scans and pose files are in data/manifest_v4.json.

Phase-correlation translation initialization and ICP/SVD registration are standard methods. The pose graph is implemented with scipy.optimize.least_squares, including a soft-L1 comparison. The implementation and integration are original experiment code; the underlying algorithms are not claimed as novel.

The supplied ground-truth-initialized oracle is a labelled development-only diagnostic. It does not enter normal inference, held-out predictions, odometry or graph-factor generation. Ground truth selects the predefined trajectory window and evaluates estimates.
