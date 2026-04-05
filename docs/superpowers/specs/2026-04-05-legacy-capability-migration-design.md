# 电力 AI 平台旧能力迁移与真实运行时重建设计

> 设计日期：2026-04-05
> 子项目目标：在保持当前 Go 微服务边界不变的前提下，把旧项目中的真实图像生成、真实四维评分、完整前端工作台与历史检索能力迁移到当前新架构，并在 Windows 原生环境中跑通。

## 1. 背景与问题定义

当前仓库已经完成第一阶段 vertical slice，具备以下基础：

- `gateway-service`、`auth-service`、`model-service`、`task-service`、`asset-service`、`audit-service` 六个 Go 服务骨架
- `python-ai-service` 的最小 mock 生成链路
- `web-console` 的登录、仪表盘、提交任务最小闭环
- Docker 提供的 MySQL 与 Redis 开发环境

但与旧项目相比，现状仍有两个决定性交付缺口：

1. 前端仅有最小表单式交互，缺少旧项目已有的完整参数面板、结果预览、四维评分可视化、历史筛选与详情复看能力。
2. 后端生成与评分仍以 mock 占位为主，没有把旧项目中的真实 Stable Diffusion / UniPic 生成链路、ImageReward / LAION-Aesthetics / CLIP-IQA 评分链路迁入新架构。

本设计的目的不是“修饰现有演示版”，而是完成一次真正的能力回迁与工业化重构：旧项目中的模型与算法仍由 Python 脚本承载，平台化职责交给 Go 微服务，前端升级为完整工作台。

## 2. 设计目标

### 2.1 总体目标

构建一个可在当前机器上实际运行的完整项目版本，满足以下条件：

- 保持当前微服务边界，不退回单体架构
- 真实图像生成与真实四维评分均由 Python 运行时完成
- 前端具备完整工作台体验，而非最小演示页
- 历史数据、任务状态、评分结果均能落库、查询、复看
- 整套系统以 Windows 原生方式运行，Python 使用 `G:\miniconda3`

### 2.2 必须达成的结果

- 支持真实生成模型下载、管理、运行
- 支持真实评分模型下载、管理、运行
- 支持生成任务创建、状态轮询、错误展示
- 支持图片结果持久化、评分结果持久化、历史检索与详情聚合
- 支持完整前端页面：登录、生成工作台、历史中心、模型中心、任务审计基础视图
- 支持以 `G:` 盘为统一模型与输出目录，不在其他盘落模型

## 3. 范围定义

### 3.1 本期范围

本期实现以下子目标：

- 将旧项目生成参数体系迁回新平台
- 将旧项目前端“生成 + 历史 + 评分”主体验迁回并重组
- 将旧项目真实评分模型链迁回 `python-ai-service`
- 将真实生成模型接入 `python-ai-service`
- 补齐 Go 微服务间的任务回写、结果保存、聚合查询接口
- 在 Windows 原生环境中跑通真实生成、真实评分、前端查询闭环

### 3.2 本期不做

- Kubernetes 与生产级容器化 GPU 方案
- 多 worker 并发 GPU 调度
- 对象存储正式替换本地文件系统
- 完整报表导出与批量实验管理的高级功能
- 大规模多用户生产级权限系统扩展

## 4. 约束与运行环境

### 4.1 硬件与系统约束

- 操作系统：Windows
- GPU：`NVIDIA GeForce RTX 3060 6GB`
- CUDA 驱动：以本机已安装版本为准
- Python 管理：`G:\miniconda3`

### 4.2 运行形态约束

- `web-console`、所有 Go 服务、`python-ai-service` 均以 Windows 原生方式启动
- MySQL 与 Redis 可继续通过 Docker 提供
- 所有真实模型均由 Python 脚本调用，不在 Go 服务内部嵌入模型逻辑
- 运行时模型、缓存、输出统一落到 `G:` 盘新目录

### 4.3 模型目录约束

统一使用：

- `G:\electric-ai-runtime\hf-home`
- `G:\electric-ai-runtime\models\generation`
- `G:\electric-ai-runtime\models\scoring`
- `G:\electric-ai-runtime\outputs\images`
- `G:\electric-ai-runtime\logs`
- `G:\electric-ai-runtime\tmp`

所有 Hugging Face 缓存、模型下载和生成图片输出都必须收敛到上述目录。

## 5. 总体架构

迁移后的系统保持现有微服务边界：

```text
Web Console
    |
    v
Gateway Service
    |
    +------------------+------------------+------------------+------------------+------------------+
    |                  |                  |                  |                  |                  |
    v                  v                  v                  v                  v                  v
Auth Service      Model Service      Task Service      Asset Service      Audit Service      Static Access
                                           |
                                           v
                                         Redis
                                           |
                                           v
                                  Python AI Service
                                           |
                     +---------------------+----------------------+
                     |                                            |
                     v                                            v
            Generation Runtimes                           Scoring Runtimes
      (SD1.5 / UniPic2 via Python)         (ImageReward / LAION-Aesthetics / CLIP-IQA)

MySQL: task, asset, model, audit tables
G:\electric-ai-runtime: models, caches, outputs, logs
```

设计原则：

- Go 服务负责平台化职责，不负责模型执行
- Python 服务负责真实模型下载、加载、推理、显存治理
- 前端面向平台用户，不再沿用最小化演示布局
- 任何任务状态变化都要可追踪、可落库、可审计

## 6. 服务职责调整

### 6.1 Gateway Service

保留统一入口职责，并新增以下转发能力：

- `/api/v1/assets/*` 转发到 `asset-service`
- `/api/v1/audit/*` 转发到 `audit-service`
- `/files/images/*` 或等价静态访问路径统一代理到图片输出目录

不承担模型逻辑，不直接操作业务表。

### 6.2 Task Service

从“只会创建任务”升级为完整任务中心，负责：

- 创建生成任务
- 查询任务详情与任务状态
- 接收 Python 运行时回写的状态更新
- 记录错误摘要、重试次数、阶段信息
- 为前端提供轮询接口

任务状态必须支持：

- `queued`
- `preparing`
- `downloading`
- `generating`
- `scoring`
- `persisting`
- `completed`
- `failed`

### 6.3 Asset Service

从“只会保存结果”升级为资产中心，负责：

- 保存生成图片元数据
- 保存 Prompt 参数
- 保存四维评分与总分
- 提供历史分页查询
- 提供多条件筛选
- 提供单图详情聚合接口
- 为前端生成结果页和历史页提供统一数据结构

### 6.4 Model Service

负责模型侧控制平面，不执行模型本身，提供：

- 可用模型列表
- 模型类型、运行状态、展示名称
- 默认参数模板
- 电力场景 Prompt 模板
- 模型可用性标记

模型服务需要区分：

- `available`
- `downloading`
- `unavailable`
- `experimental`

### 6.5 Audit Service

负责记录关键运行事件，至少覆盖：

- 任务创建
- 模型下载开始 / 完成 / 失败
- 模型加载开始 / 完成 / 失败
- 图像生成开始 / 完成 / 失败
- 图像评分开始 / 完成 / 失败
- 结果写库成功 / 失败

### 6.6 Python AI Service

升级为真实 AI 运行时中心，负责：

- 消费 Redis 任务或接受内部任务调度
- 下载生成模型与评分模型
- 真实加载和执行生成模型
- 真实加载和执行评分模型
- 管理显存、缓存、临时文件
- 将运行进度、错误和结果回写给 Go 服务

它是唯一可以接触模型权重和深度学习运行时的服务。

## 7. Python 运行时设计

### 7.1 目录结构

建议重构为：

```text
python-ai-service/
  app/
    api/
    core/
    runtimes/
    workers/
    services/
    schemas/
    clients/
    utils/
  scripts/
    download_models.py
    runtime_probe.py
  tests/
```

职责划分：

- `api/`：健康检查、运行时状态、调试接口
- `workers/`：任务消费与执行入口
- `runtimes/`：模型加载、卸载、设备管理、缓存路径
- `services/`：生成服务、评分服务、回写服务
- `clients/`：调用 Go 内部服务的 HTTP 客户端
- `scripts/`：模型下载与环境探测脚本

### 7.2 双入口设计

Python 服务拆成两个入口：

- `app.main`
  - 提供 `GET /health`
  - 提供 `GET /runtime/status`
  - 提供 `GET /runtime/models`
  - 提供必要的内部诊断接口
- `app.worker`
  - 启动 Redis consumer
  - 消费生成任务
  - 执行生成与评分全链路
  - 回写任务状态和资产结果

### 7.3 Python 环境固定方案

统一使用：

- Conda 环境：`G:\miniconda3\envs\electric-ai-py310`
- Python 版本：`3.10`

选择 Python 3.10 的原因：

- 更接近旧项目 UniPic2 Windows 依赖要求
- 对 `flash-attn`、`bitsandbytes`、PyTorch CUDA 轮子兼容性更稳
- 降低 Windows 深度学习依赖组合的不确定性

### 7.4 模型下载与缓存策略

所有模型下载必须走统一脚本 `download_models.py`，不允许业务运行时临时写散路径。

下载策略：

- HF 相关缓存定向到 `G:\electric-ai-runtime\hf-home`
- 生成模型下载到 `G:\electric-ai-runtime\models\generation`
- 评分模型下载到 `G:\electric-ai-runtime\models\scoring`
- 本地已有小权重文件如 `sac+logos+ava1-l14-linearMSE.pth` 应迁入评分目录统一管理

脚本需要支持：

- 指定模型下载
- 全量初始化下载
- 校验文件是否齐全
- 失败可重试
- 生成清晰的下载日志

### 7.5 生成模型策略

本期接入两个真实生成后端：

1. `sd15-electric`
   - 作为必须跑通的真实生成基线
   - 使用 Stable Diffusion 1.5 系链路
   - 优先保证在 RTX 3060 6GB 上真实可运行

2. `unipic2-kontext`
   - 作为高级真实生成后端
   - 通过旧项目中的 UniPic2 代码与脚本接入
   - 允许首次下载时间较长
   - 如果运行时探测不满足条件，必须明确标记为不可用，而不是静默失败

要求：

- 两个后端都是真实生成，不允许使用占位图替代
- UI 必须能区分模型可用性和准备状态

### 7.6 评分模型策略

评分链路全部使用真实模型：

- `ImageReward`：文本一致性主评分
- `LAION-Aesthetics`：构图美学
- `CLIP-IQA / CLIP prompts`：视觉保真度、物理合理性与回退策略

评分结果统一归一化到 `0-100`：

- `visual_fidelity`
- `text_consistency`
- `physical_plausibility`
- `composition_aesthetics`
- `total_score`

默认总分计算：

```text
total_score =
  visual_fidelity * 0.25 +
  text_consistency * 0.30 +
  physical_plausibility * 0.30 +
  composition_aesthetics * 0.15
```

### 7.7 显存治理策略

考虑到本机仅有 `6GB` 显存，运行时必须遵守以下规则：

- 同时只允许一个重 GPU 任务执行
- 生成与评分绝不共驻显存
- 先加载生成模型，生成完成后立即卸载
- 清理 CUDA cache 后再加载评分模型
- 单次批量图数默认限制为小批量
- 所有关键阶段都记录显存相关日志

执行顺序固定为：

1. 领取任务
2. 校验 / 下载模型
3. 加载生成模型
4. 执行生成
5. 落盘图片
6. 卸载生成模型并清显存
7. 加载评分模型
8. 执行评分
9. 回写任务与资产结果
10. 卸载评分模型并清显存

## 8. 任务流与数据流

### 8.1 主流程

```text
前端提交生成请求
  -> gateway-service
  -> task-service 创建 task_jobs
  -> Redis 推送 generate job
  -> python-ai-service worker 消费任务
  -> 更新任务状态为 preparing/downloading/generating/scoring
  -> 真实生成图片并落盘
  -> 真实评分
  -> 回写 asset-service 保存图片、参数、评分
  -> 回写 task-service 标记 completed 或 failed
  -> 回写 audit-service 记录事件
  -> 前端轮询并展示最终结果
```

### 8.2 状态回写方式

Python 运行时不直接写 MySQL，而是调用内部 Go 服务接口：

- 调用 `task-service` 更新任务状态
- 调用 `asset-service` 保存图片与评分
- 调用 `audit-service` 记录事件

原因：

- 保持微服务边界清晰
- 避免 Python 直接耦合多个业务表结构
- 保持审计和校验逻辑集中在 Go 服务

### 8.3 失败处理

失败必须带上阶段信息：

- `download_failed`
- `load_failed`
- `generation_failed`
- `scoring_failed`
- `persist_failed`

`task-service` 保存：

- 当前阶段
- 错误摘要
- 原始错误消息
- 是否允许重试

前端据此展示“失败发生在哪一步”。

## 9. 数据模型调整

### 9.1 task_jobs

在现有基础上补充或强化以下字段语义：

- `job_type`
- `status`
- `payload_json`
- `result_json`
- `error_message`
- `retry_count`
- `created_at`
- `updated_at`

其中：

- `payload_json` 保存完整生成请求参数
- `result_json` 保存最终结果摘要，如图片数量、资产 ID 列表、总耗时

### 9.2 asset_images

继续作为图片主表，至少包含：

- `job_id`
- `image_name`
- `file_path`
- `model_name`
- `status`
- `created_at`

### 9.3 asset_image_prompts

保存：

- `positive_prompt`
- `negative_prompt`
- `sampling_steps`
- `seed`
- `guidance_scale`

如需兼容旧项目参数，还可扩展：

- `width`
- `height`
- `batch_size`
- `sampler_name`

### 9.4 asset_image_scores

保存：

- `visual_fidelity`
- `text_consistency`
- `physical_plausibility`
- `composition_aesthetics`
- `total_score`

### 9.5 audit_task_events

统一记录任务时间线，便于：

- 前端任务日志展示
- 错误追踪
- 论文答辩时说明平台化治理能力

## 10. 接口设计调整

### 10.1 对前端开放的网关接口

至少包含：

- `POST /api/v1/auth/login`
- `GET /api/v1/models`
- `POST /api/v1/tasks/generate`
- `GET /api/v1/tasks/:id`
- `GET /api/v1/tasks/:id/events`
- `GET /api/v1/assets/history`
- `GET /api/v1/assets/:id`
- `GET /files/images/:name`

### 10.2 Python 调用的内部接口

至少包含：

- `POST /internal/tasks/:id/status`
- `POST /internal/assets/generate-result`
- `POST /internal/audit/task-events`

要求：

- 内部接口可以使用服务间密钥或内网鉴权
- 内部接口返回统一结构

## 11. 前端工作台设计

### 11.1 页面结构

前端拆分为以下视图：

- 登录页
- 应用壳布局页
- 生成工作台
- 历史结果中心
- 模型中心
- 任务审计页

### 11.2 生成工作台

迁回并升级旧项目的核心能力：

- 模型选择
- 正向 Prompt
- 负向 Prompt
- Seed
- Steps
- 宽高
- CFG
- 批量数
- 场景模板加载
- 运行中日志提示
- 主图预览
- 多图缩略图切换
- 雷达图
- 四维评分明细
- 总分展示

### 11.3 历史结果中心

迁回旧项目历史页能力，并做平台化重组：

- Prompt 关键词筛选
- 模型筛选
- 尺寸 / 步数 / CFG / seed 筛选
- 四维评分最小值筛选
- 分页
- 卡片式结果浏览
- 详情侧栏或详情弹层
- Prompt 与评分复看

### 11.4 视觉方向

前端不沿用当前最简页面，而采用更完整的控制台布局：

- 左侧导航
- 中央工作区
- 结果与评分并列展示
- 顶部运行状态条
- 更明确的任务状态反馈

目标不是炫技，而是让页面看起来像完整系统，而不是 demo。

## 12. 错误处理与可观测性

### 12.1 错误分层

错误分为三层：

1. Python 运行时错误
2. 任务编排与写库错误
3. 前端展示与交互错误

必须做到：

- 后端不吞错
- 任务表有错误摘要
- 审计表有阶段事件
- 前端能展示阶段级失败信息

### 12.2 运行状态可视化

前端至少展示：

- 当前任务状态
- 当前使用模型
- 当前阶段
- 失败原因
- 是否已完成写库

### 12.3 环境探测

提供 `runtime_probe.py`，在实施前验证：

- CUDA 是否可用
- PyTorch 是否识别 GPU
- 关键依赖是否安装
- `G:` 目录是否可写
- 模型目录是否齐全

## 13. 验证策略

### 13.1 Python 层验证

需要验证：

- 模型下载脚本可执行
- 运行时探测脚本可执行
- SD1.5 真实生成可成功输出图片
- UniPic2 接入路径可被探测与执行
- 真实评分链路可返回四维评分
- 显存清理策略有效

### 13.2 Go 服务验证

需要验证：

- 创建生成任务
- 查询任务状态
- 更新任务状态
- 保存资产结果
- 历史查询与详情聚合
- 审计事件写入
- 网关路由完整

### 13.3 前端验证

需要验证：

- 登录成功
- 生成任务提交通路
- 轮询成功
- 结果可展示
- 历史页可筛选
- 详情页可复看

### 13.4 端到端验收

最小验收路径：

1. 登录系统
2. 选择真实模型
3. 提交生成任务
4. 等待任务经过下载 / 生成 / 评分 / 入库
5. 在生成页看到真实图片和四维评分
6. 在历史页重新检索到该结果并打开详情

## 14. 风险与缓解策略

### 14.1 模型下载过大

风险：初次下载时间长，可能失败。

缓解：

- 通过独立下载脚本分步下载
- 支持断点后重试
- 把“下载中”作为显式任务阶段展示

### 14.2 6GB 显存不足

风险：UniPic2 或评分链在部分阶段可能 OOM。

缓解：

- 严格串行执行
- 生成与评分分阶段加载
- 优先保证 SD1.5 基线路径可跑通
- 对不可运行模型明确标记不可用，而不是假装支持

### 14.3 Windows 深度学习依赖复杂

风险：`flash-attn`、CUDA 轮子、bitsandbytes 兼容性问题。

缓解：

- 固定 Python 3.10
- 固定 Conda 环境
- 固定下载脚本和依赖版本
- 先做 `runtime_probe.py`，再进入业务联调

## 15. 实施顺序

按以下顺序实施，避免返工：

1. 重构 `python-ai-service` 为真实运行时中心
2. 打通 `G:\electric-ai-runtime` 目录、下载脚本、Conda 环境与运行时探测
3. 实现 SD1.5 真实生成与真实评分闭环
4. 接入 UniPic2 并纳入模型中心
5. 扩展 `task-service`、`asset-service`、`audit-service`、`gateway-service`
6. 重做 `web-console` 工作台与历史页
7. 跑通端到端联调与脚本化验证

## 16. 完成标准

只有同时满足以下条件，才算本子项目完成：

- Windows 原生环境可启动所有必要服务
- Python 使用 `G:\miniconda3` 的固定环境
- 所有模型与输出统一放在 `G:` 指定目录
- 至少一个真实生成模型稳定跑通
- 真实评分链稳定跑通
- Go 服务可完成任务、资产、审计闭环
- 前端具备完整工作台与历史中心
- 结果可以入库、查询、复看
- 具备可重复执行的启动与验证路径

## 17. 结论

本设计选择“保持微服务边界，重建 Python AI 运行时中心”的路线，而不是回退到旧单体或在 Go 服务中嵌入模型逻辑。这样既能最大化保留当前新架构的工业化价值，又能把旧项目中真正重要的生成、评分和工作台能力完整迁回。

该设计是当前仓库从 vertical slice foundation 走向“完整可交付项目”的直接蓝图，适合作为后续实施计划与代码改造的唯一依据。
