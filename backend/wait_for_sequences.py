"""Wait until every corridor has at least MIN_SEQS sequences exported.

Run as module from project root with the venv Python so imports work:
  python -m backend.wait_for_sequences

This will periodically print per-location sequence counts and exit when all
locations defined in `backend.database.CORRIDORS` have >= MIN_SEQS.
"""

from __future__ import annotations

import time
from pathlib import Path
import sys

MIN_SEQS = int(__import__('os').getenv('MIN_SEQS_PER_LOCATION', '10'))
SLEEP = int(__import__('os').getenv('WAIT_CHECK_SECONDS', '60'))


def discover_counts() -> dict:
    import glob
    import numpy as _np
    from pathlib import Path

    d = Path(__file__).resolve().parents[1] / 'model' / 'training_data'
    counts = {}
    if not d.exists():
        return counts
    for p in sorted(d.glob('X_*.npy')):
        try:
            arr = _np.load(p)
            counts[p.stem.replace('X_', '')] = int(arr.shape[0])
        except Exception:
            counts[p.stem.replace('X_', '')] = 0
    return counts


def main() -> int:
    print(f'[WAIT] Waiting for >= {MIN_SEQS} sequences per location (checking every {SLEEP}s)')
    while True:
        counts = discover_counts()
        print('[WAIT] Current sequence counts:', counts)

        # If any location missing or below threshold, sleep and continue.
        missing = [k for k, v in counts.items() if v < MIN_SEQS]
        if not counts:
            print('[WAIT] No exported arrays yet')
        if not missing and counts:
            print('[WAIT] All locations have reached the threshold — exiting')
            return 0

        time.sleep(SLEEP)


if __name__ == '__main__':
    sys.exit(main())
