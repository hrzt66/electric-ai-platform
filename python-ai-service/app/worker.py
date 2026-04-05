from __future__ import annotations

from app.workers.job_worker import JobWorker


def build_worker(pipeline) -> JobWorker:
    return JobWorker(pipeline=pipeline)


def main() -> int:
    raise SystemExit("Worker bootstrap will be wired after Redis consumer integration.")


if __name__ == "__main__":
    main()
