# Thesis Figure Package Design

**Date:** 2026-04-18

## Goal

为毕业设计正文准备一套可直接插入论文的高分辨率图表与对比拼图，完整覆盖：

- 生成模型同 prompt、同 seed 的结果对比
- 生成模型训练过程证据
- 主流评分模型组合基线与自训练评分模型的结构与结果对比
- 自训练评分模型与 YOLO 辅助检测分支的训练证据
- 固定 prompt 集上的量化评估统计图

最终产物必须直接落到仓库内 `docs/image/`，并具备统一中文标题、中文坐标轴、统一配色和论文插图级排版。

## Scope

本设计覆盖：

- 固定 8 个 prompt 的生成结果采样与对比拼图
- 3 个生成模型的公平对比
- `electric-score-v1` 与 `electric-score-v2` 两套评分链路的结果对比
- 生成模型训练日志图表抽取
- 自训练评分模型训练记录图表抽取
- YOLO 辅助检测训练记录图表抽取
- 论文插图级命名、目录、清单和样式规范

本设计不覆盖：

- 新训练一版模型以补齐缺失日志
- 使用 `unipic2-kontext` 参与本次论文主对比
- 修改现有评分权重或重写评分逻辑
- 重新采集新的公开数据集

## Fixed Experiment Setup

### Generation Model Set

本次论文主对比只使用以下 3 个生成模型：

- `sd15-electric`
- `sd15-electric-specialized`
- `ssd1b-electric`

明确排除：

- `unipic2-kontext`

排除原因：

- 用户已明确要求“除了 unipic2”
- 论文主对比优先保证三组模型在当前仓库内可稳定复现、可统一参数和可直接进入统计分析

### Scoring Model Set

本次论文评分对比分成两条链路：

- `electric-score-v1`
  - 论文表述为“主流评分模型组合基线”
  - 实际组成：`ImageReward + CLIP-IQA + Aesthetic Predictor`
- `electric-score-v2`
  - 论文表述为“自训练电力领域评分模型”
  - 实际形态：轻量四维回归模型 + YOLO 辅助检测特征

### Fixed Inference Parameters

所有生成对比默认使用统一参数：

- `seed = 42`
- `width = 512`
- `height = 512`
- `num_images = 1`
- `steps = 20`
- `guidance_scale = 7.5`

这组参数与当前前端工作台默认值兼容，可最大程度减少论文对比与平台真实运行逻辑之间的偏差。

### Fixed Prompt Set

固定测试集由“前端 7 条精选正向提示词 + 1 条默认正向提示词”组成，共 8 条：

1. `modern electrical substation yard, high-voltage breakers and transformers, stainless steel busbars, gravel ground, safety fencing, warning signage sharp and legible, tidy cables, cinematic depth of field`
2. `aerial view of steel lattice transmission towers marching across landscape, taut conductors, wide right-of-way, realistic insulators, rolling terrain, clear sky`
3. `grid control room, wall of SCADA screens, operators at desks, LED status panels, cool white lighting, cable management neat, reflective floor, photorealistic optics`
4. `utility-scale wind turbines on gentle hills, aligned rows, late afternoon sun, long shadows, crisp blades, realistic nacelles, minimal haze`
5. `large photovoltaic farm, endless rows of blue PV panels, tracked mounting racks, clean gravel paths, cable trays, realistic inverters, midday sun`
6. `massive concrete hydroelectric dam, spillway gates, turbulent discharge water, mist, safety railings, mountain backdrop, overcast soft light`
7. `linemen performing night maintenance on transmission tower, bucket truck, headlamps, portable work lights casting rim light, reflective safety vests, visible harnesses, wet asphalt after rain`
8. `wind turbines on grassland, modern wind power station, tall white turbine, clear sky, sunlight, realistic, clean composition, high detail, cinematic lighting`

### Fixed Negative Prompt

所有生成任务统一使用以下负向提示词，不允许在模型间单独调整：

`cartoon, CGI, illustration, painting, anime, over-saturated, over-sharpened, blurry, soft-focus, noise, grainy, jpeg artifacts, banding, chromatic aberration, halos, lens dirt, water spots, duplicate structures, warped geometry, distorted text, gibberish signage, misaligned labels, deformed faces, deformed hands, extra limbs, floating objects`

## Figure Narrative

整套论文图按 4 条证据链组织：

1. 生成结果对比链
2. 生成模型训练证据链
3. 评分基线与自训练评分器对比链
4. 自训练评分模型与 YOLO 辅助检测训练证据链

推荐在论文正文中按以下顺序摆放：

1. 先展示 8 prompt 总览拼图，快速给出视觉印象
2. 再展示单 prompt 的细粒度模型对比图
3. 接着展示生成训练曲线，说明专精模型来源
4. 然后展示“主流评分模型组合基线 vs 自训练评分模型”结构图
5. 最后展示量化统计图，支撑结论

## Figure Inventory

### A. 生成结果对比图

必须产出：

- `01_generation_prompt_overview_grid.png`
  - 内容：8 个 prompt × 3 个模型的大总览拼图
  - 作用：作为生成质量对比小节首页总览图
- `02_generation_prompt_01_model_compare.png`
- `03_generation_prompt_02_model_compare.png`
- `04_generation_prompt_03_model_compare.png`
- `05_generation_prompt_04_model_compare.png`
- `06_generation_prompt_05_model_compare.png`
- `07_generation_prompt_06_model_compare.png`
- `08_generation_prompt_07_model_compare.png`
- `09_generation_prompt_08_model_compare.png`
  - 内容：每张图只展示 1 个 prompt 下 3 个模型的横向对比
  - 标注：prompt 编号、模型名、seed、评分器说明

### B. 生成模型训练证据图

数据来源：

- `model/training/generation/sd15-electric-specialized-v2/training.log`

必须产出：

- `10_generation_training_loss_curve.png`
  - 数据：`step_loss`
- `11_generation_lr_decay_curve.png`
  - 数据：`lr`
- `12_generation_progress_throughput_curve.png`
  - 数据：训练步数、累计时间、`it/s`

### C. 评分器结构与训练证据图

必须产出：

- `13_scoring_pipeline_baseline_vs_student.png`
  - 内容：`electric-score-v1` 主流评分模型组合基线 vs `electric-score-v2` 自训练评分器结构图

自训练评分模型训练数据来源：

- `model/training/scoring/electric-score-v2/history.json`
- `model/scoring/electric-score-v2/metrics.json`
- `python-ai-service/training/scoring/config.py`

必须产出：

- `14_scoring_v2_training_loss_curve.png`
  - 数据：`train_loss`
- `15_scoring_v2_lr_curve.png`
  - 数据：固定学习率 `3e-4`
  - 呈现：水平线 + 图注说明“该模型训练未使用学习率衰减调度器”
- `16_scoring_v2_progress_curve.png`
  - 数据：`epoch / 100`
  - 呈现：训练轮次覆盖进度
- `17_scoring_v2_regression_mae.png`
  - 数据：`visual_fidelity / text_consistency / physical_plausibility / composition_aesthetics` 四维 `per_target_mae`

明确说明：

- `electric-score-v1` 作为主流评分模型组合基线，不存在本仓库内可追溯的本地训练日志
- 因此不为 `electric-score-v1` 伪造训练损失、学习率或吞吐率曲线

### D. YOLO 辅助检测训练证据图

数据来源：

- `model/training/scoring/electric-score-v2/yolo-mps-compact-noval/train100/results.csv`
- `model/scoring/electric-score-v2/metrics.json`

必须产出：

- `18_yolo_training_loss_curve.png`
  - 数据：`train/box_loss`、`train/cls_loss`、`train/dfl_loss`
- `19_yolo_lr_curve.png`
  - 数据：`lr/pg0`、`lr/pg1`、`lr/pg2`
- `20_yolo_progress_throughput_curve.png`
  - 数据：`epoch`、累计 `time`
  - 呈现：训练进度与时间演化
- `21_yolo_detection_metrics.png`
  - 数据：`precision`、`recall`、`mAP50`、`mAP50-95`

### E. 固定 Prompt 集统计图

统计对象：

- 3 个生成模型
- 2 套评分链路：`electric-score-v1` 与 `electric-score-v2`
- 固定 8 个 prompt

必须产出：

- `22_average_total_score_compare.png`
  - 内容：各生成模型在 `v1` 与 `v2` 下的平均总分对比
- `23_dimension_gain_compare.png`
  - 内容：`electric-score-v2 - electric-score-v1` 的四维增益对比
- `24_total_score_boxplot.png`
  - 内容：不同模型、不同评分器下总分分布箱线图
- `25_multidim_score_heatmap_v1.png`
  - 内容：`prompt × 维度` 热力图，评分器为 `v1`
- `26_multidim_score_heatmap_v2.png`
  - 内容：`prompt × 维度` 热力图，评分器为 `v2`
- `27_prompt_win_count_compare.png`
  - 内容：固定 8 prompt 下各模型获胜次数统计，分别统计 `v1` 和 `v2`
- `28_generation_time_compare.png`
  - 内容：3 个生成模型的生成耗时对比

## Figure Style System

### Language

所有最终论文插图统一使用：

- 中文标题
- 中文坐标轴
- 中文图例
- 中文图注候选文案

### Visual Mapping

统一配色如下：

- `sd15-electric`：深蓝
- `sd15-electric-specialized`：电力橙
- `ssd1b-electric`：青绿
- `electric-score-v1`：灰蓝
- `electric-score-v2`：深红
- YOLO 辅助检测：墨绿

### Output Format

统一输出：

- 高分辨率 `PNG`
- 白底论文风格
- 适合 A4 页面插图缩放

### Annotation Rules

所有拼图或对比图必须携带必要标注：

- 模型名称
- prompt 编号
- 固定 seed
- 评分器标识（若该图与评分器相关）
- 必要时补充数据来源简注

## Output Layout

所有图表统一输出到：

- `docs/image/generation-comparison/`
- `docs/image/generation-training/`
- `docs/image/scoring-training/`
- `docs/image/evaluation-stats/`
- `docs/image/paper-ready/`

其中：

- 前四个目录保存原始导出图
- `paper-ready/` 保存适合直接插入论文的整理版图

## Figure Manifest

除图片外，还必须输出 1 份清单文件，记录每张图的论文使用信息：

- `docs/image/figure_manifest.json`

每条记录至少包含：

- 文件名
- 中文标题
- 图的用途
- 数据来源
- 推荐插入的小节

## Data Honesty Rules

本次毕业设计图表必须遵守以下真实性约束：

- 不为 `electric-score-v1` 伪造训练曲线
- 不为 `electric-score-v2` 伪造不存在的逐 epoch 吞吐率日志
- 生成训练图只使用 `sd15-electric-specialized-v2` 的真实日志
- YOLO 图只使用真实 `results.csv` 与 `metrics.json`
- 所有统计图必须能追溯回固定 8 prompt 的原始生成结果与评分结果

如果某类指标在现有仓库产物中不存在，则必须以图注或说明文本明确指出，而不是补造数据。

## Acceptance Criteria

本设计完成后的实现产物必须满足：

1. `docs/image/` 下生成完整的论文图包
2. 至少包含 28 张命名规范一致的图
3. 8 个 prompt 的三模型对比图全部可读
4. 评分部分明确展示“主流评分模型组合基线 vs 自训练评分模型”
5. 自训练评分模型与 YOLO 辅助检测都有真实训练证据图
6. 每张图都可追溯到仓库内现有日志、配置、生成结果或评分结果
7. 用户无需手工改标题或重排版即可直接插入毕业设计正文
