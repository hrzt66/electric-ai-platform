# Docker GPU 运行手册

本手册对应当前仓库的 Docker GPU 运行方式。目标是在不破坏 Go 微服务边界的前提下，把真实生成和真实评分继续收敛到 Python 运行时，并通过 Docker Compose 完成容器化部署。

## 1. 固定约束

- 宿主机固定为 Windows
- Docker 路线固定使用 `deploy/docker-compose.platform.yml`
- 运行时根目录固定挂载：宿主机 `G:\electric-ai-runtime` -> 容器 `/runtime`
- Docker 侧模型、输出和缓存与 Windows 原生链路共享同一份 `G:\electric-ai-runtime`

## 2. 前提检查

启动前至少确认：

- `docker compose version` 可用
- `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` 能看到 GPU
- `G:\electric-ai-runtime` 已存在，或允许 Docker 自动创建

## 3. 端口规划

为了避免和 Windows 原生链路冲突，Docker GPU 路线使用独立端口：

| 服务 | 宿主机端口 | 容器端口 |
| --- | --- | --- |
| MySQL | `13307` | `3306` |
| Redis | `16380` | `6379` |
| gateway-service | `18080` | `8080` |
| python-ai-service | `18090` | `8090` |
| web-console | `18088` | `80` |

## 4. 一键脚本

### 4.1 启动平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/up-platform.ps1
```

脚本会：

- 构建镜像
- 拉起 MySQL、Redis、6 个 Go 微服务、Python API、Python Worker 和前端 Nginx
- 等待 `18080`、`18090`、`18088` 可访问

### 4.2 下载模型

下载全部模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -All
```

只下载关键模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,sd15-electric-specialized,unipic2-kontext,image-reward,aesthetic-predictor
```

只检查目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -All -CheckOnly
```

### 4.3 真实联调验收

默认用 `unipic2-kontext` 做 Docker 烟测：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName unipic2-kontext
```

如果只想验证 `sd15-electric`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName sd15-electric
```

### 4.4 停止平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1
```

如果需要重置 MySQL / Redis 数据卷：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1 -RemoveVolumes
```

## 5. 手工命令等价写法

```powershell
docker compose -f deploy/docker-compose.platform.yml up -d --build
docker compose -f deploy/docker-compose.platform.yml run --rm python-ai-service python3 scripts/download_models.py --model unipic2-kontext --model image-reward --model aesthetic-predictor
docker compose -f deploy/docker-compose.platform.yml ps
docker compose -f deploy/docker-compose.platform.yml logs -f python-ai-worker
docker compose -f deploy/docker-compose.platform.yml down
```

## 6. 验收地址

平台启动后：

- 前端工作台：`http://127.0.0.1:18088`
- 统一网关：`http://127.0.0.1:18080`
- Python 运行时：`http://127.0.0.1:18090`

默认登录账号：

- 用户名：`admin`
- 密码：`admin123456`

## 7. 常见问题

### 7.1 容器启动成功但模型状态仍是 `unavailable`

优先检查：

- `scripts/docker/download-models.ps1` 是否已执行
- `G:\electric-ai-runtime\models\generation\...` 是否存在完整权重
- `http://127.0.0.1:18090/runtime/models` 中状态是否已变为 `available`

### 7.2 生成任务一直不完成

优先检查：

- `python-ai-worker` 是否正常运行
- `docker compose -f deploy/docker-compose.platform.yml logs -f python-ai-worker`
- Redis 是否健康
- `python-ai-service` 与 `python-ai-worker` 是否共享同一个 `/runtime`

### 7.3 详情里显示的是容器路径 `/runtime/...`

这是预期行为。Docker 路线下资产记录保存的是容器内路径，但 gateway 会把 `/runtime/outputs/images` 暴露为可访问的图片地址，因此应通过 gateway 访问图片，而不是依赖宿主机绝对路径。

## 8. 推荐验收顺序

```powershell
docker compose -f deploy/docker-compose.platform.yml config
powershell -ExecutionPolicy Bypass -File scripts/docker/up-platform.ps1
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,sd15-electric-specialized,unipic2-kontext,image-reward,aesthetic-predictor
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName unipic2-kontext
```
