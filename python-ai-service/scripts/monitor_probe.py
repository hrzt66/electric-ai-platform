from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.torch_cuda import is_mps_available, preferred_torch_device_type


def detect_mps_available() -> bool:
    return is_mps_available()


def detect_preferred_device_type() -> str:
    return preferred_torch_device_type()


def measure_ai_process_memory_bytes() -> int:
    try:
        output = subprocess.check_output(["ps", "-axo", "rss=,command="], text=True)
    except Exception:
        return 0

    total_kb = 0
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        rss_kb, command = parts
        if "python-ai-service" not in command and "worker.py" not in command:
            continue
        if not rss_kb.isdigit():
            continue
        total_kb += int(rss_kb)
    return total_kb * 1024


def build_payload(system_name: str | None = None) -> dict[str, object]:
    detected = (system_name or platform.system()).lower()
    if detected == "darwin":
        mps_available = detect_mps_available()
        preferred_device = detect_preferred_device_type()
        ai_process_memory_bytes = measure_ai_process_memory_bytes()
        return {
            "platform_family": "macos",
            "mps_available": mps_available,
            "preferred_device_type": preferred_device,
            "ai_process_memory_bytes": ai_process_memory_bytes,
            "unavailable_reason": (
                "" if mps_available else "PyTorch MPS backend is not available on this machine"
            ),
        }

    return {
        "platform_family": "windows",
        "gpu_name": "",
        "vram_total_mb": 0,
        "vram_used_mb": 0,
        "gpu_utilization_percent": 0,
        "temperature_c": 0,
    }


def main() -> None:
    print(json.dumps(build_payload()))


if __name__ == "__main__":
    main()
