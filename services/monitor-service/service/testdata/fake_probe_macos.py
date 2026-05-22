#!/usr/bin/env python3
import json


def main() -> None:
    print(
        json.dumps(
            {
                "platform_family": "macos",
                "mps_available": True,
                "ai_process_memory_bytes": 123456,
            }
        )
    )


if __name__ == "__main__":
    main()

