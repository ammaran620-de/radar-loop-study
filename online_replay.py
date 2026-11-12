"""Warm-reference, image-to-decision CPU replay, including I/O and preprocessing."""
import hashlib,json,platform,time
import numpy as np
import torch
from experiment import ROOT,decode_scan,descriptor,similarity
from geometric_verification import scan_points
from learned_descriptor import load_model,model_input,extract_descriptors
from registration_v4 import verify_fast,apply_gate


def predict(frame,references,reference_features,reference_vectors,model,gate):
    # This perception boundary never reads frame coordinates or ground truth.
    start=time.perf_counter();angles,power=decode_scan(ROOT/frame['path'])
    sectors=descriptor(angles,power);points=scan_points(ROOT/frame['path'])
    with torch.inference_mode():
        vector=model({'radar_batch':model_input(ROOT/frame['path'])}).numpy().reshape(-1)
    vector/=max(np.linalg.norm(vector),1e-9)
    order=np.argsort(-(reference_vectors@vector),kind='stable')[:3]
    evidence=[];selected=None
    for j in order:
        ref=references[j];cached=reference_features[ref['id']]
        _,shift=similarity(sectors,cached['sectors'])
        stats=verify_fast(points,cached['points'],shift/60*2*np.pi);decision=apply_gate(stats,gate)
        evidence.append({'reference_id':ref['id'],'registration':decision})
        if decision['accepted']:
            selected=ref['id'];break
    return {'query_id':frame['id'],'selected_reference_id':selected,
            'decision':'provisional_candidate' if selected else 'abstain','evidence':evidence,
            'image_to_decision_ms':(time.perf_counter()-start)*1000}


def main():
    old=json.loads((ROOT/'data/manifest.json').read_text());extra=json.loads((ROOT/'data/manifest_v4.json').read_text())
    refs=[f for f in old['frames'] if f['split']=='reference'];gate=json.loads((ROOT/'results/frozen_gate.json').read_text())['gate']
    setup=time.perf_counter();features={}
    for ref in refs:
        angles,power=decode_scan(ROOT/ref['path'])
        features[ref['id']]={'sectors':descriptor(angles,power),'points':scan_points(ROOT/ref['path'])}
    descriptors,_=extract_descriptors(refs);vectors=np.array([descriptors[r['id']] for r in refs]);model,_=load_model()
    setup_s=time.perf_counter()-setup;output={}
    for name,queries in [('development',[f for f in old['frames'] if f['split']=='query']),('heldout',[f for f in extra['frames'] if f['split']=='heldout'])]:
        # Strip evaluation labels before entering the measured prediction API.
        records=[predict({k:f[k] for k in ['id','path','timestamp_us']},refs,features,vectors,model,gate) for f in queries]
        times=[r['image_to_decision_ms'] for r in records]
        output[name]={'median_image_to_decision_ms':float(np.median(times)),
            'p95_image_to_decision_ms':float(np.percentile(times,95)),
            'selected':sum(r['selected_reference_id'] is not None for r in records),'records':records}
    result={'scope':'CPU file replay, warm reference database; includes query file I/O, preprocessing, neural inference, retrieval and sequential candidate checks',
        'not_measured':['sensor acquisition','ROS transport','embedded target hardware','long-running live operation'],
        'reference_setup_s':setup_s,'reference_cache_array_bytes':int(vectors.nbytes+sum(v['sectors'].nbytes+v['points'].nbytes for v in features.values())),
        'python':platform.python_version(),'torch':torch.__version__,'machine':platform.machine(),
        'sessions':output}
    (ROOT/'results/online_replay_v4.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({name:{k:v for k,v in session.items() if k!='records'} for name,session in output.items()},indent=2))

if __name__=='__main__':main()
