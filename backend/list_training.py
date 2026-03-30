import glob
import os
import json
import numpy as np
from pathlib import Path

files = sorted(glob.glob(str(Path(__file__).parent / 'model' / 'training_data' / 'X_*.npy')))
out = {}
for f in files:
    try:
        arr = np.load(f)
        out[Path(f).name] = {'shape': list(arr.shape), 'file_size_bytes': os.path.getsize(f)}
    except Exception as e:
        out[Path(f).name] = {'error': str(e)}
print(json.dumps(out))
