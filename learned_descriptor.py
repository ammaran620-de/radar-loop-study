"""Frozen RadarLoc inference using the authors' released checkpoint."""
import hashlib
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "third_party/radarloc"
EXPECTED_CHECKPOINT_SHA256 = "aa36dcd85b7394d8c76fb77215fef2cc21448eecab6b86c3b24a507ef42193bb"
sys.path.insert(0, str(VENDOR))
from models.radar.radar_net import RadarNet
from models.radar.cylindrical_resnet_FPN import FPNFeatureExtractor
from layers.radar.pooling import GeM


def load_model():
    torch.set_num_threads(2)
    # The development environment's oneDNN path crashes for this older model.
    # Use the portable CPU kernels, including on machines with oneDNN enabled.
    torch.backends.mkldnn.enabled = False
    from download_checkpoint import ensure_checkpoint
    checkpoint_path = ensure_checkpoint()
    checkpoint_hash = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    if checkpoint_hash != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("RadarLoc checkpoint checksum does not match the reviewed release")
    feature_extractor = FPNFeatureExtractor(
        planes=[32, 64, 128, 256],
        layers=[1, 1, 1, 1],
        min_out_level=3,
        out_channels=256,
        cylindrical_padding=True,
    )
    model = RadarNet(feature_extractor, pooling=GeM(), normalize=False)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint, strict=True)
    model.eval()
    return model, checkpoint_hash


def model_input(scan_path):
    raw = cv2.imread(str(scan_path), cv2.IMREAD_GRAYSCALE)
    if raw is None or raw.ndim != 2 or raw.shape[1] <= 11:
        raise ValueError(f"Invalid radar PNG: {scan_path}")
    # Authors' preprocessing: strip metadata, transpose to range x angle,
    # area-resize to width=384 angles and height=128 ranges, scale and normalize.
    image = cv2.resize(raw[:, 11:].T, (384, 128), interpolation=cv2.INTER_AREA)
    normalized = (image.astype(np.float32) / 255.0 - 0.031) / 0.048
    return torch.from_numpy(normalized[None, None, :, :])


def extract_descriptors(frames):
    torch.set_num_threads(2)
    model, checkpoint_hash = load_model()
    descriptors = {}
    timings = []
    with torch.inference_mode():
        for frame in frames:
            input_tensor = model_input(ROOT / frame["path"])
            start = time.perf_counter()
            vector = model({"radar_batch": input_tensor}).numpy().reshape(-1)
            timings.append((time.perf_counter() - start) * 1000)
            descriptors[frame["id"]] = vector / max(np.linalg.norm(vector), 1e-9)
    return descriptors, {
        "name": "RadarLoc",
        "upstream": "https://github.com/jac99/RadarLoc",
        "checkpoint_sha256": checkpoint_hash,
        "frozen": True,
        "training": "Authors' released pretrained checkpoint; no fine-tuning on this sample",
        "preprocessing": "Author normalization and area-resize; full Boreas range is an out-of-domain adaptation",
        "descriptor_dimension": 256,
        "median_forward_ms": float(np.median(timings)),
        "p95_forward_ms": float(np.percentile(timings, 95)),
        "torch_version": torch.__version__,
    }
