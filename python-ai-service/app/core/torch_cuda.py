from __future__ import annotations

"""Torch CUDA 辅助函数，统一处理随机种子和显存清理。"""

import gc
import logging


def seed_global_torch(seed: int) -> None:
    """同时设置 CPU 与 CUDA 默认随机数生成器的种子。"""
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available() and hasattr(torch.cuda, "manual_seed_all"):
        torch.cuda.manual_seed_all(seed)


def best_effort_cleanup_cuda(*, logger: logging.Logger | None = None, label: str = "runtime") -> None:
    """尽力执行 CUDA 同步和缓存回收，避免任务结束后残留显存。"""
    gc.collect()
    try:
        import torch
    except ImportError:
        return

    if not torch.cuda.is_available():
        return

    for step_name in ("synchronize", "empty_cache", "ipc_collect"):
        step = getattr(torch.cuda, step_name, None)
        if not callable(step):
            continue
        try:
            step()
        except Exception as exc:  # pragma: no cover - 仅在真实 CUDA 故障时触发
            if logger is not None:
                logger.warning("cuda cleanup step failed label=%s step=%s error=%s", label, step_name, exc)

    gc.collect()
