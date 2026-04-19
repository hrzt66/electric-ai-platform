from __future__ import annotations

from dataclasses import asdict, dataclass


FIXED_GENERATION_PROMPTS = [
    "modern electrical substation yard, high-voltage breakers and transformers, stainless steel busbars, gravel ground, safety fencing, warning signage sharp and legible, tidy cables, cinematic depth of field",
    "aerial view of steel lattice transmission towers marching across landscape, taut conductors, wide right-of-way, realistic insulators, rolling terrain, clear sky",
    "grid control room, wall of SCADA screens, operators at desks, LED status panels, cool white lighting, cable management neat, reflective floor, photorealistic optics",
    "utility-scale wind turbines on gentle hills, aligned rows, late afternoon sun, long shadows, crisp blades, realistic nacelles, minimal haze",
    "large photovoltaic farm, endless rows of blue PV panels, tracked mounting racks, clean gravel paths, cable trays, realistic inverters, midday sun",
    "massive concrete hydroelectric dam, spillway gates, turbulent discharge water, mist, safety railings, mountain backdrop, overcast soft light",
    "linemen performing night maintenance on transmission tower, bucket truck, headlamps, portable work lights casting rim light, reflective safety vests, visible harnesses, wet asphalt after rain",
    "wind turbines on grassland, modern wind power station, tall white turbine, clear sky, sunlight, realistic, clean composition, high detail, cinematic lighting",
]

FIXED_NEGATIVE_PROMPT = (
    "cartoon, CGI, illustration, painting, anime, over-saturated, over-sharpened, blurry, soft-focus, "
    "noise, grainy, jpeg artifacts, banding, chromatic aberration, halos, lens dirt, water spots, "
    "duplicate structures, warped geometry, distorted text, gibberish signage, misaligned labels, "
    "deformed faces, deformed hands, extra limbs, floating objects"
)

GENERATION_MODELS = ["sd15-electric", "sd15-electric-specialized", "ssd1b-electric"]
SCORING_MODELS = ["electric-score-v1", "electric-score-v2"]

MODEL_COLORS = {
    "sd15-electric": "#1f4e79",
    "sd15-electric-specialized": "#d97706",
    "ssd1b-electric": "#0f766e",
    "electric-score-v1": "#64748b",
    "electric-score-v2": "#b91c1c",
}


@dataclass(slots=True)
class PromptSuite:
    prompts: list[str]
    negative_prompt: str
    generation_models: list[str]
    scoring_models: list[str]
    seed: int


@dataclass(slots=True)
class FigureSpec:
    filename: str
    title: str
    section: str
    source: str

    def to_manifest_record(self) -> dict[str, str]:
        return asdict(self)


def build_prompt_suite() -> PromptSuite:
    return PromptSuite(
        prompts=list(FIXED_GENERATION_PROMPTS),
        negative_prompt=FIXED_NEGATIVE_PROMPT,
        generation_models=list(GENERATION_MODELS),
        scoring_models=list(SCORING_MODELS),
        seed=42,
    )


def expected_figure_inventory() -> list[FigureSpec]:
    prompt_specs = [
        FigureSpec(
            filename=f"{index + 2:02d}_generation_prompt_{index + 1:02d}_model_compare.png",
            title=f"Prompt {index + 1} 生成结果对比图",
            section="生成结果对比",
            source="docs/image",
        )
        for index in range(len(FIXED_GENERATION_PROMPTS))
    ]
    trailing_specs = [
        FigureSpec("10_generation_training_loss_curve.png", "生成模型训练损失曲线", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("11_generation_lr_decay_curve.png", "生成模型学习率衰减曲线", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("12_generation_progress_throughput_curve.png", "生成模型训练进度与吞吐率图", "生成模型训练结果分析", "model/training/generation/sd15-electric-specialized-v2/training.log"),
        FigureSpec("13_scoring_pipeline_baseline_vs_student.png", "主流评分模型组合基线与自训练评分器结构对比", "评分模型设计", "python-ai-service/app/services/scoring_service.py"),
        FigureSpec("14_scoring_v2_training_loss_curve.png", "自训练评分模型训练损失曲线", "评分模型训练结果分析", "model/training/scoring/electric-score-v2/history.json"),
        FigureSpec("15_scoring_v2_lr_curve.png", "自训练评分模型学习率曲线", "评分模型训练结果分析", "python-ai-service/training/scoring/config.py"),
        FigureSpec("16_scoring_v2_progress_curve.png", "自训练评分模型训练进度图", "评分模型训练结果分析", "model/training/scoring/electric-score-v2/history.json"),
        FigureSpec("17_scoring_v2_regression_mae.png", "自训练评分模型各维度回归误差图", "评分模型训练结果分析", "model/scoring/electric-score-v2/metrics.json"),
        FigureSpec("18_yolo_training_loss_curve.png", "YOLO 辅助检测训练损失曲线", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("19_yolo_lr_curve.png", "YOLO 辅助检测学习率曲线", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("20_yolo_progress_throughput_curve.png", "YOLO 辅助检测训练进度与吞吐率图", "辅助检测模型训练结果分析", "model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv"),
        FigureSpec("21_yolo_detection_metrics.png", "YOLO 辅助检测指标图", "辅助检测模型训练结果分析", "model/scoring/electric-score-v2/metrics.json"),
        FigureSpec("22_average_total_score_compare.png", "固定 Prompt 集平均总分对比图", "实验结果对比", "docs/image"),
        FigureSpec("23_dimension_gain_compare.png", "各维度增益对比图", "实验结果对比", "docs/image"),
        FigureSpec("24_total_score_boxplot.png", "总分箱线图", "实验结果对比", "docs/image"),
        FigureSpec("25_multidim_score_heatmap_v1.png", "多维度评分热力图（基线评分器）", "实验结果对比", "docs/image"),
        FigureSpec("26_multidim_score_heatmap_v2.png", "多维度评分热力图（自训练评分器）", "实验结果对比", "docs/image"),
        FigureSpec("27_prompt_win_count_compare.png", "固定 Prompt 集获胜次数统计图", "实验结果对比", "docs/image"),
        FigureSpec("28_generation_time_compare.png", "生成耗时对比图", "实验结果对比", "docs/image"),
    ]
    return [
        FigureSpec("01_generation_prompt_overview_grid.png", "固定 Prompt 集生成结果总览", "生成结果对比", "docs/image"),
        *prompt_specs,
        *trailing_specs,
    ]
