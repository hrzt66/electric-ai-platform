# Windows 原生运行手册

本手册对应当前仓库的 Windows 原生运行方式，目标是在保持 Go 微服务边界清晰的前提下，把真实图像生成与真实评分统一收敛到 Python 运行时。若要走容器化 GPU 部署，请查看 [docs/docker-gpu-runbook.md](docker-gpu-runbook.md)。

## 1. 固定目录约束

- Python 由 `G:\miniconda3` 管理
- 项目 AI 运行时根目录固定为 `G:\electric-ai-runtime`
- 旧项目参考目录固定为 `E:\毕业设计\源代码\Project`
- 本地日志、launcher 和构建产物写入 `.runtime-logs\windows`

推荐运行时目录结构：

```text
G:\electric-ai-runtime
├─ hf-home
├─ logs
├─ models
│  ├─ generation
│  │  ├─ sd15-electric
│  │  ├─ sd15-electric-specialized
│  │  └─ unipic2-kontext
│  └─ scoring
│     ├─ image-reward
│     ├─ aesthetic-predictor
│     ├─ electric-score-v2
│     └─ electric-score-v3
├─ outputs
│  └─ images
└─ tmp
```

## 2. 启动前提

本机至少需要准备：

- Docker Desktop，可正常执行 `docker compose`
- `G:\Golang\go1.24.0\bin\go.exe`
- `G:\miniconda3\condabin\conda.bat`
- 可用的 `npm.cmd`

当前仓库最重要的环境约束：

- Go 必须显式使用 `G:\Golang\go1.24.0`
- PowerShell 下不要手动 `conda activate`，优先使用仓库脚本或直接调用虚拟环境 Python

## 3. 一键脚本清单

### 3.1 Python 环境准备

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/setup-python-runtime.ps1
```

脚本作用：

- 创建或复用 `G:\miniconda3\envs\electric-ai-py310`
- 安装 `python-ai-service\requirements.txt`
- 执行运行时探针脚本

### 3.2 模型准备

下载全部模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
```

只检查目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All -CheckOnly
```

说明：

- Hugging Face 模型下载到 `G:\electric-ai-runtime\models\...`
- 美学权重优先从旧项目目录复制
- 已有权重会被优先复用

### 3.3 平台启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-platform.ps1
```

启动顺序大致为：

1. 复用或启动 `3307/6380` 上的 MySQL 和 Redis
2. 检查运行时模型目录
3. 清理旧监听进程
4. 构建并启动 6 个 Go 微服务
5. 启动 Python API
6. 启动 Python Worker
7. 启动 `web-console` 的 Vite dev server

### 3.4 真实联调验收

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

如果要直接验收 `unipic2-kontext`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1 -ModelName unipic2-kontext
```

这个脚本会验证：

- gateway 登录
- 模型目录暴露
- 真实任务提交
- 任务从 `queued/generating/scoring` 到完成
- 历史资产回查
- 审计事件回查
- 输出图片真实落盘

## 4. 服务端口总表

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| MySQL | `3307` | Docker 暴露端口 |
| Redis | `6380` | Docker 暴露端口 |
| auth-service | `8081` | 登录与令牌 |
| model-service | `8082` | 模型目录与状态 |
| task-service | `8083` | 任务创建与状态 |
| asset-service | `8084` | 历史与详情 |
| audit-service | `8085` | 审计事件 |
| gateway-service | `8080` | 统一入口 |
| python-ai-service | `8090` | Python 运行时 API |
| web-console | `5173` | 前端工作台 |

## 5. GoLand 本地调试建议

如需在 GoLand 中单独运行某个 Go 微服务：

1. 先执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1
```

2. 把 GoLand 的 Go SDK 固定到 `G:\Golang\go1.24.0`
3. 将 Run Configuration 的 Working Directory 指到对应服务目录
4. 直接运行对应服务下的 `cmd/server/main.go`

各服务目录中的 `.env.local` 会自动提供基础环境变量。

## 6. 日志与临时产物

平台启动后会在以下目录生成运行痕迹：

- `.runtime-logs\windows\bin`
- `.runtime-logs\windows\launchers`
- `.runtime-logs\windows\*.stdout.log`
- `.runtime-logs\windows\*.stderr.log`

这些文件只用于本地排障，不应提交。

## 7. 常见问题

### 7.1 `conda activate` 报编码错误

处理方式：

- 不要手动 `conda activate`
- 统一使用脚本或直接调用 `G:\miniconda3\envs\electric-ai-py310\python.exe`

### 7.2 Go 版本用错

处理方式：

```powershell
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' version
```

### 7.3 `3307` 或 `6380` 被占用

处理方式：

- 如果占用的就是当前平台数据库或 Redis，脚本会尝试复用
- 如果是无关服务，请先释放端口

### 7.4 模型目录检查失败

处理方式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
```

### 7.5 前端可打开但接口失败

优先检查：

- `gateway-service` 是否启动
- `http://127.0.0.1:8080/health` 是否可访问
- Vite 代理是否正常转发 `/api` 和 `/files`

## 8. 推荐验收命令

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests -v
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/task-service/... ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...
npm --prefix web-console run test
npm --prefix web-console run build
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```
