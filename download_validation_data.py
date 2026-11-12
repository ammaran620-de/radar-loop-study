"""Fixed held-out session and a predeclared, contiguous real-motion segment."""
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from download_sample import ROOT,download,records


def main():
    entries=[]
    for purpose,sequence in [('heldout','boreas-2021-09-07-09-35'),('trajectory','boreas-2021-09-02-11-42')]:
        folder=ROOT/'data'/sequence
        source=f'https://boreas.s3.amazonaws.com/{sequence}/applanix/radar_poses.csv'
        raw=download(source,folder/'sensor_poses.csv');rows=records(folder/'sensor_poses.csv')
        indexes=np.linspace(0,len(rows)-1,40,dtype=int) if purpose=='heldout' else range(141,223)
        for index in indexes:
            row=rows[index];timestamp=int(row['GPSTime']);path=f'data/{sequence}/radar/{timestamp}.png'
            entries.append({'id':f'{purpose}_{index}','split':purpose,'sequence':sequence,
                'timestamp_us':timestamp,'path':path,'x':float(row['easting']),'y':float(row['northing']),
                'source_url':f'https://boreas.s3.amazonaws.com/{sequence}/radar/{timestamp}.png',
                'pose_source_url':source,'pose_file_sha256':hashlib.sha256(raw).hexdigest()})
    def fetch(frame):
        frame['sha256']=hashlib.sha256(download(frame['source_url'],ROOT/frame['path'])).hexdigest();return frame
    with ThreadPoolExecutor(max_workers=8) as pool:
        frames=[]
        for i,frame in enumerate(pool.map(fetch,entries),1):
            frames.append(frame)
            if i%20==0:print(f'Downloaded {i}/{len(entries)}',flush=True)
    (ROOT/'data/manifest_v4.json').write_text(json.dumps({'protocol':'docs/UPGRADE_PROTOCOL.md',
        'dataset':'Boreas','license':'CC BY 4.0','trajectory_window_rows':[141,222],
        'heldout_sampling':'40 uniform row indices, separate session','frames':frames},indent=2))

if __name__=='__main__':main()
