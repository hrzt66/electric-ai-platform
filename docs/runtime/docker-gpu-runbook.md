# Docker GPU 运行手册

本手册对应当前仓库的 Docker GPU 交付方式。目标是保持 Go 微服务边界不变，把真实生成与真实评分继续收敛到 Python 运行时，同时把整个平台重新编排到容器中。

## 1. 固定约束

- 宿主机固定为 Windows。
- Docker 路线固定使用 `deploy/docker-compose.platform.yml`。
- 运行时根目录固定挂载：宿主机 `G:\electric-ai-runtime` -> 容器 `/runtime`。
- Docker 侧模型、输出、缓存和原生链路共享同一份 `G:\electric-ai-runtime`。

## 2. 前提检查

启动前至少确认下面三件事：

- `docker compose version` 可用。
- `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` 可以看到 GPU。
- 宿主机 `G:\electric-ai-runtime` 存在，或者允许 Docker 自动创建。

## 3. 端口规划

为了避免和当前原生链路冲突，Docker 统一使用新的宿主机端口：

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

这个脚本会：

- 构建完整镜像
- 拉起 MySQL、Redis、6 个 Go 微服务、Python API、Python Worker、前端 Nginx
- 等待 `18080`、`18090`、`18088` 健康可访问

### 4.2 下载模型

下载全部运行时模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -All
```

只下载关键模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,unipic2-kontext,image-reward,aesthetic-predictor
```

只检查目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -All -CheckOnly
```

说明：

- `unipic2-kontext` 真实权重来源已经切到 `Skywork/UniPic2-SD3.5M-Kontext-2B`
- 美学权重仍优先从旧项目迁移或复用运行时目录已有权重

### 4.3 真实联调验收

默认用 `UniPic2` 做 Docker 烟测：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1
```

如果只想验证 `sd15-electric`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName sd15-electric
```

这个脚本会验证：

- gateway 登录
- Python 运行时模型目录暴露
- 真实生成任务提交
- Worker 从 Redis Stream 消费任务
- 生成结果与评分落库
- 审计事件可回查
- `/files/images/...` 预览地址可直接访问

### 4.4 停止平台

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1
```

如果要重置 MySQL / Redis 数据卷：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker/down-platform.ps1 -RemoveVolumes
```

## 5. 手工命令等价写法

如果你不想走脚本，也可以直接执行：

```powershell
docker compose -f deploy/docker-compose.platform.yml up -d --build
docker compose -f deploy/docker-compose.platform.yml run --rm python-ai-service python3 scripts/download_models.py --model unipic2-kontext --model image-reward --model aesthetic-predictor
docker compose -f deploy/docker-compose.platform.yml ps
docker compose -f deploy/docker-compose.platform.yml logs -f python-ai-worker
docker compose -f deploy/docker-compose.platform.yml down
```

## 6. 验收地址

平台拉起后：

- 前端工作台：`http://127.0.0.1:18088`
- 统一网关：`http://127.0.0.1:18080`
- Python 运行时：`http://127.0.0.1:18090`

登录账号仍为：

- 用户名：`admin`
- 密码：`admin123456`

## 7. 常见问题

### 7.1 容器能起但 `unipic2-kontext` 状态还是 `unavailable`

优先检查：

- `scripts/docker/download-models.ps1` 是否已经执行
- `G:\electric-ai-runtime\models\generation\unipic2-kontext` 是否已有完整权重文件
- `http://127.0.0.1:18090/runtime/models` 中该模型状态是否变为 `available`

### 7.2 `docker compose up` 成功，但生成任务一直不完成

优先检查：

- `python-ai-worker` 是否在运行
- `docker compose -f deploy/docker-compose.platform.yml logs -f python-ai-worker`
- Redis 是否健康
- `python-ai-service` 与 `python-ai-worker` 是否都挂载到了同一个 `G:\electric-ai-runtime`

### 7.3 图片详情里是容器路径 `/runtime/...`

这是预期行为。Docker 路线下资产记录保存的是容器内运行时路径，但 gateway 已把 `/runtime/outputs/images` 暴露成：

- `http://127.0.0.1:18080/files/images/<filename>`

因此前端预览、下载和烟测都应通过 gateway 访问，不依赖宿主机绝对路径。

## 8. 推荐验收顺序

```powershell
docker compose -f deploy/docker-compose.platform.yml config
powershell -ExecutionPolicy Bypass -File scripts/docker/up-platform.ps1
powershell -ExecutionPolicy Bypass -File scripts/docker/download-models.ps1 -Model sd15-electric,unipic2-kontext,image-reward,aesthetic-predictor
powershell -ExecutionPolicy Bypass -File scripts/docker/smoke-test.ps1 -ModelName unipic2-kontext
```
