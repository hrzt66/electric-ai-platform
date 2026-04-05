from __future__ import annotations

"""FastAPI 入口，提供健康检查、运行时探针和内部生成接口。"""

from fastapi import FastAPI

from app.dependencies import build_generation_service, build_runtime_registry, build_scoring_service
from app.schemas.jobs import GenerateJob


def create_app(*, runtime_registry=None, generation_service=None, scoring_service=None) -> FastAPI:
    """允许测试时注入假实现，线上则装配真实运行时与评分服务。"""
    registry = runtime_registry or build_runtime_registry()
    generator = generation_service or build_generation_service()
    scorer = scoring_service or build_scoring_service(release_after_batch=False)

    app = FastAPI(title="python-ai-service")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/runtime/status")
    def runtime_status() -> dict:
        return registry.build_status()

    @app.get("/runtime/models")
    def runtime_models() -> dict:
        return registry.list_models()

    @app.post("/internal/generate")
    def generate(request: GenerateJob) -> dict:
        # API 模式会直接在请求线程内执行生成和评分，适合 smoke test 与链路联调。
        runtime = registry.get_generation_runtime(request.model_name)
        generated_images = generator.generate(request, runtime)
        scored_results = scorer.score_batch(request, generated_images)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "job_id": request.job_id,
                "results": scored_results,
            },
            "trace_id": f"job-{request.job_id}",
        }

    return app


app = create_app()
