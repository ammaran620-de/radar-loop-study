"""Coarse-to-fine registration with scan-only raster translation proposals."""
import cv2
import numpy as np
from scipy.spatial import cKDTree
from geometric_verification import rigid_fit,alignment_statistics

ALGORITHM={'name':'coarse_to_fine_phase_initialized_icp','raster_resolution_m':1.0,
           'raster_size':256,'coarse_points':160,'coarse_iterations':8,
           'refine_starts':2,'refine_iterations':25,'correspondence_m':4.0}


def rotation(yaw):
    c,s=np.cos(yaw),np.sin(yaw)
    return np.array([[c,-s],[s,c]])


def raster(points):
    size=ALGORITHM['raster_size'];resolution=ALGORITHM['raster_resolution_m']
    grid=np.zeros((size,size),np.float32)
    indexes=np.floor(points/resolution+size/2).astype(int)
    valid=((indexes>=0)&(indexes<size)).all(axis=1)
    np.add.at(grid,(indexes[valid,1],indexes[valid,0]),1)
    return cv2.GaussianBlur(grid,(5,5),0.8)


def phase_translation(source,target):
    shift,response=cv2.phaseCorrelate(raster(source),raster(target))
    return np.array(shift)*ALGORITHM['raster_resolution_m'],float(response)


def icp(source,target,initial_r,initial_t,iterations=25,threshold=4):
    tree=cKDTree(target);r=initial_r.copy();t=np.array(initial_t,dtype=float)
    for _ in range(iterations):
        aligned=source@r.T+t;distance,index=tree.query(aligned)
        keep=np.flatnonzero(distance<=threshold)
        if len(keep)<12:break
        keep=keep[np.argsort(distance[keep])[:max(12,int(len(keep)*.75))]]
        dr,dt=rigid_fit(aligned[keep],target[index[keep]])
        r=dr@r;t=dr@t+dt
        if np.linalg.norm(dt)<1e-3 and abs(np.arctan2(dr[1,0],dr[0,0]))<1e-4:break
    return r,t


def apply_gate(stats,gate):
    reasons=[]
    if stats.get('overlap',0)<gate['overlap']:reasons.append('low_overlap')
    if stats.get('rmse_m') is None or stats['rmse_m']>gate['rmse_m']:reasons.append('high_residual')
    if stats.get('sector_coverage',0)<6:reasons.append('limited_angular_support')
    if np.linalg.norm(stats.get('translation_xy_m',[1e6,1e6]))>40:reasons.append('large_translation')
    return {**stats,'accepted':not reasons,'reason':', '.join(reasons) if reasons else 'passed_frozen_gate'}


def verify_fast(source,target,initial_yaw):
    if len(source)<20 or len(target)<20:
        return {'overlap':0,'rmse_m':None,'sector_coverage':0,'reason':'insufficient_returns'}
    ss=source[np.linspace(0,len(source)-1,min(160,len(source)),dtype=int)]
    starts=[]
    for offset in [-np.pi/15,-np.pi/30,0,np.pi/30,np.pi/15]:
        r=rotation(initial_yaw+offset);rotated=source@r.T
        translation,response=phase_translation(rotated,target)
        # Phase proposal is evidence, not a calibrated confidence value.
        for t in [translation,np.median(target,axis=0)-np.median(rotated,axis=0)]:
            rr,tt=icp(ss,target,r,t,iterations=8)
            stats=alignment_statistics(ss,target,rr,tt)
            starts.append((stats,rr,tt,response))
    starts.sort(key=lambda x:(-x[0]['overlap'],x[0]['rmse_m'] if x[0]['rmse_m'] is not None else 1e6))
    refined=[]
    for _,r,t,response in starts[:2]:
        r,t=icp(source,target,r,t,iterations=25)
        stats=alignment_statistics(source,target,r,t)
        stats.update(yaw_rad=float(np.arctan2(r[1,0],r[0,0])),translation_xy_m=t.tolist(),phase_response=response)
        refined.append(stats)
    return max(refined,key=lambda s:(s['overlap'],-(s['rmse_m'] if s['rmse_m'] is not None else 1e6)))
