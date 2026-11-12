"""Build the static inspection console from reproducible experiment outputs."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent


def build():
    read=lambda name:json.loads((ROOT/'results'/name).read_text())
    legacy=read('learned_loop_study.json')
    data={'trajectory':read('trajectory_v4.json'),'development':read('development_v4.json'),
        'heldout':read('heldout_v4.json'),'heldoutBaseline':read('heldout_baseline_v3.json'),
        'gate':read('frozen_gate.json'),'maps':read('radar_maps_v4.json'),
        'replay':read('online_replay_v4.json'),'diagnosis':read('rejection_diagnosis_v4.json'),
        'observations':{key:legacy[key] for key in ['images','points','queries','references']}}
    output=ROOT/'site/study-data.js'
    output.write_text('window.RADAR_STUDY='+json.dumps(data,separators=(',',':'),allow_nan=False).replace('</','<\\/')+';')
    return output

if __name__=='__main__':print(build())
