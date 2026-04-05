# Legacy Capability Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持当前 Go 微服务边界不变的前提下，把旧项目中的真实图像生成、真实评分、完整工作台和历史检索能力迁入当前仓库，并在 Windows 原生环境中跑通。

**Architecture:** Go 服务继续承担任务中心、资产中心、模型目录、审计和统一网关职责，所有真实模型下载、加载、生成、评分都收敛到 `python-ai-service`。前端改造成完整工作台，通过 gateway 访问统一接口，并把图片、评分、历史、模型状态串成一个闭环。

**Tech Stack:** Go 1.24, Gin, MySQL, Redis Streams, Vue 3, Vite, Pinia, Element Plus, Python 3.10, FastAPI, PyTorch, diffusers, transformers, ImageReward, CLIP, safetensors

---

## 文件结构与职责映射

### Python AI Runtime

- Modify: `python-ai-service/requirements.txt`
  负责补齐真实生成和真实评分所需依赖。
- Create: `python-ai-service/app/core/settings.py`
  统一管理运行目录、服务地址、模型缓存路径、环境变量。
- Create: `python-ai-service/app/core/runtime_paths.py`
  负责确保 `G:\electric-ai-runtime` 下目录存在并输出标准路径。
- Create: `python-ai-service/app/schemas/runtime.py`
  定义运行时状态、模型状态、下载清单等响应结构。
- Modify: `python-ai-service/app/schemas/jobs.py`
  从最小生成请求升级为完整生成任务、状态回写、评分结果结构。
- Create: `python-ai-service/app/clients/task_client.py`
  回写任务状态与错误摘要。
- Create: `python-ai-service/app/clients/asset_client.py`
  回写图片结果和评分结果。
- Create: `python-ai-service/app/clients/audit_client.py`
  写入任务链路审计事件。
- Create: `python-ai-service/app/runtimes/base.py`
  统一定义生成运行时、评分运行时、可用性探测接口。
- Create: `python-ai-service/app/runtimes/runtime_registry.py`
  管理 `sd15-electric`、`unipic2-kontext` 和评分器的注册、探测、加载。
- Create: `python-ai-service/app/runtimes/sd15_runtime.py`
  实现 Stable Diffusion 1.5 真正生成。
- Create: `python-ai-service/app/runtimes/unipic2_runtime.py`
  适配旧项目 UniPic2 代码并提供新接口。
- Create: `python-ai-service/app/runtimes/scorers/image_reward_runtime.py`
  实现文本一致性评分。
- Create: `python-ai-service/app/runtimes/scorers/aesthetic_runtime.py`
  实现审美与构图评分。
- Create: `python-ai-service/app/runtimes/scorers/clip_iqa_runtime.py`
  实现感知质量评分。
- Create: `python-ai-service/app/services/generation_service.py`
  调用具体生成模型并落盘图片。
- Create: `python-ai-service/app/services/scoring_service.py`
  聚合四维评分与总分。
- Create: `python-ai-service/app/services/job_pipeline.py`
  编排 `preparing -> downloading -> generating -> scoring -> persisting` 全链路。
- Create: `python-ai-service/app/workers/job_worker.py`
  消费 Redis Stream 任务。
- Create: `python-ai-service/app/worker.py`
  Worker 进程入口。
- Modify: `python-ai-service/app/main.py`
  保留健康检查，并提供运行时状态与模型状态接口。
- Create: `python-ai-service/scripts/runtime_probe.py`
  探测 CUDA、Python、模型目录和关键包。
- Create: `python-ai-service/scripts/download_models.py`
  按 manifest 下载或校验模型。
- Create: `python-ai-service/tests/test_runtime_settings.py`
  覆盖路径、配置、manifest 行为。
- Create: `python-ai-service/tests/test_job_pipeline.py`
  覆盖状态回写顺序和失败分支。
- Create: `python-ai-service/tests/test_scoring_service.py`
  覆盖四维评分聚合和总分计算。

### Task Service

- Modify: `services/task-service/model/task.go`
  新增阶段、错误摘要、参数摘要、结果引用等字段。
- Modify: `services/task-service/repository/task_repository.go`
  扩展建表、更新状态、查询详情、分页查询。
- Modify: `services/task-service/service/task_service.go`
  创建完整任务、推送 Redis、接收 Python 回写。
- Modify: `services/task-service/controller/task_controller.go`
  新增详情查询、状态回写、列表接口。
- Modify: `services/task-service/router/router.go`
  挂载新路由。
- Modify: `services/task-service/service/task_service_test.go`
  增补任务状态迁移、回写、错误用例。

### Asset Service

- Modify: `services/asset-service/model/asset.go`
  增加 prompt、评分结构、缩略图/原图、模型标识、时间戳。
- Modify: `services/asset-service/repository/asset_repository.go`
  扩展历史分页、筛选、详情聚合查询。
- Modify: `services/asset-service/service/asset_service.go`
  处理结果写入、历史列表、详情返回。
- Modify: `services/asset-service/controller/asset_controller.go`
  提供 `POST /results`、`GET /history`、`GET /history/:id`。
- Modify: `services/asset-service/router/router.go`
  注册历史与详情接口。
- Modify: `services/asset-service/service/asset_service_test.go`
  覆盖查询和聚合结构。

### Audit / Model / Gateway

- Modify: `services/audit-service/model/event.go`
  记录任务阶段、模型阶段、错误摘要。
- Modify: `services/audit-service/repository/audit_repository.go`
  提供事件写入和按任务查询。
- Modify: `services/audit-service/service/audit_service.go`
  统一审计事件入库。
- Modify: `services/audit-service/controller/audit_controller.go`
  增加按任务查询事件接口。
- Modify: `services/model-service/model/model.go`
  提供模型类型、状态、默认参数、提示词模板。
- Modify: `services/model-service/repository/model_repository.go`
  以配置常量返回模型目录。
- Modify: `services/model-service/service/model_service.go`
  组合静态目录和 Python 运行时动态状态。
- Modify: `services/model-service/controller/model_controller.go`
  返回模型列表、单模型状态。
- Modify: `services/gateway-service/router/router.go`
  代理 asset、audit、新 task 接口和静态图片访问。
- Modify: `services/gateway-service/service/proxy_service.go`
  增加静态文件与新服务转发。

### Web Console

- Create: `web-console/src/types/platform.ts`
  统一前端任务、资产、模型、审计类型。
- Create: `web-console/src/api/platform.ts`
  统一封装任务、资产、模型、审计请求。
- Create: `web-console/src/stores/platform.ts`
  管理当前任务、轮询、历史筛选和模型列表。
- Create: `web-console/src/components/AppShell.vue`
  提供统一布局、导航、状态栏。
- Create: `web-console/src/components/workbench/ParameterPanel.vue`
  完整参数面板。
- Create: `web-console/src/components/workbench/ResultPreview.vue`
  结果预览、多图切换、下载。
- Create: `web-console/src/components/workbench/ScoreRadar.vue`
  四维评分雷达图。
- Create: `web-console/src/components/history/HistoryFilters.vue`
  历史筛选。
- Create: `web-console/src/components/history/HistoryTable.vue`
  历史列表。
- Create: `web-console/src/components/history/HistoryDetailDrawer.vue`
  图片详情、评分详情、审计轨迹。
- Modify: `web-console/src/router/index.ts`
  增加工作台、历史中心、模型中心页面路由。
- Modify: `web-console/src/App.vue`
  切换为 shell 入口。
- Modify: `web-console/src/views/DashboardView.vue`
  升级成概览页。
- Modify: `web-console/src/views/GenerateView.vue`
  升级成工作台页。
- Create: `web-console/src/views/HistoryView.vue`
  接入历史中心。
- Create: `web-console/src/views/ModelCenterView.vue`
  展示模型可用性与下载准备状态。
- Create: `web-console/src/views/TaskAuditView.vue`
  展示任务状态和审计时间线。

### Native Scripts / Docs

- Create: `scripts/windows/setup-python-runtime.ps1`
  创建 Python 3.10 环境并安装依赖。
- Create: `scripts/windows/download-runtime-models.ps1`
  下载模型。
- Create: `scripts/windows/start-platform.ps1`
  以原生方式启动 Go 服务、Python API、Python Worker、前端。
- Create: `scripts/windows/smoke-test.ps1`
  提交任务并轮询直到完成。
- Modify: `README.md`
  补充 Windows 原生运行说明。
- Create: `docs/runtime/windows-native-runbook.md`
  补充部署、故障排查、模型目录约束。

## 实施任务

### Task 1: 建立 Python 运行时配置、路径与探测脚本

**Files:**
- Create: `python-ai-service/app/core/settings.py`
- Create: `python-ai-service/app/core/runtime_paths.py`
- Create: `python-ai-service/app/schemas/runtime.py`
- Create: `python-ai-service/scripts/runtime_probe.py`
- Create: `python-ai-service/scripts/download_models.py`
- Create: `python-ai-service/tests/test_runtime_settings.py`
- Modify: `python-ai-service/requirements.txt`

- [ ] **Step 1: 写失败测试，固定运行目录与模型 manifest 行为**

```python
from app.core.settings import Settings


def test_settings_default_to_g_drive_runtime(monkeypatch):
    monkeypatch.delenv("ELECTRIC_AI_RUNTIME_ROOT", raising=False)
    settings = Settings()
    assert str(settings.runtime_root) == r"G:\electric-ai-runtime"
    assert str(settings.output_image_dir).endswith(r"outputs\images")


def test_runtime_probe_reports_missing_models(tmp_path):
    from app.core.runtime_paths import RuntimePaths

    paths = RuntimePaths(tmp_path)
    report = paths.build_probe_report()
    assert report["directories"]["models_generation"]["exists"] is False
```

- [ ] **Step 2: 运行测试确认当前实现缺失**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_runtime_settings.py -v`
Expected: `ModuleNotFoundError` or import failure for `app.core.settings`

- [ ] **Step 3: 实现统一设置与路径对象**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    runtime_root: Path = Path(r"G:\electric-ai-runtime")
    hf_home: Path = runtime_root / "hf-home"
    generation_model_dir: Path = runtime_root / "models" / "generation"
    scoring_model_dir: Path = runtime_root / "models" / "scoring"
    output_image_dir: Path = runtime_root / "outputs" / "images"
```

- [ ] **Step 4: 实现探测脚本和下载 manifest 入口**

```python
def main() -> int:
    report = build_runtime_probe()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


MANIFEST = {
    "sd15-electric": {"repo_id": "runwayml/stable-diffusion-v1-5", "target": "generation"},
    "image-reward": {"repo_id": "THUDM/ImageReward", "target": "scoring"},
}
```

- [ ] **Step 5: 补齐依赖并重新运行测试**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_runtime_settings.py -v`
Expected: `2 passed`

- [ ] **Step 6: 提交这一小批基础设施**

```bash
git add python-ai-service/requirements.txt python-ai-service/app/core python-ai-service/app/schemas/runtime.py python-ai-service/scripts python-ai-service/tests/test_runtime_settings.py
git commit -m "feat: add python runtime settings and probe"
```

### Task 2: 建立 Python 内部客户端与任务编排骨架

**Files:**
- Modify: `python-ai-service/app/schemas/jobs.py`
- Create: `python-ai-service/app/clients/task_client.py`
- Create: `python-ai-service/app/clients/asset_client.py`
- Create: `python-ai-service/app/clients/audit_client.py`
- Create: `python-ai-service/app/services/job_pipeline.py`
- Create: `python-ai-service/app/workers/job_worker.py`
- Create: `python-ai-service/app/worker.py`
- Modify: `python-ai-service/app/main.py`
- Create: `python-ai-service/tests/test_job_pipeline.py`

- [ ] **Step 1: 写失败测试，固定任务状态推进顺序**

```python
def test_pipeline_updates_status_in_order(fake_pipeline):
    fake_pipeline.run(job_id=7)
    assert fake_pipeline.statuses == [
        "preparing",
        "downloading",
        "generating",
        "scoring",
        "persisting",
        "completed",
    ]
```

- [ ] **Step 2: 运行测试确认 pipeline 还不存在**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_job_pipeline.py -v`
Expected: FAIL with missing `JobPipeline`

- [ ] **Step 3: 实现内部客户端接口，统一回写 task、asset、audit**

```python
class TaskClient:
    def update_status(self, job_id: int, status: str, stage: str, error_message: str | None = None) -> None:
        payload = {"status": status, "stage": stage, "error_message": error_message}
        self._session.post(f"{self._base_url}/internal/tasks/{job_id}/status", json=payload, timeout=15)
```

- [ ] **Step 4: 实现 JobPipeline 和 Worker 入口**

```python
class JobPipeline:
    def run(self, job: GenerateJob) -> None:
        self._task_client.update_status(job.id, "preparing", "preparing")
        runtime = self._registry.get_generation_runtime(job.model_name)
        runtime.prepare(job)
        self._task_client.update_status(job.id, "generating", "generating")
        images = self._generation_service.generate(job)
        self._task_client.update_status(job.id, "scoring", "scoring")
        scored = self._scoring_service.score_batch(job, images)
        self._task_client.update_status(job.id, "persisting", "persisting")
        self._asset_client.save_results(job.id, scored)
```

- [ ] **Step 5: 扩展 FastAPI 主入口，暴露运行时状态接口**

```python
@app.get("/runtime/status")
def runtime_status() -> RuntimeStatusResponse:
    return runtime_registry.build_status()


@app.get("/runtime/models")
def runtime_models() -> RuntimeModelListResponse:
    return runtime_registry.list_models()
```

- [ ] **Step 6: 运行 Python 单测**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_job_pipeline.py -v`
Expected: `1 passed`

- [ ] **Step 7: 提交任务编排骨架**

```bash
git add python-ai-service/app python-ai-service/tests/test_job_pipeline.py
git commit -m "feat: add python job pipeline skeleton"
```

### Task 3: 扩展 Task Service 为完整任务中心

**Files:**
- Modify: `services/task-service/model/task.go`
- Modify: `services/task-service/repository/task_repository.go`
- Modify: `services/task-service/service/task_service.go`
- Modify: `services/task-service/controller/task_controller.go`
- Modify: `services/task-service/router/router.go`
- Modify: `services/task-service/service/task_service_test.go`

- [ ] **Step 1: 写失败测试，固定任务创建、详情查询、状态回写**

```go
func TestTaskServiceUpdateStatus(t *testing.T) {
	svc := NewTaskService(repo, redisClient)
	err := svc.UpdateStatus(context.Background(), 9, UpdateStatusInput{
		Status: "scoring",
		Stage:  "scoring",
	})
	require.NoError(t, err)
	require.Equal(t, "scoring", repo.updated.Status)
}
```

- [ ] **Step 2: 运行 task-service 单测确认失败**

Run: `go test ./services/task-service/service -v`
Expected: FAIL with undefined `UpdateStatus`

- [ ] **Step 3: 扩展任务模型与仓储字段**

```go
type Job struct {
	ID             int64  `json:"id"`
	JobType        string `json:"job_type"`
	Status         string `json:"status"`
	Stage          string `json:"stage"`
	ErrorMessage   string `json:"error_message"`
	ModelName      string `json:"model_name"`
	Prompt         string `json:"prompt"`
	NegativePrompt string `json:"negative_prompt"`
	PayloadJSON    string `json:"payload_json"`
	CreatedAt      string `json:"created_at"`
	UpdatedAt      string `json:"updated_at"`
}
```

- [ ] **Step 4: 增加详情查询、分页和内部状态回写接口**

```go
router.GET("/api/v1/tasks/:id", controller.GetTask)
router.GET("/api/v1/tasks", controller.ListTasks)
router.POST("/internal/tasks/:id/status", controller.UpdateTaskStatus)
```

- [ ] **Step 5: 保持 Redis Stream 投递，但 payload 改成完整任务结构**

```go
Values: map[string]any{
	"job_id":  job.ID,
	"payload": job.PayloadJSON,
	"model":   job.ModelName,
}
```

- [ ] **Step 6: 运行 task-service 单测**

Run: `go test ./services/task-service/...`
Expected: `ok  	electric-ai/services/task-service/...`

- [ ] **Step 7: 提交任务中心升级**

```bash
git add services/task-service
git commit -m "feat: expand task service lifecycle"
```

### Task 4: 扩展 Asset、Audit、Model、Gateway 服务

**Files:**
- Modify: `services/asset-service/model/asset.go`
- Modify: `services/asset-service/repository/asset_repository.go`
- Modify: `services/asset-service/service/asset_service.go`
- Modify: `services/asset-service/controller/asset_controller.go`
- Modify: `services/asset-service/router/router.go`
- Modify: `services/asset-service/service/asset_service_test.go`
- Modify: `services/audit-service/model/event.go`
- Modify: `services/audit-service/repository/audit_repository.go`
- Modify: `services/audit-service/service/audit_service.go`
- Modify: `services/audit-service/controller/audit_controller.go`
- Modify: `services/model-service/model/model.go`
- Modify: `services/model-service/service/model_service.go`
- Modify: `services/model-service/controller/model_controller.go`
- Modify: `services/gateway-service/router/router.go`
- Modify: `services/gateway-service/service/proxy_service.go`

- [ ] **Step 1: 写失败测试，固定历史列表和模型目录接口**

```go
func TestAssetServiceListHistory(t *testing.T) {
	items, err := svc.ListHistory(context.Background(), ListHistoryInput{ModelName: "sd15-electric"})
	require.NoError(t, err)
	require.Len(t, items.Items, 1)
}
```

- [ ] **Step 2: 运行 Go 单测确认失败点**

Run: `go test ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...`
Expected: FAIL with missing history/detail/model status behavior

- [ ] **Step 3: 实现 Asset Service 历史列表与详情聚合**

```go
type AssetDetail struct {
	Asset        Asset         `json:"asset"`
	Scores       ScoreSummary  `json:"scores"`
	Task         TaskSummary   `json:"task"`
	AuditEvents  []AuditEvent  `json:"audit_events"`
}
```

- [ ] **Step 4: 实现 Audit Service 按任务查询与 Model Service 状态目录**

```go
router.GET("/api/v1/audit/tasks/:task_id/events", controller.ListTaskEvents)
router.GET("/api/v1/models", controller.ListModels)
router.GET("/api/v1/models/:name", controller.GetModel)
```

- [ ] **Step 5: Gateway 代理新接口并暴露图片访问路径**

```go
proxy.Map("/api/v1/assets", assetServiceBaseURL)
proxy.Map("/api/v1/audit", auditServiceBaseURL)
proxy.Map("/files/images", "http://localhost:19090")
```

- [ ] **Step 6: 运行 Go 单测**

Run: `go test ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...`
Expected: all packages `ok`

- [ ] **Step 7: 提交平台控制面扩展**

```bash
git add services/asset-service services/audit-service services/model-service services/gateway-service
git commit -m "feat: add history audit and model control plane"
```

### Task 5: 接入 SD1.5 真实生成链路

**Files:**
- Create: `python-ai-service/app/runtimes/base.py`
- Create: `python-ai-service/app/runtimes/runtime_registry.py`
- Create: `python-ai-service/app/runtimes/sd15_runtime.py`
- Create: `python-ai-service/app/services/generation_service.py`
- Create: `python-ai-service/tests/test_sd15_runtime.py`
- Modify: `python-ai-service/scripts/download_models.py`
- Modify: `python-ai-service/requirements.txt`

- [ ] **Step 1: 写失败测试，固定 SD1.5 运行时接口和图片输出**

```python
def test_sd15_runtime_returns_saved_images(tmp_path, fake_sd_pipeline):
    runtime = SD15Runtime(fake_sd_pipeline, output_dir=tmp_path)
    result = runtime.generate(prompt="substation", negative_prompt="", seed=11, width=512, height=512)
    assert len(result.images) == 1
    assert result.images[0].path.exists()
```

- [ ] **Step 2: 运行测试确认运行时尚未实现**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_sd15_runtime.py -v`
Expected: FAIL with missing `SD15Runtime`

- [ ] **Step 3: 以低显存优先策略实现 SD1.5 Runtime**

```python
pipe = StableDiffusionPipeline.from_pretrained(
    model_dir,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    safety_checker=None,
)
pipe.enable_attention_slicing()
pipe.enable_vae_slicing()
pipe.to(device)
```

- [ ] **Step 4: 规范输出文件名、seed 与元数据**

```python
filename = f"{job_id}_{index}_{seed}.png"
image_path = self._settings.output_image_dir / filename
image.save(image_path)
```

- [ ] **Step 5: 把模型加入 manifest 和 registry**

```python
registry.register_generation(
    model_name="sd15-electric",
    runtime_factory=lambda: SD15Runtime(settings=settings),
)
```

- [ ] **Step 6: 运行测试与最小生成烟测**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_sd15_runtime.py -v`
Expected: `1 passed`

Run: `G:\miniconda3\python.exe python-ai-service\scripts\runtime_probe.py`
Expected: JSON 中 `sd15-electric` 可见，并在模型未下载时显示 `unavailable` 或 `downloading`

- [ ] **Step 7: 提交 SD1.5 运行时**

```bash
git add python-ai-service/app/runtimes python-ai-service/app/services/generation_service.py python-ai-service/scripts/download_models.py python-ai-service/tests/test_sd15_runtime.py python-ai-service/requirements.txt
git commit -m "feat: add sd15 generation runtime"
```

### Task 6: 接入真实四维评分链路

**Files:**
- Create: `python-ai-service/app/runtimes/scorers/image_reward_runtime.py`
- Create: `python-ai-service/app/runtimes/scorers/aesthetic_runtime.py`
- Create: `python-ai-service/app/runtimes/scorers/clip_iqa_runtime.py`
- Create: `python-ai-service/app/services/scoring_service.py`
- Create: `python-ai-service/tests/test_scoring_service.py`
- Modify: `python-ai-service/scripts/download_models.py`
- Modify: `python-ai-service/requirements.txt`

- [ ] **Step 1: 写失败测试，固定四维分数与总分公式**

```python
def test_scoring_service_builds_weighted_total():
    service = ScoringService()
    result = service.combine_scores(
        visual_fidelity=80,
        text_consistency=90,
        physical_plausibility=70,
        composition_aesthetics=60,
    )
    assert result.total_score == 77.5
```

- [ ] **Step 2: 运行测试确认评分服务缺失**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_scoring_service.py -v`
Expected: FAIL with missing `ScoringService`

- [ ] **Step 3: 实现 ImageReward、LAION-Aesthetics、CLIP-IQA 适配器**

```python
score = (
    visual_fidelity * 0.25
    + text_consistency * 0.30
    + physical_plausibility * 0.30
    + composition_aesthetics * 0.15
)
```

- [ ] **Step 4: 迁入旧项目本地审美权重并统一到评分目录**

```python
local_weight = settings.scoring_model_dir / "sac+logos+ava1-l14-linearMSE.pth"
if not local_weight.exists():
    shutil.copyfile(old_weight_path, local_weight)
```

- [ ] **Step 5: 在 pipeline 中接入真实评分结果**

```python
scored_assets = self._scoring_service.score_batch(job=job, images=generated_images)
```

- [ ] **Step 6: 运行测试**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_scoring_service.py -v`
Expected: `1 passed`

- [ ] **Step 7: 提交真实评分能力**

```bash
git add python-ai-service/app/runtimes/scorers python-ai-service/app/services/scoring_service.py python-ai-service/tests/test_scoring_service.py python-ai-service/scripts/download_models.py python-ai-service/requirements.txt
git commit -m "feat: add real scoring runtimes"
```

### Task 7: 迁入 UniPic2 与运行时注册目录

**Files:**
- Create: `python-ai-service/app/runtimes/unipic2_runtime.py`
- Create: `python-ai-service/app/utils/legacy_imports.py`
- Modify: `python-ai-service/app/runtimes/runtime_registry.py`
- Modify: `python-ai-service/scripts/runtime_probe.py`
- Modify: `python-ai-service/scripts/download_models.py`
- Modify: `services/model-service/service/model_service.go`
- Modify: `services/model-service/service/model_service_test.go`

- [ ] **Step 1: 写失败测试，固定 UniPic2 在不满足条件时返回 `experimental` 或 `unavailable`**

```python
def test_unipic2_probe_marks_unavailable_without_weights(tmp_path):
    runtime = UniPic2Runtime(model_root=tmp_path)
    status = runtime.probe()
    assert status.status in {"unavailable", "experimental"}
```

- [ ] **Step 2: 运行测试确认适配器缺失**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_unipic2_runtime.py -v`
Expected: FAIL with missing `UniPic2Runtime`

- [ ] **Step 3: 包装旧项目导入路径和启动参数**

```python
sys.path.append(str(legacy_root / "Project"))
sys.path.append(str(legacy_root / "Project" / "model" / "Unipic" / "UniPic-1"))
sys.path.append(str(legacy_root / "Project" / "model" / "Unipic" / "UniPic-2"))
```

- [ ] **Step 4: 在 registry 和 model-service 中注册高级模型**

```go
models = append(models, Model{
	Name:   "unipic2-kontext",
	Type:   "generation",
	Status: "experimental",
})
```

- [ ] **Step 5: 运行 Python 与 Go 侧测试**

Run: `G:\miniconda3\python.exe -m pytest python-ai-service/tests/test_unipic2_runtime.py -v`
Expected: `1 passed`

Run: `go test ./services/model-service/...`
Expected: all packages `ok`

- [ ] **Step 6: 提交 UniPic2 适配**

```bash
git add python-ai-service/app/runtimes/unipic2_runtime.py python-ai-service/app/utils/legacy_imports.py python-ai-service/scripts services/model-service
git commit -m "feat: integrate unipic2 runtime registry"
```

### Task 8: 重建前端工作台、历史中心与模型中心

**Files:**
- Create: `web-console/src/types/platform.ts`
- Create: `web-console/src/api/platform.ts`
- Create: `web-console/src/stores/platform.ts`
- Create: `web-console/src/components/AppShell.vue`
- Create: `web-console/src/components/workbench/ParameterPanel.vue`
- Create: `web-console/src/components/workbench/ResultPreview.vue`
- Create: `web-console/src/components/workbench/ScoreRadar.vue`
- Create: `web-console/src/components/history/HistoryFilters.vue`
- Create: `web-console/src/components/history/HistoryTable.vue`
- Create: `web-console/src/components/history/HistoryDetailDrawer.vue`
- Modify: `web-console/src/router/index.ts`
- Modify: `web-console/src/App.vue`
- Modify: `web-console/src/views/DashboardView.vue`
- Modify: `web-console/src/views/GenerateView.vue`
- Create: `web-console/src/views/HistoryView.vue`
- Create: `web-console/src/views/ModelCenterView.vue`
- Create: `web-console/src/views/TaskAuditView.vue`

- [ ] **Step 1: 写失败测试或最小类型约束，固定平台数据结构**

```ts
export interface ScoreSummary {
  visualFidelity: number
  textConsistency: number
  physicalPlausibility: number
  compositionAesthetics: number
  totalScore: number
}
```

- [ ] **Step 2: 先跑前端构建，确认当前页面仍是最小版**

Run: `npm --prefix web-console run build`
Expected: build passes, but generated bundle only包含旧的最小生成页

- [ ] **Step 3: 先搭统一 shell 与路由**

```ts
{
  path: "/history",
  name: "history",
  component: () => import("../views/HistoryView.vue"),
}
```

- [ ] **Step 4: 迁入旧项目参数面板、结果预览、雷达图和历史过滤能力**

```vue
<ParameterPanel v-model="form" :models="modelOptions" :submitting="submitting" @submit="submitJob" />
<ResultPreview :assets="currentAssets" :active-index="activeIndex" @change="activeIndex = $event" />
<ScoreRadar :scores="activeScores" />
```

- [ ] **Step 5: 接入任务轮询、历史查询、详情抽屉和模型可用性**

```ts
await platformStore.fetchModels()
await platformStore.fetchHistory()
await platformStore.pollTask(jobId)
```

- [ ] **Step 6: 运行构建与前端测试**

Run: `npm --prefix web-console run build`
Expected: `vite build` success

Run: `npm --prefix web-console run test`
Expected: vitest success for updated stores/components tests

- [ ] **Step 7: 提交前端重建**

```bash
git add web-console/src
git commit -m "feat: rebuild web console workbench"
```

### Task 9: 补齐 Windows 原生脚本、运行说明与端到端烟测

**Files:**
- Create: `scripts/windows/setup-python-runtime.ps1`
- Create: `scripts/windows/download-runtime-models.ps1`
- Create: `scripts/windows/start-platform.ps1`
- Create: `scripts/windows/smoke-test.ps1`
- Modify: `README.md`
- Create: `docs/runtime/windows-native-runbook.md`

- [ ] **Step 1: 写脚本前先固定启动顺序**

```powershell
$services = @(
  "services/auth-service/cmd/server",
  "services/model-service/cmd/server",
  "services/task-service/cmd/server",
  "services/asset-service/cmd/server",
  "services/audit-service/cmd/server",
  "services/gateway-service/cmd/server"
)
```

- [ ] **Step 2: 实现 Python 3.10 环境准备脚本**

```powershell
& G:\miniconda3\condabin\conda.bat create -y -p G:\miniconda3\envs\electric-ai-py310 python=3.10
& G:\miniconda3\envs\electric-ai-py310\python.exe -m pip install -r python-ai-service\requirements.txt
```

- [ ] **Step 3: 实现模型下载和平台启动脚本**

```powershell
& G:\miniconda3\envs\electric-ai-py310\python.exe python-ai-service\scripts\download_models.py --all
Start-Process powershell -ArgumentList "-NoExit", "-Command", "go run ./services/task-service/cmd/server"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "G:\miniconda3\envs\electric-ai-py310\python.exe -m app.worker"
```

- [ ] **Step 4: 实现端到端烟测脚本**

```powershell
$job = Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/v1/tasks/generate" -Body ($payload | ConvertTo-Json) -ContentType "application/json"
do {
  Start-Sleep -Seconds 3
  $detail = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/tasks/$($job.data.id)"
} while ($detail.data.status -notin @("completed", "failed"))
```

- [ ] **Step 5: 执行烟测并记录结果**

Run: `powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1`
Expected: 输出任务 ID、最终状态、历史详情 URL；完成时能拿到图片地址和四维评分

- [ ] **Step 6: 提交运行脚本与文档**

```bash
git add scripts/windows README.md docs/runtime/windows-native-runbook.md
git commit -m "docs: add native runtime scripts and runbook"
```

## 自检映射

- 规格中的“保持微服务边界”由 Task 3、Task 4、Task 9 落地，没有把模型逻辑塞回 Go。
- 规格中的“真实生成与真实评分都由 Python 跑通”由 Task 5、Task 6、Task 7 落地。
- 规格中的“完整前端工作台、历史中心、模型中心”由 Task 8 落地。
- 规格中的“Windows 原生、G 盘目录、Python 3.10”由 Task 1、Task 9 落地。
- 规格中的“任务状态、结果落库、审计追踪”由 Task 2、Task 3、Task 4 落地。

## 占位项扫描

- 已检查：本文没有 `TODO`、`TBD`、`implement later`、`similar to task` 之类占位语。
- 已检查：每个任务都列出了明确文件、命令和预期输出。
- 已检查：状态名称统一为 `queued / preparing / downloading / generating / scoring / persisting / completed / failed`。

## 执行方式

计划文件已保存到 `docs/superpowers/plans/2026-04-05-legacy-capability-migration.md`。

基于你前面“之后的步骤按照你认为最优解来，不要过多询问我”的授权，后续默认采用 **Inline Execution**，直接按本计划继续实现。
