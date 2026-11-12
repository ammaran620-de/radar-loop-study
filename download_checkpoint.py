"""Retrieve the author's reviewed RadarLoc checkpoint without committing binaries."""
import hashlib
from pathlib import Path
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parent
PATH=ROOT/'third_party/radarloc/weights/radarloc.pth'
SHA256='aa36dcd85b7394d8c76fb77215fef2cc21448eecab6b86c3b24a507ef42193bb'
URL='https://raw.githubusercontent.com/jac99/RadarLoc/main/weights/radarloc.pth'


def ensure_checkpoint():
    if PATH.exists():
        if hashlib.sha256(PATH.read_bytes()).hexdigest()!=SHA256:
            raise ValueError('Existing RadarLoc checkpoint checksum mismatch')
        return PATH
    PATH.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(3):
        try:
            with urlopen(Request(URL,headers={'User-Agent':'radar-loop-study'}),timeout=60) as response:
                content=response.read()
            if hashlib.sha256(content).hexdigest()!=SHA256:raise ValueError('Downloaded checkpoint checksum mismatch')
            temporary=PATH.with_suffix('.partial');temporary.write_bytes(content);temporary.replace(PATH)
            return PATH
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

if __name__=='__main__':print(ensure_checkpoint())
