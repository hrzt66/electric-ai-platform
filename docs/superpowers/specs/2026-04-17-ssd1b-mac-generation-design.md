# SSD-1B Mac Generation Design

**Date:** 2026-04-17

## Context

当前仓库已经接入两个生成模型：

- `sd15-electric`
- `unipic2-kontext`

在用户这台 `16GB` Apple Silicon Mac 上，`unipic2-kontext` 已经表现出明显的统一内存压力，真实运行中 Python 进程占用接近整机物理内存，并在 worker 重启后反复回收 Redis 中未完成的旧任务。`sd15-electric` 虽然更轻，但用户明确要求新的默认替代方案不要再走 `SD1.5` 体系。

因此，本次目标不是删除现有全部生成能力，而是在不破坏现有链路的前提下，为本机部署增加一个更适合 `macOS + MPS + 16GB unified memory` 的默认生成模型。

## Goal

为 Electric AI Platform 新增一个适合 Apple Silicon Mac 本地部署的非 `SD1.5` 默认生成模型，并完成平台级接入。

本次必须满足：

1. 新增生成模型 `ssd1b-electric`
2. 新模型默认用于前端生成工作台
3. `unipic2-kontext` 继续保留，可在模型选择器中手动切换
4. 默认评分模型继续保持 `electric-score-v1`
5. 清理 Redis 中与第二次 `unipic2-kontext` 生成残留相关的旧消息，避免 worker 重启后反复消费

## Final Decision

本次新增模型采用：

- 运行时内部名称：`ssd1b-electric`
- Hugging Face 模型来源：`segmind/SSD-1B`
- 推理管线：`diffusers.StableDiffusionXLPipeline`

同时保留以下现状：

- `unipic2-kontext` 不删除
- `electric-score-v1` 继续作为默认评分模型

## Why This Decision

### 为什么选 `SSD-1B`

`SSD-1B` 属于 `SDXL` 蒸馏路线，不是 `SD1.5` 体系，画质和语义表达能力整体上更接近用户希望保留的 `UniPic2` 档次，但权重体量和运行压力明显低于 `UniPic2` 这类更大模型。对于 `16GB` Apple Silicon Mac，本地推理的落地风险更低。

### 为什么不直接继续用 `UniPic2`

`UniPic2` 在当前机器上的主要问题不是“能不能启动”，而是“能不能稳定作为日常默认模型”。当前真实日志已经表明：

- 首次加载和编码阶段耗时长
- 统一内存压力大
- 用户中断 worker 后，Redis pending 消息会被重复认领

因此 `UniPic2` 更适合作为保留的实验模型，而不是默认工作流。

### 为什么默认评分不改

用户已明确要求默认评分保持不变，因此前端默认评分、任务默认评分与生成提交流程都继续沿用 `electric-score-v1`。本次新增生成模型不顺带引入评分口径变更，避免把“换模型”和“换评分标准”混在一次改动里。

## Non-Goals

- 不删除 `unipic2-kontext` 代码或模型目录
- 不删除 `sd15-electric` 及其专用训练链路
- 不把默认评分切换为 `electric-score-v2`
- 不在本次实现中训练新的电力行业专用 `SSD-1B` 微调权重
- 不改任务服务、资产服务或审计服务的核心业务协议

## Chosen Approach

### 1. 新增独立 `SSD-1B` Runtime

在 `python-ai-service/app/runtimes/` 中新增一个面向 `StableDiffusionXLPipeline` 的运行时，而不是强行把 `SD15Runtime` 改造成同时承载 `SD1.5` 与 `SDXL`。

这样做的原因是：

- `SD1.5` 与 `SDXL` 的 pipeline 类型不同
- 参数和内存优化策略有差异
- 让 `ssd1b-electric` 拥有独立运行时更容易单测，也不会影响现有 `sd15-electric`

运行时行为约束：

- `cuda` 优先 `float16`
- `mps` 优先 `float16`
- `cpu` 使用 `float32`
- `cuda` 保持现有的 offload / to-device 优先级思路
- `mps` 直接加载到 `mps`
- 开启 attention slicing 与 VAE slicing
- 保留显式 `unload()`，确保模型切换时主动释放资源

### 2. 在 Runtime Registry 中把 `ssd1b-electric` 注册为正式生成模型

`python-ai-service/app/runtimes/runtime_registry.py` 中增加新的 runtime factory，并让模型中心探针能够识别本地目录 `model/generation/ssd1b-electric`。

当前 registry 已经采用“同一时刻只有一个活跃生成模型”的策略，这对 Mac 本机环境是有利的。`ssd1b-electric` 接入后继续沿用该策略：

- 当前活跃模型切换到新模型时，释放前一个生成 runtime
- `unipic2-kontext` 仍保留，但不会与 `ssd1b-electric` 同时常驻内存

### 3. 扩展模型下载与模型中心注册

需要同时更新：

- `python-ai-service/scripts/download_models.py`
- `services/model-service/repository/model_repository.go`

更新后平台会把 `ssd1b-electric` 作为新的 generation model 条目暴露给：

- 模型中心
- 生成工作台
- 运行时探针

`unipic2-kontext` 仍保留为可选项，状态建议继续标记为 `experimental`。

### 4. 前端默认生成模型切到 `ssd1b-electric`

`web-console/src/views/GenerateView.vue` 中：

- 默认 `model_name` 改成 `ssd1b-electric`
- 默认 `scoring_model_name` 继续保持 `electric-score-v1`

如果后端模型列表可用，前端仍优先使用后端返回的模型目录；如果模型列表尚未加载完成，前端表单默认值也应该直接指向 `ssd1b-electric`。

### 5. 只清理 Redis 中和第二次失败生成相关的残留任务

当前已知残留消息对应：

- stream: `stream:generate:jobs`
- message id: `1776437759795-0`
- job id: `2`
- model: `unipic2-kontext`

需要对 Redis 做一次定向清理，目标是：

- 删除这条 stream message
- 确认 pending 中不再保留这条旧记录

本次只清理这条已知残留，不批量删除整个 stream，避免误伤其它任务。

## Component Changes

预计变更边界如下：

- 新增：
  - `python-ai-service/app/runtimes/ssd1b_runtime.py`
  - 对应 Python 单测文件
- 修改：
  - `python-ai-service/app/runtimes/runtime_registry.py`
  - `python-ai-service/scripts/download_models.py`
  - `python-ai-service/tests/test_runtime_registry.py`
  - `python-ai-service/tests/test_runtime_settings.py`
  - `services/model-service/repository/model_repository.go`
  - 相关 Go 单测
  - `web-console/src/views/GenerateView.vue`
  - 相关前端单测

## Data Flow

新模型接入后的生成链路保持现有平台模式：

1. 前端生成页默认提交 `model_name=ssd1b-electric`
2. task service 创建任务并写入 Redis stream
3. Python worker 从 `stream:generate:jobs` 消费任务
4. runtime registry 构造 `ssd1b-electric` 对应 runtime
5. runtime 使用 `StableDiffusionXLPipeline` 出图并写入 `model/image`
6. 评分仍然走既有默认 `electric-score-v1`
7. 任务状态与审计事件继续按现有服务链路回传到前端

## Error Handling

- `ssd1b-electric` 模型目录不存在时，运行时应维持现有错误暴露方式，不静默退回到其它模型
- `mps` 环境下如果 pipeline 加载失败，不自动退回 `cpu`，避免把内存或兼容性问题伪装成“只是变慢”
- Redis 清理只执行针对单条 message id 的删除与确认，不做全量 stream 清空
- 前端如果拿不到模型列表，默认表单值仍保留 `ssd1b-electric`，但真正提交失败时继续由现有错误提示链路承接

## Testing Plan

实现时先补测试，再改代码。

测试覆盖至少包括：

1. Python runtime
   - `ssd1b-electric` 能从 settings 指向的目录构造 runtime
   - registry 能正确缓存、切换并释放 `ssd1b-electric`
   - `SSD-1B` runtime 在 `mps` 下走 `to("mps")`
   - `SSD-1B` runtime 在 `mps` 下生成器设备与 dtype 选择符合预期

2. Manifest / probe
   - 下载清单包含 `ssd1b-electric`
   - 运行时探针能展示 `ssd1b-electric`

3. Go model repository
   - 模型种子包含 `ssd1b-electric`
   - 查询模型目录时能返回该模型条目

4. Frontend
   - 生成页默认模型切为 `ssd1b-electric`
   - 默认评分仍然是 `electric-score-v1`
   - 历史/审计等展示逻辑不会因为新增模型名而崩溃

5. Redis cleanup
   - 手工验证 `1776437759795-0` 不再出现在 stream 和 pending 中

## Verification Criteria

满足以下条件才算完成：

- 相关 Python、Go、前端单测通过
- 本机可以成功加载 `ssd1b-electric` 并完成至少一次真实出图
- 默认生成模型为 `ssd1b-electric`
- 默认评分模型仍为 `electric-score-v1`
- `unipic2-kontext` 仍然可见且未被删除
- Redis 中不再残留第二次失败生成对应的旧消息

## Risks

- `SSD-1B` 虽然明显轻于 `UniPic2`，但仍然属于 `SDXL` 路线，在 `mps + 16GB unified memory` 上不能等同于“毫无压力”
- `mps` 下的 `float16` 兼容性仍依赖当前 PyTorch / diffusers 组合，可能需要保留已有的 best-effort 清理策略
- 如果未来要把 `SSD-1B` 真正做成电力行业专用模型，还需要单独规划微调与权重管理，本次只做通用底模接入
