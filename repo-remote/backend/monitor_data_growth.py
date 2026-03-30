import time
import os
import numpy as np
from pathlib import Path

DATA_DIR = Path(os.path.dirname(__file__)).parent / "model" / "training_data"
CHECK_INTERVAL = 300  # seconds (5 minutes)
MIN_SEQUENCES = 50    # You can adjust this threshold

print("[MONITOR] Monitoring data growth for all locations...")

while True:
    ready = []
    counts = {}
    for file in DATA_DIR.glob("X_*.npy"):
        arr = np.load(file)
        counts[file.name] = arr.shape[0]
        if arr.shape[0] >= MIN_SEQUENCES:
            ready.append(file.name)
    print(f"[MONITOR] {time.strftime('%Y-%m-%d %H:%M:%S')} | Sequences per location: {counts}")
    if len(ready) == len(counts) and len(counts) > 0:
        print(f"[MONITOR] All locations have at least {MIN_SEQUENCES} sequences. Ready to train!")
        break
    time.sleep(CHECK_INTERVAL)
