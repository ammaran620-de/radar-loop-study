# Sensor and team integration boundary

Validated input: Boreas Navtech CIR204-H polar PNGs from the listed 2021 sessions. Scan rows represent azimuths; the first 11 columns contain metadata; encoder scale is 5600 ticks/revolution. Range bins use 0.0596 m resolution and -0.31 m offset for these sessions. Exact sensor-pose timestamps are used only for evaluation.

The lab's sensor, SDK, acquisition mode and middleware are unknown. A rotating polar scanner is not interchangeable with an automotive radar detection list, range-Doppler cube, WiFi channel-state stream or arbitrary point cloud. This implementation does not pretend to support those formats.

Before connecting a real sensor, establish:

- Sensor model, firmware, packet or file schema, units and timestamps.
- Range resolution/offset, azimuth order/direction, scan timing and coordinate handedness.
- Extrinsic calibration, motion compensation and synchronization requirements.
- CPU/GPU, memory budget, required frame rate and middleware.
- Available ground truth, reference maps and the team's current error definitions.

Perception API: online_replay.predict accepts a label-free query dictionary containing id/path/timestamp, a prepared reference database, the frozen model and the gate. Outputs are provisional candidates with a query-to-reference planar transform and diagnostics. Supplied positions and orientation never enter this prediction API.

The full point-registration convention is p_reference = R(yaw) p_query + t, with metres and radians. A real adapter must implement decode_scan and range calibration faithfully, and must be checked against known rotations/translations before model-domain adaptation or registration performance is asserted.

Current map output is a voxelized radar-return map, not a probabilistic occupancy grid: it does not model free space, remove dynamic objects reliably, or establish map accuracy. The short pose graph uses fixed engineering residual scales, not calibrated covariance.
