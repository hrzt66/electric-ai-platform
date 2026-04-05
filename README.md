# Electric AI Platform

面向工业电力场景的图像生成与评分平台，采用 `Go 微服务边界 + Python AI 运行时中心 + Vue 3 工作台` 的架构组织方式，支持真实生成、真实评分、任务审计、历史资产回溯以及 Docker / Windows 原生双运行模式。

当前仓库已经完成以下主链路落地：

- Go 微服务负责登录鉴权、模型目录、任务编排、资产落库、审计追踪和统一网关。
- Python 运行时负责真实模型加载、真实图像生成、真实评分、Redis Stream FIFO 消费和显存释放。
- 前端工作台负责生成参数配置、实时进度、历史中心、模型中心和任务审计视图。
- 运行时目录、模型缓存、日志和输出统一落在 `G:\electric-ai-runtime`，便于本机原生与 Docker 共享。

## 核心能力

- 真实生成：已接入 `sd15-electric` 与 `unipic2-kontext` 两条真实生成链路。
- 真实评分：已接入 `ImageReward`、`CLIP-IQA`、`Aesthetic Predictor` 等评分链路，并支持分数校准。
- FIFO 调度：任务由 Go 侧写入 Redis Stream，Python Worker 按 FIFO 消费并持续更新状态。
- 显存回收：生成和评分完成后主动释放模型资源，降低模型切换时的显存压力。
- 审计追踪：任务生命周期会写入审计服务，前端可查看阶段时间线与关联资产。
- 双部署方式：既支持 Windows 原生运行，也支持 Docker 编排运行。

## 技术架构

### 后端微服务

- `services/auth-service`
  登录、JWT 签发、基础身份校验。
- `services/model-service`
  模型目录、默认提示词、本地可用性探测。
- `services/task-service`
  任务创建、状态流转、Redis Stream 投递。
- `services/asset-service`
  生成结果与评分结果落库、历史中心查询、详情查询。
- `services/audit-service`
  任务事件审计、时间线查询、审计落库。
- `services/gateway-service`
  统一 HTTP 入口、鉴权转发、图片静态访问。

### Python AI 运行时

- `python-ai-service/app/main.py`
  FastAPI 入口，提供健康检查、模型探针、内部生成接口。
- `python-ai-service/app/worker.py`
  Worker 入口，持续消费 Redis Stream 中的真实任务。
- `python-ai-service/app/runtimes/*`
  真实模型运行时实现与注册中心。
- `python-ai-service/app/services/*`
  任务流水线、生成服务、评分服务。

### 前端工作台

- `web-console/src/views/GenerateView.vue`
  生成工作台与实时进度展示。
- `web-console/src/views/DashboardView.vue`
  平台总览页。
- `web-console/src/views/HistoryView.vue`
  历史中心与资产详情抽屉。
- `web-console/src/views/ModelCenterView.vue`
  模型中心。
- `web-console/src/views/TaskAuditView.vue`
  任务审计页。

## 仓库结构

```text
electric-ai-platform
├─ services/                    # Go 微服务
│  ├─ auth-service
│  ├─ model-service
│  ├─ task-service
│  ├─ asset-service
│  ├─ audit-service
│  ├─ gateway-service
│  └─ platform-common
├─ python-ai-service/           # Python AI 运行时中心
│  ├─ app/
│  ├─ scripts/
│  └─ tests/
├─ web-console/                 # Vue 3 前端工作台
├─ scripts/                     # Windows / Docker 启动与验证脚本
├─ deploy/                      # Docker、数据库初始化、镜像构建文件
├─ docs/                        # 运行手册、迁移计划、设计文档
└─ storage/                     # 本地存储目录占位
```

## 环境要求

推荐按当前仓库已验证通过的版本准备环境：

- Windows 11
- Go `G:\Golang\go1.24.0`
- Python `G:\miniconda3\envs\electric-ai-py310`
- Node.js 与 `npm`
- Docker Desktop 新版
- MySQL 8
- Redis 7
- NVIDIA GPU 与可用 CUDA 环境

## 固定目录与端口

### 本机原生运行

- Python 环境：`G:\miniconda3\envs\electric-ai-py310`
- AI 运行时根目录：`G:\electric-ai-runtime`
- 旧项目参考目录：`E:\毕业设计\源代码\Project`
- Gateway：`http://127.0.0.1:8080`
- Auth Service：`http://127.0.0.1:8081`
- Model Service：`http://127.0.0.1:8082`
- Task Service：`http://127.0.0.1:8083`
- Asset Service：`http://127.0.0.1:8084`
- Audit Service：`http://127.0.0.1:8085`
- Python API：`http://127.0.0.1:8090`
- Web Console：`http://127.0.0.1:5173`
- MySQL：`127.0.0.1:3307`
- Redis：`127.0.0.1:6380`

### Docker 运行

- Web Console：`http://127.0.0.1:18088`
- Gateway：`http://127.0.0.1:18080`
- Python API：`http://127.0.0.1:18090`
- MySQL：`127.0.0.1:13307`
- Redis：`127.0.0.1:16380`

## Windows 原生运行

推荐依次执行以下命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/setup-python-runtime.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
powershell -ExecutionPolicy Bypass -File scripts/windows/start-platform.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

### 各脚本职责

- `scripts/windows/setup-python-runtime.ps1`
  创建或复用 `G:\miniconda3\envs\electric-ai-py310` 并安装 Python 依赖。
- `scripts/windows/download-runtime-models.ps1`
  准备 `G:\electric-ai-runtime` 下的模型目录，并检查本地模型文件是否齐全。
- `scripts/windows/start-platform.ps1`
  拉起 MySQL / Redis、全部 Go 微服务、Python API、Python Worker 与前端开发服务器。
- `scripts/windows/smoke-test.ps1`
  执行真实登录、真实生成任务、状态轮询、资产校验与审计校验。

### GoLand 本地调试

如果要在 GoLand 中单独调试某个 Go 微服务，建议这样配置：

1. 先执行 `powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1` 启动 MySQL / Redis。
2. 把 GoLand 的 Go SDK 固定到 `G:\Golang\go1.24.0`。
3. 将 Run Configuration 的 Working Directory 指到目标服务目录，例如 `services\auth-service`。
4. 直接运行该服务下的 `cmd/server/main.go`。

各服务目录已经提供 `.env.local`，会自动注入：

- `APP_NAME`
- `HTTP_PORT`
- `MYSQL_DSN`
- `REDIS_ADDR`
- `JWT_SECRET`

## Docker 运行

Docker 路线使用完整编排文件 `deploy/docker-compose.platform.yml`，不会覆盖当前 Windows 原生链路。

推荐顺序：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/up-platform.ps1
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,unipic2-kontext,image-reward,aesthetic-predictor
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName unipic2-kontext
```

停止平台：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1
```

### Docker 运行前注意

- 需要设置 `JWT_SECRET`，否则容器中的 Go 服务会在启动时报 `missing required env var: JWT_SECRET`。
- Docker 会把 `G:\electric-ai-runtime` 挂载到容器内 `/runtime`，因此模型和输出会与本机原生共享。
- 如果第一次构建时间较长，属于正常现象，尤其是 Python AI 镜像与前端依赖安装阶段。

## 模型说明

### 生成模型

- `sd15-electric`
  默认真实生成模型，当前主链路和基础 smoke test 使用它。
- `unipic2-kontext`
  已完成真实运行时接入；下载 `Skywork/UniPic2-SD3.5M-Kontext-2B` 后即可参与原生和 Docker 生成链路。

### 评分模型

- `image-reward`
  文图一致性评分模型。
- `clip-iqa`
  用于视觉保真度与物理合理性打分。
- `aesthetic-predictor`
  构图美学评分模型，可迁移旧项目权重。

## 常用验证命令

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests -v

$env:GOROOT = 'G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/task-service/... ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...

npm --prefix web-console run test
npm --prefix web-console run build

powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

## 日志与排障

- 本机运行日志默认落在 `.runtime-logs/`。
- Python 运行时日志落在 `G:\electric-ai-runtime\logs`。
- 如果前端页面出现空白，先检查网关 `8080`、任务服务 `8083`、模型服务 `8082` 是否可达。
- 如果 Docker 运行时报 `JWT_SECRET` 缺失，需要在 compose 使用的环境变量中显式补齐。
- 如果 PowerShell 中使用 `conda activate` 报编码问题，请直接调用 `python.exe`，不要依赖激活脚本。

## 代码注释与维护约定

当前仓库已经按照“核心人工维护代码优先”的方式补充中文注释，重点覆盖：

- Go 微服务核心配置、服务层、仓储层
- Python 运行时入口、依赖装配、任务流水线、模型注册中心、评分与 Worker
- Vue 前端核心 store、API 封装、导航骨架、生成页、审计页、历史页、总览页
- 关键启动脚本与仓库入口文档

`TODO` 只保留在真实待办点，例如：

- 生产环境密钥管理
- 独立数据库迁移流程
- 多 GPU 调度
- 评分标定自动化
- 生产配置分层

## GitHub 发布建议

推荐仓库名：`electric-ai-platform`

如果本地已经登录 Git 并具备推送权限，可以使用：

```powershell
git remote add origin https://github.com/hrzt66/electric-ai-platform.git
git push -u origin <当前分支名>
```

如果远端仓库还没创建，需要先在 GitHub 上创建空仓库，再执行上面的命令。

## 常见问题

### 1. 为什么 GoLand 直接运行会报 `missing required env var: JWT_SECRET`？

因为服务启动时会强制检查 `JWT_SECRET`。请在 GoLand 的 Run Configuration 中设置环境变量，或者让 Working Directory 指向带 `.env.local` 的服务目录。

### 2. 为什么会报 MySQL `127.0.0.1:3307 refused`？

说明本地 MySQL 还没启动，先执行 `scripts/dev-up.ps1` 或 `scripts/windows/start-platform.ps1`。

### 3. 为什么前端请求会出现重定向过多？

通常是网关、Vite 代理或登录态失配导致。先确认：

- `http://127.0.0.1:8080/health` 可访问
- 前端本地代理仍指向网关 `8080`
- 本地登录态没有损坏

### 4. 为什么 `unipic2-kontext` 很慢？

它本身比 `sd15-electric` 更重，而且首次加载会占用更多显存与时间。当前已实现“任务完成后主动释放模型”，后续可继续优化模型预热与设备调度。

## 后续计划

- [ ] 接入生产级密钥管理与配置分层
- [ ] 把服务启动阶段的 schema bootstrap 迁移为独立迁移流程
- [ ] 为多 GPU / 多实例场景引入更清晰的运行时调度器
- [ ] 补全更细粒度的前端端到端回归测试
- [ ] 增加对象存储与外部日志平台接入能力

## 进一步文档

- Windows 原生运行手册：`docs/runtime/windows-native-runbook.md`
- Docker GPU 运行手册：`docs/runtime/docker-gpu-runbook.md`
- 迁移执行计划：`docs/superpowers/plans/2026-04-05-legacy-capability-migration.md`
