"""Voxelized radar-return fusion; no occupancy/free-space or map-accuracy claim."""
import json
import numpy as np
from experiment import ROOT
from geometric_verification import scan_points
from trajectory_study import se2


def fuse_returns(point_clouds,trajectory,resolution=.5):
    transformed=[points@pose[:2,:2].T+pose[:2,2] for points,pose in zip(point_clouds,trajectory)]
    all_points=np.concatenate(transformed)
    keys=np.floor(all_points/resolution).astype(int)
    cells,counts=np.unique(keys,axis=0,return_counts=True)
    # Repeated return support, not a semantic/static-object classifier.
    supported=counts>=2
    return {'resolution_m':resolution,'input_returns':len(all_points),'cells':[
        [float((x+.5)*resolution),float((y+.5)*resolution),int(n)]
        for (x,y),n in zip(cells[supported],counts[supported])],
        'meaning':'Cells with >=2 radar returns; unknown/free space is not modelled'}


def main():
    result=json.loads((ROOT/'results/trajectory_v4.json').read_text())
    frames=[f for f in json.loads((ROOT/'data/manifest_v4.json').read_text())['frames'] if f['split']=='trajectory']
    points=[scan_points(ROOT/f['path']) for f in frames];maps={}
    for key in ['odometry','checked']:
        maps[key]=fuse_returns(points,[se2(p) for p in result['trajectories'][key]])
    (ROOT/'results/radar_maps_v4.json').write_text(json.dumps(maps,allow_nan=False))
    cells=maps['checked']['cells'];header=['ply','format ascii 1.0',f'element vertex {len(cells)}',
        'property float x','property float y','property float z','property int support','end_header']
    (ROOT/'results/checked_radar_map.ply').write_text('\n'.join(header)+'\n'+''.join(f'{x} {y} 0 {n}\n' for x,y,n in cells))
    print({key:len(value['cells']) for key,value in maps.items()})

if __name__=='__main__':main()
