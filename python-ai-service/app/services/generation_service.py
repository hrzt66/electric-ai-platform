from __future__ import annotations

"""统一封装生成阶段的参数修正与随机种子解析逻辑。"""

import logging
import secrets

from app.core.runtime_logging import configure_runtime_logging

configure_runtime_logging()
logger = logging.getLogger("electric_ai.runtime.generation")


class GenerationService:
    def generate(self, job, runtime) -> list[dict]:
        # 前端约定 seed=-1 代表“随机种子”，这里在真正调用模型前解析成正整数。
        resolved_seed = self._resolve_seed(job.seed)
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
    def _resolve_seed(seed: int) -> int:
        """把随机种子约定统一成运行时可直接消费的正整数。"""
        return int(seed) if seed >= 0 else secrets.randbelow(2_147_483_647) + 1
