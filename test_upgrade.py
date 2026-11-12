"""Numerical conventions and graph/gate contracts for the v4 study."""
import unittest
import numpy as np
from pose_evaluation import pose_matrix,project_se2,transform_error
from registration_v4 import rotation,phase_translation,icp,apply_gate
from trajectory_study import optimize,se2,metrics
from validation_study import calibrate
from build_radar_map import fuse_returns


class UpgradeTests(unittest.TestCase):
    def test_pyboreas_passive_yaw_convention(self):
        row={'roll':0,'pitch':0,'heading':np.pi/2,'easting':2,'northing':3,'altitude':1}
        pose=pose_matrix(row)
        np.testing.assert_allclose(pose[:3,:3],[[0,1,0],[-1,0,0],[0,0,1]],atol=1e-12)
        np.testing.assert_allclose(pose[:3,3],[2,3,1])

    def test_relative_projection_handles_upside_down_sensor(self):
        row={'roll':np.pi,'pitch':0,'heading':0,'easting':0,'northing':0,'altitude':0}
        a=pose_matrix(row);row.update(easting=2,northing=3);b=pose_matrix(row)
        relative=project_se2(np.linalg.inv(a)@b)
        np.testing.assert_allclose(relative[:2,2],[2,-3],atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(relative[:2,:2]),1)

    def test_relative_error_distinguishes_proximity_from_registration(self):
        truth=se2([11.24,0,.1])
        correct=transform_error({'yaw_rad':.1,'translation_xy_m':[11.24,0]},truth)
        self.assertTrue(correct['pose_correct'])
        wrong=transform_error({'yaw_rad':.1,'translation_xy_m':[0,0]},truth)
        self.assertFalse(wrong['pose_correct'])

    def test_raster_phase_translation_sign(self):
        points=np.random.default_rng(5).uniform(-30,30,(300,2))
        estimated,_=phase_translation(points,points+[7,-4])
        np.testing.assert_allclose(estimated,[7,-4],atol=.1)

    def test_icp_recovers_small_known_motion(self):
        points=np.random.default_rng(10).normal(size=(200,2))*20
        target=points@rotation(.02).T+[.2,-.3]
        r,t=icp(points,target,np.eye(2),np.zeros(2))
        np.testing.assert_allclose(r,rotation(.02),atol=1e-5)
        np.testing.assert_allclose(t,[.2,-.3],atol=1e-5)

    def test_missing_geometric_evidence_is_rejected(self):
        self.assertFalse(apply_gate({}, {'overlap':.7,'rmse_m':1.5})['accepted'])

    def test_graph_consistent_edges_preserve_trajectory(self):
        truth=[se2([i,0,0]) for i in range(5)]
        edges=[(i,i+1,se2([1,0,0]),'odometry') for i in range(4)]
        edges.append((0,4,se2([4,0,0]),'loop'))
        output,status=optimize(truth,edges)
        self.assertTrue(status['success'])
        self.assertLess(metrics(output,truth)['position_rmse_m'],1e-8)

    def test_return_map_uses_estimated_transforms(self):
        cloud=np.array([[0.,0.],[1.,0.]])
        fused=fuse_returns([cloud,cloud],[se2([2,3,0]),se2([2,3,0])],resolution=1)
        self.assertEqual(fused['input_returns'],4)
        self.assertEqual(fused['cells'],[[2.5,3.5,2],[3.5,3.5,2]])

    def test_calibration_uses_pose_errors_and_rejects_bad_permissive_gate(self):
        records=[]
        for i,(overlap,correct) in enumerate([(.8,True),(.45,False)]):
            records.append({'query_id':str(i),'verification':{'overlap':overlap,'rmse_m':1.2,
                'sector_coverage':12,'translation_xy_m':[1,1]},'pose_error':{'pose_correct':correct,
                'translation_error_m':.1 if correct else 10,'rotation_error_deg':.2}})
        gate,_=calibrate(records)
        self.assertGreater(gate['overlap'],.45)

if __name__=='__main__':unittest.main()
