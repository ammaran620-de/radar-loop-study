"""Exact-time Boreas pose references, kept outside the perception modules."""
import csv
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def pose_matrix(row):
    """Pinned pyboreas get_transform convention (passive roll @ pitch @ yaw)."""
    r,p,y = [float(row[k]) for k in ('roll','pitch','heading')]
    cr,sr,cp,sp,cy,sy = np.cos(r),np.sin(r),np.cos(p),np.sin(p),np.cos(y),np.sin(y)
    roll = np.array([[1,0,0],[0,cr,sr],[0,-sr,cr]])
    pitch = np.array([[cp,0,-sp],[0,1,0],[sp,0,cp]])
    yaw = np.array([[cy,sy,0],[-sy,cy,0],[0,0,1]])
    result=np.eye(4);result[:3,:3]=roll@pitch@yaw
    result[:3,3]=[float(row[k]) for k in ('easting','northing','altitude')]
    return result


def project_se2(transform):
    u,_,vt=np.linalg.svd(transform[:2,:2])
    rotation=u@vt
    if np.linalg.det(rotation)<0:
        u[:,-1]*=-1;rotation=u@vt
    result=np.eye(3);result[:2,:2]=rotation;result[:2,2]=transform[:2,3]
    return result


def read_poses(sequence):
    with (ROOT/'data'/sequence/'sensor_poses.csv').open() as stream:
        return {int(r['GPSTime']):pose_matrix(r) for r in csv.DictReader(stream)}


def relative_pose(query,reference,poses):
    world_query=poses[query['sequence']][query['timestamp_us']]
    world_reference=poses[reference['sequence']][reference['timestamp_us']]
    return project_se2(np.linalg.inv(world_reference)@world_query)


def estimated_pose(verification):
    a=verification['yaw_rad'];c,s=np.cos(a),np.sin(a)
    return np.array([[c,-s,verification['translation_xy_m'][0]],
                     [s,c,verification['translation_xy_m'][1]],[0,0,1]])


def transform_error(verification,truth):
    if 'yaw_rad' not in verification:return {'translation_error_m':None,'rotation_error_deg':None,'pose_correct':False}
    estimate=estimated_pose(verification)
    difference=np.linalg.inv(truth)@estimate
    angle=abs(np.arctan2(difference[1,0],difference[0,0]))*180/np.pi
    translation=float(np.linalg.norm(estimate[:2,2]-truth[:2,2]))
    return {'translation_error_m':translation,'rotation_error_deg':float(angle),
            'pose_correct':bool(translation<=2 and angle<=5)}
