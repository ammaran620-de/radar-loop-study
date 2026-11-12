"""Frozen original v3 geometry comparator on the new held-out session."""
import json,time
from experiment import ROOT,decode_scan,descriptor,similarity
from geometric_verification import scan_points,verify_pair
from pose_evaluation import read_poses,relative_pose,transform_error
from validation_study import summarize


def main():
    old=json.loads((ROOT/'data/manifest.json').read_text());extra=json.loads((ROOT/'data/manifest_v4.json').read_text())
    frames=[f for f in old['frames'] if f['split']=='reference']+[f for f in extra['frames'] if f['split']=='heldout']
    lookup={f['id']:f for f in frames};features={}
    for f in frames:features[f['id']]={'points':scan_points(ROOT/f['path']),'sectors':descriptor(*decode_scan(ROOT/f['path']))}
    poses={seq:read_poses(seq) for seq in {f['sequence'] for f in frames}};records=[]
    for prior in json.loads((ROOT/'results/heldout_v4.json').read_text())['records']:
        q,r=lookup[prior['query_id']],lookup[prior['reference_id']]
        _,shift=similarity(features[q['id']]['sectors'],features[r['id']]['sectors'])
        start=time.perf_counter();v=verify_pair(features[q['id']]['points'],features[r['id']]['points'],shift/60*6.283185307179586)
        records.append({**{k:prior[k] for k in ['query_id','reference_id','rank','score','distance_m']},'verification':v,
            'verification_ms':(time.perf_counter()-start)*1000,'pose_error':transform_error(v,relative_pose(q,r,poses))})
    result={'scope':'Original frozen v3 geometry, identical held-out descriptor candidates; no new calibration',
        'summary':summarize(records),'records':records}
    (ROOT/'results/heldout_baseline_v3.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(result['summary'])

if __name__=='__main__':main()
