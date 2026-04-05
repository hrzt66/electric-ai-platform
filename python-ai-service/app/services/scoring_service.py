from __future__ import annotations

"""真实评分服务，负责多维分数计算、校准和批量资源释放。"""

from pathlib import Path

from app.services.mock_scorer import score_from_prompt


class ScoringService:
    # 当前权重体现“文本一致性优先”的业务目标，用于总分聚合。
    COMPONENT_WEIGHTS = {
        "visual_fidelity": 0.21,
        "text_consistency": 0.37,
        "physical_plausibility": 0.24,
        "composition_aesthetics": 0.18,
    }

    def __init__(
        self,
        *,
        visual_runtime=None,
        text_runtime=None,
        physical_runtime=None,
        aesthetics_runtime=None,
        shared_clip_runtime=None,
        release_after_batch: bool = False,
    ) -> None:
        """注入各维度评分运行时，并配置批处理结束后是否自动释放资源。"""
        self._visual_runtime = visual_runtime
        self._text_runtime = text_runtime
        self._physical_runtime = physical_runtime
        self._aesthetics_runtime = aesthetics_runtime
        self._shared_clip_runtime = shared_clip_runtime
        self._release_after_batch = release_after_batch

    def combine_scores(
        self,
        *,
        visual_fidelity: float,
        text_consistency: float,
        physical_plausibility: float,
        composition_aesthetics: float,
    ) -> dict[str, float]:
        """对四个维度做工程校准后，按权重生成最终综合得分。"""
        # 这里对原始分数做轻量校准，避免真实模型输出长期偏向“保真度过高、文本一致性偏低”。
        calibrated = {
            "visual_fidelity": self._compress_high_tail(visual_fidelity, knee=72.0, scale=0.38),
            "text_consistency": self._lift_low_band(text_consistency, target=52.0, gain=0.22),
            "physical_plausibility": self._compress_high_tail(physical_plausibility, knee=68.0, scale=0.45),
            "composition_aesthetics": self._compress_high_tail(composition_aesthetics, knee=70.0, scale=0.60),
        }
        total_score = round(
            sum(calibrated[name] * weight for name, weight in self.COMPONENT_WEIGHTS.items()),
            2,
        )
        return {
            **calibrated,
            "total_score": total_score,
        }

    def score_batch(self, job, images: list[dict]) -> list[dict]:
        """对一批生成图片逐张评分，并整理成资产服务可直接入库的结构。"""
        # 评分结果直接按资产入库结构组织，减少 Worker 与资产服务之间的二次转换。
        scored_items: list[dict] = []
        for image in images:
            image_path = image["file_path"]
            scores = self._score_image(image_path=image_path, prompt=job.prompt)
            scored_items.append(
                {
                    "image_name": Path(image_path).name,
                    "file_path": image_path,
                    "model_name": job.model_name,
                    "positive_prompt": job.prompt,
                    "negative_prompt": job.negative_prompt,
                    "sampling_steps": job.steps,
                    "seed": image.get("seed", job.seed),
                    "guidance_scale": job.guidance_scale,
                    **scores,
                }
            )
        if self._release_after_batch:
            self.release_resources()
        return scored_items

    def _score_image(self, *, image_path: str, prompt: str) -> dict[str, float]:
        """对单张图片完成四维评分，必要时退回 mock 评分兜底。"""
        # 当真实评分运行时缺失时退回 mock 评分，保证开发与测试链路仍然可跑通。
        if self._text_runtime is None or self._aesthetics_runtime is None:
            return score_from_prompt(prompt)

        if self._shared_clip_runtime is not None:
            visual = float(self._shared_clip_runtime.score_image(image_path, prompt, mode="visual_fidelity"))
            physical = float(self._shared_clip_runtime.score_image(image_path, prompt, mode="physical_plausibility"))
        elif self._visual_runtime is not None and self._physical_runtime is not None:
            visual = float(self._visual_runtime.score_image(image_path, prompt))
            physical = float(self._physical_runtime.score_image(image_path, prompt))
        else:
            return score_from_prompt(prompt)

        text = float(self._text_runtime.score_image(image_path, prompt))
        aesthetics = float(self._aesthetics_runtime.score_image(image_path, prompt))
        return self.combine_scores(
            visual_fidelity=visual,
            text_consistency=text,
            physical_plausibility=physical,
            composition_aesthetics=aesthetics,
        )

    def release_resources(self) -> None:
        """统一释放各评分运行时持有的模型资源。"""
        # 所有评分运行时都遵循 unload 协议，便于在任务结束后统一释放显存。
        for runtime in (
            self._visual_runtime,
            self._text_runtime,
            self._physical_runtime,
            self._aesthetics_runtime,
            self._shared_clip_runtime,
        ):
            if runtime is not None and hasattr(runtime, "unload"):
                runtime.unload()

    @staticmethod
    def _compress_high_tail(score: float, *, knee: float, scale: float) -> float:
        """压缩高分段增幅，防止某个维度长期虚高。"""
        bounded = max(0.0, min(100.0, float(score)))
        if bounded <= knee:
            return round(bounded, 2)
        return round(min(100.0, knee + (bounded - knee) * scale), 2)

    @staticmethod
    def _lift_low_band(score: float, *, target: float, gain: float) -> float:
        """温和抬升过低分段，缓解系统性偏低问题。"""
        bounded = max(0.0, min(100.0, float(score)))
        if bounded >= target:
            return round(bounded, 2)
        return round(min(100.0, bounded + (target - bounded) * gain), 2)


# TODO: 后续可引入人工标注集做自动标定，把当前经验参数升级为可复现实验结果。
