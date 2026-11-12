"""Development-only oracle ablation. NEVER a deployment initialization."""
import json
import numpy as np
from experiment import ROOT
from geometric_verification import scan_points,alignment_statistics
from pose_evaluation import read_poses,relative_pose,transform_error
from registration_v4 import icp,apply_gate


def main():
    old=json.loads((ROOT/'results/learned_loop_study.json').read_text())
    new=json.loads((ROOT/'results/development_v4.json').read_text())
    queries={q['id']:q for q in old['queries']};refs={r['id']:r for r in old['references']}
    poses={s:read_poses(s) for s in [old['reference_sequence'],old['query_sequence']]}
    points={f['id']:scan_points(ROOT/f['path']) for f in [*queries.values(),*refs.values()]}
    records=[]
    for record in new['records']:
        if record['distance_m']>25:continue
        q,ref=queries[record['query_id']],refs[record['reference_id']]
        truth=relative_pose(q,ref,poses)
        r,t=icp(points[q['id']],points[ref['id']],truth[:2,:2],truth[:2,2],iterations=30)
        stats=alignment_statistics(points[q['id']],points[ref['id']],r,t)
        stats.update(yaw_rad=float(np.arctan2(r[1,0],r[0,0])),translation_xy_m=t.tolist())
        oracle_error=transform_error(stats,truth)
        records.append({'query_id':q['id'],'reference_id':ref['id'],
            'normal_pose_error':record['pose_error'],'oracle_pose_error':oracle_error,
            'normal_passes_gate':apply_gate(record['verification'],new['gate'])['accepted'],
            'oracle_passes_gate':apply_gate(stats,new['gate'])['accepted'],
            'initialization_limited':not record['pose_error']['pose_correct'] and oracle_error['pose_correct']})
    baseline=[]
    for q in old['queries']:
        accepted=next((c for c in q['candidates'] if c['verification']['accepted']),None)
        if accepted:baseline.append(transform_error(accepted['verification'],relative_pose(q,refs[accepted['reference_id']],poses)))
    result={'warning':'Oracle uses ground truth solely to diagnose development failures. Excluded from frozen and held-out inference.',
        'nearby_pairs':len(records),'normal_correct_pairs':sum(r['normal_pose_error']['pose_correct'] for r in records),
        'oracle_correct_pairs':sum(r['oracle_pose_error']['pose_correct'] for r in records),
        'initialization_limited_pairs':sum(r['initialization_limited'] for r in records),
        'old_selected_queries':len(baseline),'old_pose_correct_queries':sum(r['pose_correct'] for r in baseline),
        'records':records}
    (ROOT/'results/rejection_diagnosis_v4.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))

if __name__=='__main__':main()
