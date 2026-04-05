# Windows 原生运行手册

本手册对应当前仓库的本机原生交付方式，目标是让 Go 微服务边界保持清晰，同时把所有模型推理与评分逻辑收敛到 Python 运行时。若要走容器化 GPU 部署，请直接看 `docs/runtime/docker-gpu-runbook.md`。

## 1. 固定目录约束

- Python 由 `G:\miniconda3` 管理。
- 项目 AI 运行时根目录固定为 `G:\electric-ai-runtime`。
- 旧项目参考目录固定为 `E:\毕业设计\源代码\Project`。
- 仓库默认把日志、临时 launcher 和本地构建产物写到 `.runtime-logs\windows`。

运行时目录建议保持以下结构：

```text
G:\electric-ai-runtime
├─ hf-home
├─ logs
├─ models
│  ├─ generation
│  │  ├─ sd15-electric
│  │  └─ unipic2-kontext
│  └─ scoring
│     ├─ image-reward
│     └─ aesthetic-predictor
├─ outputs
│  └─ images
└─ tmp
```

## 2. 启动前提

需要本机已经具备以下基础环境：

- Docker Desktop，可正常执行 `docker compose`
- `G:\Golang\go1.24.0\bin\go.exe`
- `G:\miniconda3\condabin\conda.bat`
- 可用的 `npm.cmd`

这套仓库当前最重要的环境约束有两个：

- Go 必须显式使用 `G:\Golang\go1.24.0`，不要误用其他目录。
- PowerShell 下尽量不要自己执行 `conda activate`，脚本已绕开这个编码问题。

## 3. 一键脚本清单

在 GoLand 中单独运行某个 Go 微服务时，仓库现在会自动读取各服务目录下的 `.env.local`。这意味着你只要把运行配置的工作目录指向对应服务根目录，例如 `services\auth-service`，就不需要再手工填写 `JWT_SECRET`、`MYSQL_DSN`、`REDIS_ADDR` 这类基础环境变量。

GoLand 本地调试默认依赖 `scripts/dev-up.ps1` 启动的 MySQL/Redis，也就是：

- MySQL：`127.0.0.1:3307`
- Redis：`127.0.0.1:6380`

如果你要直接在 GoLand 里运行本地微服务，建议先执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1
```

### 3.1 Python 环境准备

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/setup-python-runtime.ps1
```

这个脚本会做三件事：

- 创建或复用 `G:\miniconda3\envs\electric-ai-py310`
- 安装 `python-ai-service\requirements.txt`
- 执行 `python-ai-service\scripts\runtime_probe.py`

### 3.2 模型准备

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
```

如果只想检查目录，不下载模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All -CheckOnly
```

说明：

- Hugging Face 模型下载到 `G:\electric-ai-runtime\models\...`
- 美学权重优先从 `E:\毕业设计\源代码\Project\sac+logos+ava1-l14-linearMSE.pth` 复制
- 如果旧权重已复制到运行时目录，脚本会直接复用 `G:\electric-ai-runtime\models\scoring\aesthetic-predictor\...`

### 3.3 平台启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-platform.ps1
```

这个脚本会按如下顺序执行：

1. 复用或启动 `3307/6380` 上的 MySQL 和 Redis
2. 检查运行时模型目录
3. 清理旧的本项目监听进程
4. 构建并启动 6 个 Go 微服务
5. 启动 Python API
6. 启动 Python Worker
7. 启动 `web-console` 的 Vite dev server

默认输出地址：

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8080`
- `http://127.0.0.1:8090`

### 3.4 真实联调验收

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

这个脚本会验证：

- gateway 登录
- 模型目录暴露
- 真实任务提交
- 任务从 `queued/generating/scoring` 到 `completed`
- 资产历史回查
- 审计事件回查
- 输出图片真实落盘

如果你要直接验收 `UniPic2`，可以改成：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1 -ModelName unipic2-kontext
```

## 4. 服务端口总表

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| MySQL | `3307` | Docker 暴露端口 |
| Redis | `6380` | Docker 暴露端口 |
| auth-service | `8081` | 登录与令牌 |
| model-service | `8082` | 模型目录 |
| task-service | `8083` | 任务创建与状态 |
| asset-service | `8084` | 资产历史与详情 |
| audit-service | `8085` | 审计事件 |
| gateway-service | `8080` | 统一代理入口 |
| python-ai-service | `8090` | Python 运行时 API |
| web-console | `5173` | 前端工作台 dev server |

## 5. 日志与临时产物

平台启动后会在下面目录生成运行痕迹：

- `.runtime-logs\windows\bin`
  Go 微服务本地构建产物。
- `.runtime-logs\windows\launchers`
  启动时生成的本地 launcher。
- `.runtime-logs\windows\*.stdout.log`
  各服务标准输出。
- `.runtime-logs\windows\*.stderr.log`
  各服务错误输出。

这些内容只用于本地运行与排障，不应提交。

## 6. 常见故障处理

### 6.1 `conda activate` 直接报编码错误

现象：

- PowerShell 执行 `conda activate` 后抛出 `UnicodeEncodeError`

处理方式：

- 不要手动 `conda activate`
- 统一使用仓库脚本，或者直接调用 `G:\miniconda3\envs\electric-ai-py310\python.exe`

### 6.2 `go build` 或 `go test` 走错 Go 版本

现象：

- 构建命令用了错误的 `GOROOT`
- 仓库行为与之前验证结果不一致

处理方式：

```powershell
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' version
```

GoLand 里也建议把 SDK/GOROOT 切到 `G:\Golang\go1.24.0`，保持和仓库验证环境一致。

### 6.3 `3307` 或 `6380` 被占用

现象：

- `docker compose up` 提示端口已占用

处理方式：

- 如果现有监听就是当前平台的 MySQL/Redis，`start-platform.ps1` 会直接复用
- 如果只占用了一部分端口，或者占用的是无关服务，请先手动释放端口再启动

### 6.4 模型目录检查失败

现象：

- `download-runtime-models.ps1` 或 `start-platform.ps1` 提示模型目录缺失

处理方式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
```

如果是美学权重缺失：

- 确认 `E:\毕业设计\源代码\Project\sac+logos+ava1-l14-linearMSE.pth` 存在
- 或确认它已经复制到 `G:\electric-ai-runtime\models\scoring\aesthetic-predictor\`

### 6.5 前端页面打开但请求失败

现象：

- 页面能打开，但生成、历史、模型列表请求报错

处理方式：

- 确认 `gateway-service` 已启动并能访问 `http://127.0.0.1:8080/health`
- 当前 `web-console` 已配置 Vite 代理，`/api` 和 `/files` 都会转发到 `8080`

### 6.6 `unipic2-kontext` 参与 smoke 失败

说明：

- 当前仓库已经把 `unipic2-kontext` 接到真实运行时，不再只是注册表占位
- 如果 smoke 失败，优先检查 `G:\electric-ai-runtime\models\generation\unipic2-kontext` 是否已完成下载
- 下载完成后，直接使用 `scripts/windows/smoke-test.ps1 -ModelName unipic2-kontext` 即可验证真实链路

## 7. 推荐验收命令

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests -v
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/task-service/... ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...
npm --prefix web-console run test
npm --prefix web-console run build
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

