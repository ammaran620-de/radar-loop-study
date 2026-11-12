"""Development ablation, frozen gates and distinct-session pose validation."""
import argparse,hashlib,json,time,statistics
import numpy as np
from experiment import ROOT,decode_scan,descriptor,similarity,score_results
from geometric_verification import scan_points,verify_pair
from learned_descriptor import extract_descriptors
from pose_evaluation import read_poses,relative_pose,transform_error
from registration_v4 import verify_fast,apply_gate,ALGORITHM,icp,rotation


def checked_frames(frames):
    if len({f['id'] for f in frames})!=len(frames):raise ValueError('Duplicate frame IDs')
    for f in frames:
        if hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Scan checksum mismatch')
        if hashlib.sha256((ROOT/'data'/f['sequence']/'sensor_poses.csv').read_bytes()).hexdigest()!=f['pose_file_sha256']:raise ValueError('Pose checksum mismatch')


def summarize(records,gate=None):
    queries={}
    for record in records:queries.setdefault(record['query_id'],[]).append(record)
    chosen=[]
    for pairs in queries.values():
        first=next((p for p in pairs if (apply_gate(p['verification'],gate)['accepted'] if gate else p['verification'].get('accepted',False))),None)
        if first:chosen.append(first)
    errors=[p['pose_error'] for p in chosen]
    return {'queries':len(queries),'selected':len(chosen),'correct_pose':sum(e['pose_correct'] for e in errors),
        'wrong_pose':sum(not e['pose_correct'] for e in errors),'abstained':len(queries)-len(chosen),
        'pose_precision':sum(e['pose_correct'] for e in errors)/len(chosen) if chosen else None,
        'median_translation_error_m':statistics.median(e['translation_error_m'] for e in errors) if errors else None,
        'median_rotation_error_deg':statistics.median(e['rotation_error_deg'] for e in errors) if errors else None}


def calibrate(records):
    # Development-only grid; frozen before reading held-out observations.
    grid=[]
    for overlap in [.4,.5,.6,.7]:
        for rmse in [1.,1.5,2.,2.5]:
            gate={'overlap':overlap,'rmse_m':rmse};result=summarize(records,gate)
            grid.append({'gate':gate,'result':result})
    zero_error=[r for r in grid if r['result']['selected'] and r['result']['wrong_pose']==0]
    if not zero_error:raise RuntimeError('No zero-error development gate; do not silently claim calibration success')
    best=max(zero_error,key=lambda r:(r['result']['correct_pose'],r['gate']['overlap'],-r['gate']['rmse_m']))
    return best['gate'],grid


def prepare(frames):
    result={}
    for f in frames:
        angles,power=decode_scan(ROOT/f['path'])
        result[f['id']]={'points':scan_points(ROOT/f['path']),'sectors':descriptor(angles,power)}
    return result


def run_pairs(queries,refs,features,vectors,poses,mode):
    refvectors=np.array([vectors[r['id']] for r in refs]);records=[];query_times=[];ranks=[]
    distances=np.array([[np.hypot(q['x']-r['x'],q['y']-r['y']) for r in refs] for q in queries])
    for qi,q in enumerate(queries):
        begin=time.perf_counter();scores=refvectors@vectors[q['id']];order=np.argsort(-scores,kind='stable');ranks.append(order)
        for rank,j in enumerate(order[:3]):
            ref=refs[j];_,shift=similarity(features[q['id']]['sectors'],features[ref['id']]['sectors'])
            source,target=features[q['id']]['points'],features[ref['id']]['points']
            start=time.perf_counter();v=verify_fast(source,target,shift/60*2*np.pi) if mode=='v4' else verify_pair(source,target,shift/60*2*np.pi)
            elapsed=(time.perf_counter()-start)*1000;truth=relative_pose(q,ref,poses)
            records.append({'query_id':q['id'],'reference_id':ref['id'],'rank':rank+1,'score':float(scores[j]),
                'distance_m':float(distances[qi,j]),'verification':v,'verification_ms':elapsed,'pose_error':transform_error(v,truth)})
        query_times.append((time.perf_counter()-begin)*1000)
        if (qi+1)%10==0:print(mode,qi+1,'/',len(queries),flush=True)
    return records,{'median_retrieval_and_top3_registration_ms':float(np.median(query_times)),
        'p95_retrieval_and_top3_registration_ms':float(np.percentile(query_times,95))},score_results(ranks,distances,25)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['development','heldout']);args=parser.parse_args()
    old=json.loads((ROOT/'data/manifest.json').read_text());refs=[f for f in old['frames'] if f['split']=='reference']
    if args.stage=='development':queries=[f for f in old['frames'] if f['split']=='query']
    else:
        frozen=json.loads((ROOT/'results/frozen_gate.json').read_text())
        source_hash=hashlib.sha256((ROOT/'registration_v4.py').read_bytes()).hexdigest()
        if frozen.get('registration_source_sha256') != source_hash:
            raise ValueError('Registration source differs from frozen development snapshot')
        queries=[f for f in json.loads((ROOT/'data/manifest_v4.json').read_text())['frames'] if f['split']=='heldout']
    frames=refs+queries;checked_frames(frames)
    if {f['sequence'] for f in refs}&{f['sequence'] for f in queries}:raise ValueError('Sessions overlap')
    if {f['sha256'] for f in refs}&{f['sha256'] for f in queries}:raise ValueError('Cross-split identical scans')
    total=time.perf_counter();feature_start=time.perf_counter();features=prepare(frames)
    preparation=time.perf_counter()-feature_start;network_start=time.perf_counter();vectors,provenance=extract_descriptors(frames);network_wall=time.perf_counter()-network_start
    poses={sequence:read_poses(sequence) for sequence in {f['sequence'] for f in frames}}
    pairs,timing,retrieval=run_pairs(queries,refs,features,vectors,poses,'v4')
    if args.stage=='development':
        gate,grid=calibrate(pairs)
        frozen={'gate':gate,'algorithm':ALGORITHM,'training_session':queries[0]['sequence'],
            'criterion':'Maximize correct selected queries subject to zero development pose errors; exploratory, not safety calibration',
            'thresholds':{'translation_m':2,'rotation_deg':5},'calibration_grid':grid}
        frozen['registration_source_sha256']=hashlib.sha256((ROOT/'registration_v4.py').read_bytes()).hexdigest()
        frozen['development_manifest_sha256']=hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()
        frozen['config_sha256']=hashlib.sha256(json.dumps({'gate':gate,'algorithm':ALGORITHM},sort_keys=True).encode()).hexdigest()
        (ROOT/'results/frozen_gate.json').write_text(json.dumps(frozen,indent=2))
    else:
        gate=frozen['gate']
        if frozen['algorithm']!=ALGORITHM:raise ValueError('Algorithm differs from frozen development config')
    result={'stage':args.stage,'gate':gate,'model':provenance,'algorithm':ALGORITHM,
            'summary':summarize(pairs,gate),'retrieval_at_25m':retrieval,'timing':timing,
            'preparation_all_frames_s':preparation,'network_wall_all_frames_s':network_wall,
            'experiment_wall_s':time.perf_counter()-total,'records':pairs}
    (ROOT/f'results/{args.stage}_v4.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))

if __name__=='__main__':main()
