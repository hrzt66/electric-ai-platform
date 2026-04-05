from __future__ import annotations

"""任务执行流水线：更新任务状态、记录审计、生成图片、评分并持久化结果。"""

import logging

from app.core.runtime_logging import configure_runtime_logging
from app.schemas.jobs import GenerateJob

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.job_pipeline")


class JobPipeline:
    def __init__(
        self,
        task_client,
        asset_client,
        audit_client,
        runtime_registry,
        generation_service,
        scoring_service,
    ) -> None:
        self._task_client = task_client
        self._asset_client = asset_client
        self._audit_client = audit_client
        self._runtime_registry = runtime_registry
        self._generation_service = generation_service
        self._scoring_service = scoring_service

    def run(self, job: GenerateJob) -> list[dict]:
        # 整条链路始终围绕“状态推进 + 审计留痕 + 资源释放”三件事展开。
        try:
            logger.info(
                "job %s starting model=%s images=%s size=%sx%s steps=%s",
                job.job_id,
                job.model_name,
                job.num_images,
                job.width,
                job.height,
                job.steps,
            )
            self._task_client.update_status(job.job_id, "preparing", "preparing")
            self._audit_client.record_event("task.preparing", {"job_id": job.job_id, "model_name": job.model_name})

            runtime = self._runtime_registry.get_generation_runtime(job.model_name)
            logger.info(
                "job %s runtime ready model=%s runtime=%s",
                job.job_id,
                job.model_name,
                type(runtime).__name__,
            )

            self._task_client.update_status(job.job_id, "downloading", "downloading")
            self._audit_client.record_event("model.prepare", {"job_id": job.job_id, "model_name": job.model_name})

            self._task_client.update_status(job.job_id, "generating", "generating")
            logger.info("job %s generation started model=%s", job.job_id, job.model_name)
            generated_images = self._generation_service.generate(job, runtime)
            logger.info("job %s generation completed count=%s", job.job_id, len(generated_images))
            self._audit_client.record_event("generation.completed", {"job_id": job.job_id, "count": len(generated_images)})

            self._task_client.update_status(job.job_id, "scoring", "scoring")
            logger.info("job %s scoring started count=%s", job.job_id, len(generated_images))
            scored_assets = self._scoring_service.score_batch(job, generated_images)
            logger.info("job %s scoring completed count=%s", job.job_id, len(scored_assets))

            self._task_client.update_status(job.job_id, "persisting", "persisting")
            logger.info("job %s persisting assets count=%s", job.job_id, len(scored_assets))
            self._asset_client.save_results(job.job_id, scored_assets)

            self._task_client.update_status(job.job_id, "completed", "completed")
            logger.info("job %s completed asset_count=%s", job.job_id, len(scored_assets))
            self._audit_client.record_event("task.completed", {"job_id": job.job_id, "asset_count": len(scored_assets)})
            return scored_assets
        except Exception as exc:
            message = str(exc)
            logger.exception("job %s failed model=%s", job.job_id, job.model_name)
            self._task_client.update_status(job.job_id, "failed", "failed", message)
            self._audit_client.record_event("task.failed", {"job_id": job.job_id, "error_message": message})
            return []
        finally:
            # FIFO 任务场景下，用完即释放显存，避免后续模型切换时长期占满 GPU。
            if hasattr(self._runtime_registry, "release_generation_runtime"):
                logger.info("job %s releasing generation runtime model=%s", job.job_id, job.model_name)
                self._runtime_registry.release_generation_runtime(job.model_name)
            if hasattr(self._scoring_service, "release_resources"):
                logger.info("job %s releasing scoring resources", job.job_id)
                self._scoring_service.release_resources()
