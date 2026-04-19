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


def is_mps_available() -> bool:
    """返回当前 PyTorch 是否暴露可用的 MPS 设备。"""
    try:
        import torch
    except ImportError:
        return False

    backends = getattr(torch, "backends", None)
    mps_backend = getattr(backends, "mps", None)
    is_available = getattr(mps_backend, "is_available", None)
    return bool(callable(is_available) and is_available())


def preferred_torch_device_type() -> str:
    """统一返回当前首选 torch 设备类型。"""
    try:
        import torch
    except ImportError:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    if is_mps_available():
        return "mps"
    return "cpu"


def best_effort_cleanup_torch(*, logger: logging.Logger | None = None, label: str = "runtime") -> None:
    """尽力执行当前设备对应的缓存回收，避免任务结束后残留显存。"""
    gc.collect()
    try:
        import torch
    except ImportError:
        return

    if torch.cuda.is_available():
        for step_name in ("synchronize", "empty_cache", "ipc_collect"):
            step = getattr(torch.cuda, step_name, None)
            if not callable(step):
                continue
            try:
                step()
            except Exception as exc:  # pragma: no cover - 仅在真实 CUDA 故障时触发
                if logger is not None:
                    logger.warning("torch cleanup step failed label=%s step=%s error=%s", label, step_name, exc)
        gc.collect()
        return

    if is_mps_available():
        empty_cache = getattr(getattr(torch, "mps", None), "empty_cache", None)
        if callable(empty_cache):
            try:
                empty_cache()
            except Exception as exc:  # pragma: no cover - 仅在真实 MPS 故障时触发
                if logger is not None:
                    logger.warning("torch cleanup step failed label=%s step=mps.empty_cache error=%s", label, exc)
        gc.collect()


def best_effort_cleanup_cuda(*, logger: logging.Logger | None = None, label: str = "runtime") -> None:
    """兼容旧调用点，实际复用通用 torch 清理逻辑。"""
    best_effort_cleanup_torch(logger=logger, label=label)
