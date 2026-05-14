import subprocess
import time
import numpy as np

start = time.time()
out = subprocess.run("adb exec-out screencap", shell=True, capture_output=True).stdout
print(f"Raw capture took: {time.time() - start:.3f}s. Size: {len(out)} bytes")

start = time.time()
out_p = subprocess.run("adb exec-out screencap -p", shell=True, capture_output=True).stdout
print(f"PNG capture took: {time.time() - start:.3f}s. Size: {len(out_p)} bytes")
