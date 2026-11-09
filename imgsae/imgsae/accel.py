"""Accelerator helpers: one code path for CUDA (Windows laptop, RTX 3050 4 GB), MPS (the original Apple M5) and CPU.
Added for the Windows/CUDA port (see docs/EXECUTION_LOG.md); no analysis logic lives here.
"""
from __future__ import annotations

import torch


def pick(pref: str | None = "auto") -> str:
    """'auto' -> cuda if available, else mps, else cpu; anything else is returned unchanged."""
    if pref not in (None, "auto"): return pref
    if torch.cuda.is_available(): return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available(): return "mps"
    return "cpu"


def kind(device) -> str: return torch.device(device).type


def empty_cache(device):
    k = kind(device)
    if k == "cuda": torch.cuda.empty_cache()
    elif k == "mps": torch.mps.empty_cache()


def reset_peak(device):
    if kind(device) == "cuda": torch.cuda.reset_peak_memory_stats()


def mem_gb(device) -> float:
    """footprint for the memory gate/watchdog: CUDA = peak memory reserved by torch since the last reset_peak;
    MPS = driver-allocated memory (as on the M5); CPU = 0."""
    k = kind(device)
    if k == "cuda": return torch.cuda.max_memory_reserved() / 1e9
    if k == "mps": return torch.mps.driver_allocated_memory() / 1e9
    return 0.0


def capacity_gb(device) -> float:
    """physical device memory (CUDA); above this Windows (WDDM) silently spills to shared system RAM, which is slow."""
    if kind(device) == "cuda": return torch.cuda.get_device_properties(torch.device(device)).total_memory / 1e9
    return float("inf")


def name(device) -> str:
    if kind(device) == "cuda": return torch.cuda.get_device_name(torch.device(device))
    return kind(device)
