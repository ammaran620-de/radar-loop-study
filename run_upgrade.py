"""Reproduce v3 baseline and v4 measurements in the documented order."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STEPS=[['download_sample.py'],['experiment.py'],['loop_closure_study.py'],
       ['download_validation_data.py'],['validation_study.py','development'],
       ['diagnose_rejections.py'],['validation_study.py','heldout'],['heldout_baseline.py'],
       ['trajectory_study.py'],['build_radar_map.py'],['online_replay.py'],['build_validation_report.py']]
if __name__=='__main__':
    for step in STEPS:
        print('\nRunning '+' '.join(step),flush=True)
        subprocess.run([sys.executable,*step],cwd=ROOT,check=True)
