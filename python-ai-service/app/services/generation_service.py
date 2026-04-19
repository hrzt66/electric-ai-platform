from __future__ import annotations

"""统一封装生成阶段的参数修正与随机种子解析逻辑。"""

import logging
import secrets

from app.core.runtime_logging import configure_runtime_logging

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.generation")


class GenerationService:
    """生成服务，负责把任务参数整理后交给具体生成模型执行。"""

    def generate(self, job, runtime) -> list[dict]:
        """执行一次生成任务，并把最终使用的种子写回每张结果记录。"""
        # 前端约定 seed=-1 代表“随机种子”，这里在真正调用模型前解析成正整数。
        resolved_seed = self._resolve_seed(job.seed, job_id=getattr(job, "job_id", None))
        if resolved_seed != job.seed:
            logger.info("job %s requested random seed, resolved seed=%s", job.job_id, resolved_seed)

        images = runtime.generate(
            job_id=job.job_id,
            prompt=job.prompt,
            negative_prompt=job.negative_prompt,
            seed=resolved_seed,
            width=job.width,
            height=job.height,
            steps=job.steps,
            guidance_scale=job.guidance_scale,
            num_images=job.num_images,
            model_name=job.model_name,
        )
        for image in images:
            image.setdefault("seed", resolved_seed)
        return images

    @staticmethod
    def _resolve_seed(seed: int, *, job_id: int | None = None) -> int:
        """把随机种子约定统一成运行时可直接消费的正整数。"""
        if seed >= 0:
            return int(seed)
        if job_id is not None:
            max_seed = 2_147_483_647
            derived = (int(job_id) * 1_103_515_245 + 12_345) % max_seed
            return derived or 1
        return secrets.randbelow(2_147_483_647) + 1
