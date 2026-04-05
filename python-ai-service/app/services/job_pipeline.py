from __future__ import annotations

from app.schemas.jobs import GenerateJob


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
        try:
            self._task_client.update_status(job.job_id, "preparing", "preparing")
            self._audit_client.record_event("task.preparing", {"job_id": job.job_id, "model_name": job.model_name})

            runtime = self._runtime_registry.get_generation_runtime(job.model_name)

            self._task_client.update_status(job.job_id, "downloading", "downloading")
            self._audit_client.record_event("model.prepare", {"job_id": job.job_id, "model_name": job.model_name})

            self._task_client.update_status(job.job_id, "generating", "generating")
            generated_images = self._generation_service.generate(job, runtime)
            self._audit_client.record_event("generation.completed", {"job_id": job.job_id, "count": len(generated_images)})

            self._task_client.update_status(job.job_id, "scoring", "scoring")
            scored_assets = self._scoring_service.score_batch(job, generated_images)

            self._task_client.update_status(job.job_id, "persisting", "persisting")
            self._asset_client.save_results(job.job_id, scored_assets)

            self._task_client.update_status(job.job_id, "completed", "completed")
            self._audit_client.record_event("task.completed", {"job_id": job.job_id, "asset_count": len(scored_assets)})
            return scored_assets
        except Exception as exc:
            message = str(exc)
            self._task_client.update_status(job.job_id, "failed", "failed", message)
            self._audit_client.record_event("task.failed", {"job_id": job.job_id, "error_message": message})
            return []
