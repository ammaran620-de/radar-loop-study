"""Short, real-radar odometry and loop-factor experiment; no noisy-GT odometry."""
import json,time
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from experiment import ROOT,decode_scan,descriptor,similarity
from geometric_verification import scan_points
from registration_v4 import icp,rotation,verify_fast,apply_gate
from pose_evaluation import read_poses,project_se2,estimated_pose,transform_error
from learned_descriptor import extract_descriptors


def se2(x):
    out=np.eye(3);out[:2,:2]=rotation(x[2]);out[:2,2]=x[:2];return out


def state(t):return np.array([t[0,2],t[1,2],np.arctan2(t[1,0],t[0,0])])


def wrap(x):return np.arctan2(np.sin(x),np.cos(x))


def optimize(initial,edges,loss='linear'):
    n=len(initial)
    def residual(parameters):
        states=np.vstack([np.zeros(3),parameters.reshape(-1,3)]);result=[]
        for i,j,z,kind in edges:
            predicted=np.linalg.inv(se2(states[i]))@se2(states[j])
            error=state(np.linalg.inv(z)@predicted)
            # Fixed engineering scales, not calibrated covariance.
            error[2]=wrap(error[2]);result.extend(error/np.array([.3,.3,.03]))
        return np.array(result)
    sparsity=lil_matrix((len(edges)*3,(n-1)*3),dtype=int)
    for k,(i,j,_,_) in enumerate(edges):
        for node in (i,j):
            if node>0:sparsity[k*3:k*3+3,(node-1)*3:node*3]=1
    fit=least_squares(residual,np.array([state(t) for t in initial])[1:].ravel(),
        jac_sparsity=sparsity.tocsr(),max_nfev=300,loss=loss,ftol=1e-6)
    return [np.eye(3)]+[se2(x) for x in fit.x.reshape(-1,3)],{'success':bool(fit.success),'nfev':fit.nfev,'cost':float(fit.cost)}


def metrics(trajectory,truth):
    errors=np.array([np.linalg.norm(a[:2,2]-b[:2,2]) for a,b in zip(trajectory,truth)])
    yaw=[abs(wrap(state(a)[2]-state(b)[2]))*180/np.pi for a,b in zip(trajectory,truth)]
    return {'position_rmse_m':float(np.sqrt(np.mean(errors**2))),'endpoint_position_error_m':float(errors[-1]),
        'median_heading_error_deg':float(np.median(yaw)),'alignment':'Initial pose anchored only; no fitted trajectory alignment'}


def main():
    frames=[f for f in json.loads((ROOT/'data/manifest_v4.json').read_text())['frames'] if f['split']=='trajectory']
    if len(frames)!=82:raise ValueError('Unexpected predeclared trajectory window')
    frozen=json.loads((ROOT/'results/frozen_gate.json').read_text());gate=frozen['gate']
    from validation_study import checked_frames
    checked_frames(frames)
    total=time.perf_counter();points=[scan_points(ROOT/f['path']) for f in frames]
    sectors=[descriptor(*decode_scan(ROOT/f['path'])) for f in frames]
    vectors,model=extract_descriptors(frames)
    # Every consecutive scan supplies a motion estimate; initialization is zero,
    # then the preceding radar-only estimate. No supplied poses enter this chain.
    trajectory=[np.eye(3)];edges=[];previous=np.eye(3);odom_times=[]
    for i in range(1,len(frames)):
        start=time.perf_counter()
        r,t=icp(points[i],points[i-1],previous[:2,:2],previous[:2,2],iterations=30,threshold=4)
        measurement=np.eye(3);measurement[:2,:2]=r;measurement[:2,2]=t
        previous=measurement;trajectory.append(trajectory[-1]@measurement)
        edges.append((i-1,i,measurement,'odometry'));odom_times.append((time.perf_counter()-start)*1000)
    loop_records=[];unverified=[];checked=[];previous_loop=-100
    # One proposal at most every eight query scans, with >=40-frame temporal gap.
    for i in range(40,len(frames),8):
        pool=list(range(0,i-39));scores=np.array([vectors[frames[j]['id']]@vectors[frames[i]['id']] for j in pool])
        j=pool[int(np.argmax(scores))];_,shift=similarity(sectors[i],sectors[j])
        v=verify_fast(points[i],points[j],shift/60*2*np.pi);decision=apply_gate(v,gate)
        if 'yaw_rad' not in v:continue
        measurement=estimated_pose(v);edge=(j,i,measurement,'loop');unverified.append(edge)
        if decision['accepted']:checked.append(edge)
        loop_records.append({'query_index':i,'reference_index':j,'cosine':float(scores.max()),'verification':decision})
    raw_graph,raw_status=optimize(trajectory,edges+unverified)
    checked_graph,checked_status=optimize(trajectory,edges+checked) if checked else (trajectory,{'success':True,'reason':'No checked loops; same odometry trajectory'})
    robust_graph,robust_status=optimize(trajectory,edges+unverified,loss='soft_l1')
    robust_checked,robust_checked_status=optimize(trajectory,edges+checked,loss='soft_l1')
    # Evaluation is deliberately after radar-only estimates and decisions.
    poses=read_poses(frames[0]['sequence']);origin=poses[frames[0]['timestamp_us']]
    truth=[project_se2(np.linalg.inv(origin)@poses[f['timestamp_us']]) for f in frames]
    for record in loop_records:
        i,j=record['query_index'],record['reference_index']
        relative=project_se2(np.linalg.inv(poses[frames[j]['timestamp_us']])@poses[frames[i]['timestamp_us']])
        record['pose_error']=transform_error(record['verification'],relative)
    result={'scope':'Short development-sequence returning segment, not a long-route benchmark',
        'sequence':frames[0]['sequence'],'rows':[141,222],'scans':len(frames),
        'duration_s':(frames[-1]['timestamp_us']-frames[0]['timestamp_us'])/1e6,
        'ground_truth_path_length_m':float(sum(np.linalg.norm(b[:2,2]-a[:2,2]) for a,b in zip(truth,truth[1:]))),
        'loop_proposals':len(unverified),'checked_loops':len(checked),'loops':loop_records,
        'odometry':metrics(trajectory,truth),'unverified_graph':metrics(raw_graph,truth),'checked_graph':metrics(checked_graph,truth),
        'robust_unverified_graph':metrics(robust_graph,truth),'robust_checked_graph':metrics(robust_checked,truth),
        'unverified_optimizer':raw_status,'checked_optimizer':checked_status,
        'robust_unverified_optimizer':robust_status,'robust_checked_optimizer':robust_checked_status,
        'median_odometry_pair_ms':float(np.median(odom_times)),'wall_s':time.perf_counter()-total,
        'trajectories':{name:[state(t).tolist() for t in ts] for name,ts in [('truth',truth),('odometry',trajectory),('unverified',raw_graph),('checked',checked_graph),('robust_unverified',robust_graph),('robust_checked',robust_checked)]},
        'warning':'Fixed graph residual scales are heuristic; no calibrated covariance. Supplied poses define/evaluate the window only.'}
    (ROOT/'results/trajectory_v4.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ['trajectories','loops']},indent=2))

if __name__=='__main__':main()
