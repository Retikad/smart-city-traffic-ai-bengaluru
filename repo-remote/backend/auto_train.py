"""Autotrainer: monitor data and trigger preprocess+training when ready.

Run this with the project's venv Python to ensure imports and paths resolve:
  python -m backend.auto_train

The script will periodically run preprocessing, check exported `X_*.npy`
arrays in `backend/model/training_data`, and once every configured corridor
has at least `MIN_SEQS_PER_LOCATION` sequences it will invoke training.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

CHECK_INTERVAL = int(__import__('os').getenv('AUTO_TRAIN_CHECK_SECONDS', '60'))
MIN_SEQS_PER_LOCATION = int(__import__('os').getenv('MIN_SEQS_PER_LOCATION', '10'))

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'model' / 'training_data'


def run_preprocess() -> int:
    """Run the preprocessing step as a subprocess and return exit code."""
    print('[AUTO_TRAIN] Running preprocess...')
    res = subprocess.run([sys.executable, '-m', 'backend.preprocess'])
    print(f'[AUTO_TRAIN] Preprocess exit: {res.returncode}')
    return res.returncode


def run_training() -> int:
    """Invoke the training pipeline as a subprocess and return exit code."""
    print('[AUTO_TRAIN] Triggering training...')
    res = subprocess.run([sys.executable, '-m', 'backend.model.train'])
    print(f'[AUTO_TRAIN] Training exit: {res.returncode}')
    return res.returncode


def discover_sequences() -> Dict[str, int]:
    """Return mapping of location -> number of sequences in X_*.npy files."""
    out: Dict[str, int] = {}
    if not DATA_DIR.exists():
        return out
    for p in sorted(DATA_DIR.glob('X_*.npy')):
        name = p.stem.replace('X_', '')
        try:
            import numpy as _np

            arr = _np.load(p)
            out[name] = int(arr.shape[0])
        except Exception:
            out[name] = 0
    return out


def all_locations_ready(seq_map: Dict[str, int], required: int) -> bool:
    if not seq_map:
        return False
    for loc, cnt in seq_map.items():
        if cnt < required:
            return False
    return True


def main() -> None:
    print('[AUTO_TRAIN] Starting auto-train monitor')
    while True:
        try:
            # Always run preprocess to refresh exports.
            run_preprocess()

            seqs = discover_sequences()
            print('[AUTO_TRAIN] Sequence counts:', seqs)

            if all_locations_ready(seqs, MIN_SEQS_PER_LOCATION):
                rc = run_training()
                if rc == 0:
                    print('[AUTO_TRAIN] Training completed successfully — exiting monitor.')
                    return
                else:
                    print('[AUTO_TRAIN] Training failed, will retry after delay.')
        except Exception as e:
            print('[AUTO_TRAIN] ERROR:', e)

        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
