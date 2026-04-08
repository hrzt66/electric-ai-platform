# Windows / Docker GPU 运行手册

本手册统一说明本项目在 Windows 原生链路和 Docker GPU 链路下的真实运行方式。目标是在保持 Go 微服务边界清晰的前提下，把真实图像生成与真实评分统一收敛到 Python 运行时，并给出可以直接复现的启动、验收和排障流程。

## 1. 适用范围

- 适用仓库：`electric-score-v2`
- 适用运行时根目录：`G:\electric-ai-runtime`
- 适用 GPU 环境：`RTX 3060 Laptop GPU 6GB` 一类单卡环境
- 适用生成模型：`sd15-electric`、`sd15-electric-specialized`
- 适用评分模型：`electric-score-v1`、`electric-score-v2`、`electric-score-v3`

当前仓库已经补充了固定 Prompt 集实测图表与对比表，图表产物位于：

- `docs/assets/real-evaluation/charts/`
- `docs/assets/real-evaluation/tables/`

## 2. 共用目录与运行约束

### 2.1 固定目录

- Python 由 `G:\miniconda3` 管理
- AI 运行时根目录固定为 `G:\electric-ai-runtime`
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

### 2.2 共用原则

- Go 必须显式使用 `G:\Golang\go1.24.0`
- PowerShell 下不要手动 `conda activate`，优先使用仓库脚本或直接调用虚拟环境 Python
- 真实生成与真实评分都依赖 `python-ai-service`
- `unipic2-kontext` 在当前 6GB 显存机器上实测存在加载失败风险，更适合作为可选路线而不是默认演示路线

## 3. Windows 原生路线

### 3.1 启动前提

本机至少需要准备：

- Docker Desktop，可正常执行 `docker compose`
- `G:\Golang\go1.24.0\bin\go.exe`
- `G:\miniconda3\condabin\conda.bat`
- `npm.cmd`

Windows 原生路线下，MySQL 与 Redis 仍可通过 Docker 复用，但 Go 微服务、Python API、Python Worker 与前端工作台直接运行在宿主机。

### 3.2 一键脚本

1. 准备 Python 运行时

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/setup-python-runtime.ps1
```

该脚本会：

- 创建或复用 `G:\miniconda3\envs\electric-ai-py310`
- 安装 `python-ai-service\requirements.txt`
- 执行运行时探针脚本

2. 下载或检查模型

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All
```

仅检查目录是否完整：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/download-runtime-models.ps1 -All -CheckOnly
```

3. 启动平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-platform.ps1
```

启动顺序大致为：

1. 复用或启动 `3307/6380` 上的 MySQL 与 Redis
2. 检查运行时模型目录
3. 清理旧监听进程
4. 构建并启动 6 个 Go 微服务
5. 启动 Python API
6. 启动 Python Worker
7. 启动 `web-console` 的 Vite dev server

4. 执行真实联调验收

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

如果要指定模型验收：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1 -ModelName sd15-electric
```

### 3.3 默认访问地址

- Web Console：`http://127.0.0.1:5173`
- Gateway：`http://127.0.0.1:8080`
- Python AI Service：`http://127.0.0.1:8090`
- MySQL：`127.0.0.1:3307`
- Redis：`127.0.0.1:6380`

### 3.4 Windows 路线推荐验收命令

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests -v
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' test ./services/task-service/... ./services/asset-service/... ./services/audit-service/... ./services/model-service/... ./services/gateway-service/...
npm --prefix web-console run test
npm --prefix web-console run build
powershell -ExecutionPolicy Bypass -File scripts/windows/smoke-test.ps1
```

## 4. Docker GPU 路线

### 4.1 启动前提

启动前至少确认：

- `docker compose version` 可用
- `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` 能识别 GPU
- `G:\electric-ai-runtime` 已存在，或允许 Docker 自动创建

Docker GPU 路线固定使用：

- 编排文件：`deploy/docker-compose.platform.yml`
- 运行时挂载：宿主机 `G:\electric-ai-runtime` -> 容器 `/runtime`

### 4.2 端口规划

为了避免和 Windows 原生链路冲突，Docker GPU 路线使用独立端口：

| 服务 | 宿主机端口 | 容器端口 |
| --- | --- | --- |
| MySQL | `13307` | `3306` |
| Redis | `16380` | `6379` |
| gateway-service | `18080` | `8080` |
| python-ai-service | `18090` | `8090` |
| web-console | `18088` | `80` |

### 4.3 一键脚本

1. 启动平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/up-platform.ps1
```

2. 下载模型

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -All
```

仅下载常用模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,sd15-electric-specialized,unipic2-kontext,image-reward,aesthetic-predictor
```

3. 真实联调验收

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName sd15-electric
```

4. 停止平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1
```

如果需要连同数据库卷一起清理：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1 -RemoveVolumes
```

### 4.4 手工命令等价写法

```powershell
docker compose -f deploy/docker-compose.platform.yml up -d --build
docker compose -f deploy/docker-compose.platform.yml run --rm python-ai-service python3 scripts/download_models.py --model sd15-electric --model sd15-electric-specialized --model image-reward --model aesthetic-predictor
docker compose -f deploy/docker-compose.platform.yml ps
docker compose -f deploy/docker-compose.platform.yml logs -f python-ai-worker
docker compose -f deploy/docker-compose.platform.yml down
```

### 4.5 默认访问地址

- Web Console：`http://127.0.0.1:18088`
- Gateway：`http://127.0.0.1:18080`
- Python AI Service：`http://127.0.0.1:18090`

默认登录账号：

- 用户名：`admin`
- 密码：`admin123456`

## 5. 如何选择路线

- 日常开发、断点调试、脚本联调优先使用 Windows 原生路线
- 需要更接近部署形态的复现与验证时使用 Docker GPU 路线
- 当前 6GB 显存设备上，固定 Prompt 集实测建议优先使用 `sd15-electric` 和 `sd15-electric-specialized`
- `unipic2-kontext` 在本机实测中出现过模型加载失败，不建议作为固定演示默认模型

## 6. 常见问题

### 6.1 `conda activate` 报错

处理方式：

- 不要手动 `conda activate`
- 统一使用脚本或直接调用 `G:\miniconda3\envs\electric-ai-py310\python.exe`

### 6.2 Go 版本不正确

```powershell
$env:GOROOT='G:\Golang\go1.24.0'
& 'G:\Golang\go1.24.0\bin\go.exe' version
```

### 6.3 模型状态一直是 `unavailable`

优先检查：

- 模型目录是否完整
- `download-runtime-models.ps1` 或 `download-models.ps1` 是否已执行
- `http://127.0.0.1:8090/runtime/models` 或 `http://127.0.0.1:18090/runtime/models` 返回状态是否正常

### 6.4 任务长时间停留在生成或评分中

优先检查：

- Python Worker 是否正常运行
- 当前模型是否超过显存或页面文件可承受范围
- Docker 路线下 `python-ai-service` 与 `python-ai-worker` 是否共享同一份 `/runtime`

### 6.5 详情里显示容器路径 `/runtime/...`

这属于预期行为。Docker 路线下资产记录会保留容器内路径，但前端应通过 Gateway 暴露的文件访问地址查看图片，而不是依赖宿主机绝对路径。

## 7. 推荐验收顺序

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m pytest python-ai-service/tests/test_benchmark_utils.py -q
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' -m py_compile python-ai-service/scripts/build_real_evaluation_assets.py python-ai-service/app/benchmark_utils.py
```

如果需要复用已有评测结果重新生成图表与表格：

```powershell
& 'G:\miniconda3\envs\electric-ai-py310\python.exe' python-ai-service/scripts/build_real_evaluation_assets.py --skip-benchmark --output-root docs/assets/real-evaluation
```

完成后可以在以下目录查看实测结果：

- `docs/assets/real-evaluation/charts/`
- `docs/assets/real-evaluation/tables/`
