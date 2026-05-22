#!/usr/bin/env python3
import json


def main() -> None:
    print(
        json.dumps(
            {
                "platform_family": "windows",
                "gpu_name": "NVIDIA GeForce RTX 4060",
                "vram_total_mb": 8192,
                "vram_used_mb": 2048,
                "gpu_utilization_percent": 33.5,
                "temperature_c": 61.5,
            }
        )
    )


if __name__ == "__main__":
    main()
