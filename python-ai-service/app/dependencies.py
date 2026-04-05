from __future__ import annotations

"""集中装配 Python AI 运行时依赖，避免 API 入口和 Worker 入口各自重复 new 对象。"""

from app.clients.asset_client import AssetClient
from app.clients.audit_client import AuditClient
from app.clients.task_client import TaskClient
from app.core.settings import Settings, get_settings
from app.runtimes.runtime_registry import RuntimeRegistry
from app.runtimes.scorers.aesthetic_runtime import AestheticRuntime
from app.runtimes.scorers.clip_iqa_runtime import ClipIQARuntime
from app.runtimes.scorers.image_reward_runtime import ImageRewardRuntime
from app.services.generation_service import GenerationService
from app.services.job_pipeline import JobPipeline
from app.services.scoring_service import ScoringService


def build_runtime_registry(settings: Settings | None = None) -> RuntimeRegistry:
    """创建运行时注册中心，统一管理生成模型实例的获取与释放。"""
    return RuntimeRegistry(settings=settings or get_settings())


def build_generation_service() -> GenerationService:
    """生成服务本身无状态，因此可以直接轻量实例化。"""
    return GenerationService()


def build_scoring_service(
    *,
    settings: Settings | None = None,
    release_after_batch: bool | None = None,
) -> ScoringService:
    """评分服务默认接入真实评分运行时，并复用同一个 CLIP-IQA 实例降低显存占用。"""
    runtime_settings = settings or get_settings()
    return ScoringService(
        text_runtime=ImageRewardRuntime(),
        aesthetics_runtime=AestheticRuntime(),
        shared_clip_runtime=ClipIQARuntime(mode="visual_fidelity"),
        release_after_batch=(
            runtime_settings.scoring_release_after_batch if release_after_batch is None else release_after_batch
        ),
    )


def build_job_pipeline(
    *,
    settings: Settings | None = None,
    runtime_registry: RuntimeRegistry | None = None,
    generation_service: GenerationService | None = None,
    scoring_service: ScoringService | None = None,
) -> JobPipeline:
    """把任务服务、资产服务、审计服务和本地模型链路组装成一条完整执行流水线。"""
    runtime_settings = settings or get_settings()
    return JobPipeline(
        task_client=TaskClient(runtime_settings.task_service_base_url),
        asset_client=AssetClient(runtime_settings.asset_service_base_url),
        audit_client=AuditClient(runtime_settings.audit_service_base_url),
        runtime_registry=runtime_registry or build_runtime_registry(runtime_settings),
        generation_service=generation_service or build_generation_service(),
        scoring_service=scoring_service or build_scoring_service(settings=runtime_settings),
    )
