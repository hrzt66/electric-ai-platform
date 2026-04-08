# Electric Specialized Generator And Human-Aligned Scorer V3 Design

**Date:** 2026-04-07

## Goal

在当前这台 `RTX 3060 Laptop GPU 6GB` + `16GB RAM` 的 Windows 本机环境上，交付两套新的可落地能力，并无缝接入现有 Electric AI Platform：

1. 一个真正偏电力行业场景的专用生成模型，而不是继续直接使用通用大众底模。
2. 一个更贴近人类主观判断、同时保留电力行业物理约束的四维评分模型。

## Final Decision

最终采用以下组合方案：

- 生成侧：
  - 最终部署模型继续选择 `Stable Diffusion 1.5` 体系。
  - 训练方式采用“电力行业数据集 + 本机电力图片 + LoRA 微调 + 权重合并”的路线。
  - 最终交付为独立部署目录 `G:\electric-ai-runtime\models\generation\sd15-electric-specialized`。
- 评分侧：
  - 新建 `electric-score-v3`，采用“强教师模型蒸馏 + 电力部件检测与规则约束 + 轻量学生模型推理”的混合架构。
  - 最终交付目录为 `G:\electric-ai-runtime\models\scoring\electric-score-v3`。
- 平台侧：
  - 前端继续保留旧模型可选。
  - 新生成模型与新评分模型都作为独立条目接入模型中心与生成工作台。

## Why This Decision

### 为什么最终部署不用更高版本生成模型

用户允许我自行决策，并且优先级是“生成质量和行业专属性优先，可以接受长时间训练”。但在这台机器上，最终可长期稳定部署的模型仍然应该优先考虑 `SD1.5` 体系，原因如下：

- 当前硬件仅有 `6GB` 显存，`SDXL`、`SD3.x` 或更大模型在本机训练和日常推理上都更容易出现显存不足、训练中断、推理不稳的问题。
- `Diffusers` 官方文档明确把 LoRA 作为更低显存、更小权重体积的训练方式，并支持将 LoRA 融合到基础模型以提升推理效率。
- 现有仓库已经围绕 `sd15-electric` 形成完整运行时链路，改造成本最低，部署风险也最低。

因此，本设计采用“训练时尽量借助更强公开能力做教师与校准，部署时选择更稳的 SD1.5 专用模型”的策略。

## Data Strategy

### 数据来源

训练语料将由三部分混合构成：

1. 公开电力场景数据集
2. 用户本机已有电力图片
3. 运行时目录中已下载或已整理过的外部电力图像

预计纳入的公开数据源包括：

- `InsPLAD`
  - 电力线路资产巡检数据集，公开仓库描述为包含 `10,607` 张高分辨率无人机图像。
- `TTPLA`
  - 输电塔与电力线的航拍检测/分割数据集。
- `PLD-UAV`
  - 无人机场景下的城市场景与山地场景电力线数据集。
- `Power Equipment Image Dataset`
  - Hugging Face 数据集卡标记为 `MIT` 许可，可补充变电站和电力设备图像。

本机数据源包括：

- `E:\毕业设计\源代码\Project\static`
- `G:\electric-ai-runtime\datasets\external\power_equipment_substation\...`

### 数据清洗原则

所有图片在进入训练集之前都必须经过统一的清洗管线：

- 去损坏文件
- 去零字节文件
- 去近重复图
- 过滤明显非电力场景图
- 统一扩展名与路径规范
- 生成标准化 caption 与场景标签
- 进行类别均衡，避免某一类场景过度主导模型

### 目标场景覆盖

生成模型和评分模型都必须覆盖下列几类场景，且不能只偏单一类：

- 变电站设备
- 输电塔 / 导线 / 绝缘子
- 风电场
- 光伏场站
- 电力巡检与综合工业电力场景

## Generation Model Design

### 最终模型名称

- 运行时内部名称：`sd15-electric-specialized`
- 展示名称：`Stable Diffusion 1.5 Electric Specialized`

### 训练形式

采用两阶段方案：

#### 阶段 1：行业通用域适配

目标是让模型先学会“电力行业视觉语义”：

- 电力设备外观
- 变电站结构
- 输电塔/导线/绝缘子关系
- 风机、光伏板、升压站、巡检视角等常见语义

这一阶段使用清洗后的混合电力图像与标准化 caption，训练 `SD1.5 LoRA`，主要更新 UNet 的 LoRA 层，必要时再启用文本编码器 LoRA。

#### 阶段 2：高价值样本强化

目标是强化更符合人类感知、且更贴近业务需要的图像质量：

- 对关键类别样本进行过采样
- 对低质量自动 caption 做人工规则修正
- 对局部强场景词做 prompt 模板增强
- 结合评分器教师信号筛选更优训练样本

### 训练产物

训练过程中保留三类产物：

- 中间 LoRA checkpoint
- 训练配置与指标日志
- 最终融合后的可部署模型目录

最终部署只使用融合后的独立模型目录，不要求前端或运行时额外感知 LoRA。

### 训练路径设计

新增以下运行时目录：

```text
G:\electric-ai-runtime
├─ datasets
│  ├─ generation-v3
│  │  ├─ raw
│  │  │  ├─ public
│  │  │  ├─ local
│  │  │  └─ external
│  │  ├─ curated
│  │  ├─ captions
│  │  └─ manifests
├─ models
│  ├─ generation
│  │  ├─ sd15-electric
│  │  ├─ sd15-electric-specialized
│  │  └─ unipic2-kontext
│  └─ scoring
│     ├─ electric-score-v2
│     └─ electric-score-v3
└─ training
   ├─ generation
   │  └─ sd15-electric-specialized
   └─ scoring
      └─ electric-score-v3
```

### 训练代码组织

在仓库中新增专门训练目录，而不是把训练逻辑散落在运行时中：

- `python-ai-service/training/generation/...`
- `python-ai-service/training/scoring/...`
- `python-ai-service/scripts/train_*.py`

生成训练至少包含：

- 数据索引构建
- 清洗与 dedupe
- caption 标准化
- LoRA 训练
- LoRA 融合
- 样例出图与对比评估

### 推理接入方式

运行时接入不替换旧模型，而是新增模型工厂与模型清单条目：

- `python-ai-service/app/runtimes/runtime_registry.py`
- `python-ai-service/scripts/download_models.py`
- `services/model-service/repository/model_repository.go`

前端继续沿用当前的模型选择器：

- `web-console/src/components/workbench/ParameterPanel.vue`

## Scoring Model Design

### 最终模型名称

- 运行时内部名称：`electric-score-v3`
- 展示名称：`Electric Score V3 (Human-Aligned)`

### 目标

新评分模型不是简单替换一个轻量 backbone，而是把“人类偏好”与“电力行业约束”结合：

- 既要更像人类对图像好坏的判断
- 又不能失去电力场景对结构合理性的约束

### 保留的四个维度

仍然保留现有四维度，不改变业务含义：

- `visual_fidelity`
- `text_consistency`
- `physical_plausibility`
- `composition_aesthetics`

总分继续使用现有业务权重：

- `visual_fidelity = 0.21`
- `text_consistency = 0.37`
- `physical_plausibility = 0.24`
- `composition_aesthetics = 0.18`

### 评分器架构

#### 1. 强教师层

使用公开、已验证的人类偏好模型与指标作为教师信号：

- `PickScore`
  - 用于 prompt-image 偏好对齐与人类主观一致性监督。
- `HPS v2.1`
  - 用于增强人类偏好预测稳定性。
- `ImageReward`
  - 作为已有文本图像对齐基线保留。

这些教师模型不会全部直接作为线上最终推理路径，而主要用于：

- 训练集软标签生成
- 学生模型蒸馏
- 回归标定

#### 2. 电力领域约束层

保留并升级电力部件结构约束：

- 继续使用 YOLO 检测电力部件
- 扩展部件类别
- 加入 prompt 实体词到检测结果的覆盖关系
- 引入导线、绝缘子、杆塔、变压器、母线、断路器、风机、光伏板等实体约束

这一层主要负责：

- `physical_plausibility`
- `text_consistency` 中的实体覆盖部分

#### 3. 轻量学生层

最终线上仍然使用轻量学生模型做主推理，以保证：

- 本机推理速度
- 显存可控
- 批量评分可落地

但学生模型的监督来源改为：

- 强教师偏好分数
- 电力领域检测特征
- 现有四维业务目标
- 人工规则标定

### text_consistency 的新定义

`text_consistency` 不再主要依赖单一 ImageReward 分数，而是由三部分融合得到：

1. 人类偏好对齐分数
2. prompt 中电力实体词是否真的在图中出现
3. prompt 场景词与整体场景风格是否一致

这样能更贴近“用户写了什么，图里有没有，而且像不像人类会认同的结果”。

### physical_plausibility 的新定义

`physical_plausibility` 以电力结构合理性为主：

- 导线是否存在合理连接关系
- 绝缘子/杆塔/横担是否出现合理组合
- 变电站设备是否像真实工业设备而不是抽象拼贴
- 风电、光伏、升压站等新能源场景是否具备基本物理语义

### composition_aesthetics 的新定义

`composition_aesthetics` 不只依赖通用美学分数，还加入“人类更容易接受的工业构图”校准：

- 主体清晰
- 视角稳定
- 杂乱度可控
- 没有明显 AI 错位

## Training And Calibration Plan

### 评分模型训练样本构建

训练集不只来自静态标注图，还会加入“生成任务回流样本”：

- 用现有生成模型和新生成模型对标准电力 prompt 生成图像
- 用教师模型与规则产生软标签
- 形成“prompt + image + 四维标签 + 总分标签”的训练样本

这样评分器会更贴近本系统真正会生成出来的图，而不是只懂公开 benchmark。

### 训练策略

评分模型分三层训练：

1. 电力实体检测器训练/微调
2. 强教师信号离线打标
3. 轻量学生模型蒸馏与校准

### 分数校准

所有输出最终强制落到 `[0, 100]`。

并保留前端等级展示所需的区间：

- `0-30`: `E`
- `30-50`: `D`
- `50-70`: `C`
- `70-85`: `B`
- `85-100`: `A`

前端继续显示数字分数，同时显示字母 chip。

## Platform Integration Design

### 模型中心

模型中心新增两条注册项：

- `sd15-electric-specialized`
- `electric-score-v3`

种子数据通过 `model-service` 维护，保证前端模型中心可见。

### Python Runtime

Python 运行时新增两类能力：

- 新生成模型 runtime builder
- 新评分 bundle runtime

并保持旧能力可继续使用：

- `sd15-electric`
- `unipic2-kontext`
- `electric-score-v1`
- `electric-score-v2`

### 前端

前端保持当前交互形式，不重做工作台结构：

- 生成模型下拉框新增专用模型
- 评分模型下拉框新增 `electric-score-v3`
- 历史详情、工作台雷达图继续展示四维数值
- 等级 chip 继续显示

### 结果可追踪性

每次任务都需要记录：

- 使用的生成模型
- 使用的评分模型
- prompt
- seed
- steps
- guidance scale
- 四维分数
- 总分

保证新旧模型可横向比较。

## Validation

### 生成模型验收

至少覆盖以下验收方式：

- 固定标准 prompt 集对比
- 与 `sd15-electric` 的 A/B 结果对比
- 电力实体覆盖率提升
- 人类主观筛查结果更稳定

### 评分模型验收

至少覆盖以下验收方式：

- 与 `electric-score-v2` 的离线对比
- 对同一 prompt 的多图排序更贴近人工判断
- 对明显错误图像给出更低 `physical_plausibility`
- 对 prompt 不匹配图像给出更低 `text_consistency`

## Risks

### 风险 1：本机长时间训练不稳定

缓解：

- 优先 LoRA 而不是全量微调
- 分阶段保存 checkpoint
- 所有训练脚本支持断点恢复

### 风险 2：本机图片质量参差不齐

缓解：

- 必须做质量过滤和近重复过滤
- 低质量图不能直接进入高质量阶段训练

### 风险 3：评分器过度依赖教师，失去业务可解释性

缓解：

- 维持电力实体检测与规则支路
- 把教师分数作为监督而不是唯一线上推理来源

## Non-Goals

本次设计明确不做：

- 不在当前机器上训练全量 SDXL / SD3.x 并作为最终部署模型
- 不移除旧模型
- 不上传 GitHub
- 不把所有评分逻辑替换成单一黑盒 VLM

## Sources

- [Hugging Face Diffusers DreamBooth docs](https://huggingface.co/docs/diffusers/main/en/training/dreambooth)
- [Hugging Face Diffusers Text-to-image training docs](https://huggingface.co/docs/diffusers/v0.35.0/en/training/text2image)
- [Hugging Face Diffusers LoRA docs](https://huggingface.co/docs/diffusers/v0.23.0/en/training/lora)
- [InsPLAD official repository](https://github.com/andreluizbvs/InsPLAD)
- [PLD-UAV official repository](https://github.com/SnorkerHeng/PLD-UAV)
- [TTPLA official repository](https://github.com/R3ab/ttpla_dataset)
- [Power Equipment Image Dataset card](https://huggingface.co/datasets/sxiong/Power-equipment-image-dataset/blob/main/README.md)
- [PickScore model card](https://huggingface.co/yuvalkirstain/PickScore_v1)
- [Pick-a-Pic paper](https://arxiv.org/abs/2305.01569)
- [HPSv2 official repository](https://github.com/tgxs002/HPSv2)
- [HPSv2 paper](https://arxiv.org/abs/2306.09341)
- [TIFA official repository](https://github.com/Yushi-Hu/tifa)

## Status

用户已在对话中明确授权“之后都自己决策”，因此本设计按“默认批准并继续实施”的方式推进。

用户另有明确要求：

- 训练好的模型必须放到 `G:\electric-ai-runtime`
- 暂时不要上传到 git 或 GitHub
- 前端继续保留旧模型可选
