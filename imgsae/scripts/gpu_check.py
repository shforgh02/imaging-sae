"""Quick GPU health check before long runs: 20 CT-FM forward passes on a 160^3 fp16 window while sampling clock/power.
usage: .venv\Scripts\python scripts\gpu_check.py
Healthy RTX 3050 Ti laptop: SM clock well above 210 MHz under load, power.draw <= enforced limit (~50 W), no sw_power_cap.
(Added 2026-11-07 after a broken power-sensor reading pinned the GPU at its minimum clock; see docs/EXECUTION_LOG.md.)
"""
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import torch  # noqa: E402
from imgsae.encoders import ctfm  # noqa: E402

Q = "clocks.sm,clocks.max.sm,power.draw,enforced.power.limit,temperature.gpu,clocks_throttle_reasons.sw_power_cap"
samples = []


def sample(stop):
    while not stop.is_set():
        samples.append(subprocess.run(["nvidia-smi", f"--query-gpu={Q}", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()); time.sleep(2)


def main():
    m = ctfm.load("cuda").half(); x = torch.rand(1, 1, 160, 160, 160, device="cuda", dtype=torch.float16); stop = threading.Event()
    with torch.no_grad():
        m(x); torch.cuda.synchronize(); th = threading.Thread(target=sample, args=(stop,)); th.start(); t = time.time()
        for _ in range(20): m(x)
        torch.cuda.synchronize(); spw = (time.time() - t) / 20; stop.set(); th.join()
    print("clock MHz, max MHz, power W, limit W, temp C, power cap"); print("\n".join(samples))
    capped = any("Active" in s.split(",")[-1] for s in samples)
    print(f"seconds per 160^3 window: {spw:.3f}  ->  {'POWER-CAPPED (see EXECUTION_LOG)' if capped else 'OK'}")


if __name__ == "__main__":
    main()
