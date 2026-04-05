from __future__ import annotations

"""运行时注册中心，负责模型清单探测、实例缓存与显存释放策略。"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from app.core.runtime_paths import RuntimePaths
from app.core.runtime_logging import configure_runtime_logging
from app.core.settings import Settings, get_settings
from app.runtimes.sd15_runtime import SD15Runtime
from app.runtimes.unipic2_runtime import UniPic2Runtime
from scripts.download_models import get_model_manifest

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.registry")


class RuntimeRegistry:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        manifest_provider: Callable[[Settings | None], dict[str, dict[str, Any]]] = get_model_manifest,
    ) -> None:
        self._settings = settings or get_settings()
        self._manifest_provider = manifest_provider
        # 生成模型通过工厂注册，后续新增模型时只需要在这里挂接即可。
        self._generation_runtime_factories: dict[str, Callable[[], Any]] = {
            "sd15-electric": self._build_sd15_runtime,
            "unipic2-kontext": self._build_unipic2_runtime,
        }
        self._runtime_cache: dict[str, Any] = {}
        self._active_generation_model_name: str | None = None

    def get_generation_runtime(self, model_name: str):
        # 当前策略是“同一时刻只保留一个活跃生成模型”，以便在单卡环境中主动回收显存。
        if model_name not in self._generation_runtime_factories:
            raise KeyError(f"unsupported generation runtime: {model_name}")

        if self._active_generation_model_name and self._active_generation_model_name != model_name:
            logger.info(
                "switching generation runtime from=%s to=%s",
                self._active_generation_model_name,
                model_name,
            )
            self._release_generation_runtime(self._active_generation_model_name)

        if model_name not in self._runtime_cache:
            logger.info("building generation runtime model=%s", model_name)
            self._runtime_cache[model_name] = self._generation_runtime_factories[model_name]()
        else:
            logger.info("reusing cached generation runtime model=%s", model_name)
        self._active_generation_model_name = model_name
        return self._runtime_cache[model_name]

    def release_generation_runtime(self, model_name: str | None = None) -> None:
        """释放指定模型或当前活跃模型占用的运行时资源。"""
        target = model_name or self._active_generation_model_name
        if target is None:
            return
        self._release_generation_runtime(target)

    def list_models(self) -> dict[str, list[dict[str, Any]]]:
        # 模型中心既要展示注册表条目，也要反馈本地目录是否真的已经下载完成。
        manifest = self._manifest_provider(self._settings)
        items: list[dict[str, Any]] = []
        for name, entry in manifest.items():
            local_dir = Path(entry["local_dir"])
            has_files = local_dir.exists() and any(local_dir.iterdir())
            items.append(
                {
                    **entry,
                    "name": name,
                    "status": self._resolve_status(name=name, target=entry["target"], has_files=has_files),
                    "ready": has_files,
                }
            )
        items.sort(key=lambda item: item["name"])
        return {"items": items}

    def build_status(self) -> dict[str, Any]:
        paths = RuntimePaths(self._settings.runtime_root)
        report = paths.build_probe_report()
        report["packages"] = {
            "torch": self._package_available("torch"),
            "diffusers": self._package_available("diffusers"),
            "transformers": self._package_available("transformers"),
            "huggingface_hub": self._package_available("huggingface_hub"),
            "ImageReward": self._package_available("ImageReward"),
        }
        report["python_version"] = sys.version.split()[0]
        report["cuda_available"] = self._detect_cuda()
        report["models"] = self.list_models()["items"]
        return report

    def _build_sd15_runtime(self) -> SD15Runtime:
        return SD15Runtime(
            model_dir=self._settings.generation_model_dir / "sd15-electric",
            output_dir=self._settings.output_image_dir,
        )

    def _build_unipic2_runtime(self) -> UniPic2Runtime:
        return UniPic2Runtime(
            model_dir=self._settings.generation_model_dir / "unipic2-kontext",
            output_dir=self._settings.output_image_dir,
            offload_mode=self._settings.unipic2_offload_mode,
        )

    def _release_generation_runtime(self, model_name: str) -> None:
        # 实际运行时对象遵循 unload 协议，由各模型实现负责清理 torch / diffusers 资源。
        runtime = self._runtime_cache.pop(model_name, None)
        if runtime is not None:
            logger.info("releasing generation runtime model=%s", model_name)
            if hasattr(runtime, "unload"):
                runtime.unload()
        if self._active_generation_model_name == model_name:
            self._active_generation_model_name = None

    @staticmethod
    def _package_available(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    def _detect_cuda(self) -> bool | None:
        if not self._package_available("torch"):
            return None

        import torch

        return bool(torch.cuda.is_available())

    def _resolve_status(self, *, name: str, target: str, has_files: bool) -> str:
        if has_files:
            return "available"
        if target == "generation" and name not in self._generation_runtime_factories:
            return "experimental"
        return "unavailable"


# TODO: 后续如果接入多 GPU，可把“单活模型”策略升级为基于设备池的调度器。
