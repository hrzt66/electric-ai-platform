# 电力 AI 图像生成与多维质量评价平台设计文档

> 设计日期：2026-04-04
> 设计目标：基于现有任务书、开题报告、`DB.sql` 与评分模型文档，设计一套面向工业化使用的“电力行业 AI 图像生成与四维质量评价”平台。

## 1. 项目背景

本课题名称为“基于 AI 生成电力图像及多维度质量评价”。项目目标不是仅完成图像生成演示，而是构建一套可持续扩展、可部署、可运维、可审计的行业化平台，用于支撑以下场景：

- 电力场景图像生成
- 生成结果四维质量评分
- 多模型、多 Prompt、多参数实验对比
- 电力行业关键词与评分策略管理
- 平台权限治理、操作审计、导出报表、运行监控

从现有资料来看，平台必须覆盖以下核心能力：

- 典型电力场景图像生成
- 视觉保真度、文本一致性、物理合理性、构图美观度四维评分
- 图像、Prompt、模型、评分结果、实验结果入库
- 主客观分析基础支撑
- 工业化平台能力：登录鉴权、RBAC、审计、监控、部署

## 2. 设计目标

### 2.1 总体目标

构建一个前后端分离、微服务化、面向工业应用的电力 AI 图像平台，实现“生成、评分、分析、治理、运维”全流程闭环。

### 2.2 具体目标

- 提供统一的 Web 控制台，完成图像生成、评分分析与平台管理
- 采用 Go + Gin 构建微服务体系，内部统一采用 MVC 分层
- 采用 Python 独立 AI 服务承载模型推理与评分脚本
- 使用 MySQL 持久化核心业务数据
- 使用 Redis 承担异步任务流转、缓存、幂等与限流
- 支持批量实验、任务编排、失败重试和结果导出
- 支持权限控制、审计日志、健康检查与基础告警

## 3. 范围定义

### 3.1 本期范围

本期按完整平台化第一版实施，范围包括：

- 微服务网关与认证授权体系
- 图像生成、评分、实验、导出、模型配置、审计、监控基础能力
- 本地文件存储
- Docker Compose 部署
- 面向论文展示和答辩的可运行系统

### 3.2 暂不纳入本期

以下内容在架构上预留扩展位，但不作为第一版强制交付：

- MinIO / 对象存储正式替换
- Kubernetes 编排
- 多机房高可用
- OpenTelemetry 全链路追踪平台化接入
- 企业微信、邮件、短信等外部告警通道

## 4. 总体架构

### 4.1 架构选型

平台采用：

- 前端：`Vite + Vue 3 + TypeScript + Pinia + Vue Router + Element Plus`
- 网关与业务微服务：`Go + Gin`
- AI 推理与评分：`Python` 独立服务，内部调用模型脚本
- 数据库：`MySQL`
- 缓存与队列：`Redis`
- 存储：本地文件目录
- 部署：`Docker Compose`

### 4.2 总体架构图

```text
Web Console (Vite)
        |
        v
Gateway Service (Gin)
        |
        +-------------------+-------------------+------------------+------------------+
        |                   |                   |                  |                  |
        v                   v                   v                  v                  v
Auth Service          Asset Service        Task Service      Model Service      Audit Service
        |                   |                   |                  |                  |
        +-------------------+---------+---------+------------------+------------------+
                                      |
                                      v
                                    Redis
                                      |
                                      v
                              Python AI Service
                                      |
                                      v
                           Model Scripts / Runtime

MySQL: auth_*, asset_*, task_*, model_*, audit_* tables
Local Storage: generated images, thumbnails, exports
```

### 4.3 设计原则

- 微服务边界清晰，但不过度拆分
- Go 服务内部统一 MVC 分层，降低维护成本
- 模型运行时与业务服务解耦，避免深度学习依赖污染 Gin 服务
- 异步优先，生成、评分、导出、批量实验均通过任务机制驱动
- 先单库逻辑分域，后续可平滑拆库
- 先本地存储，后续可替换为对象存储

## 5. 微服务拆分

### 5.1 Gateway Service

职责：

- 系统统一入口
- JWT 校验与用户上下文透传
- 路由转发
- 限流、跨域、统一响应、请求日志
- Swagger 聚合与健康检查聚合

约束：

- 不承载核心业务数据逻辑
- 不直接操作业务表

### 5.2 Auth Service

职责：

- 用户、角色、权限、菜单管理
- 登录、登出、刷新令牌
- 密码策略与账号状态控制
- 登录日志记录

### 5.3 Asset Service

职责：

- 图像元数据管理
- Prompt 参数管理
- 评分结果管理
- 图像详情、列表、筛选、聚合查询
- 文件信息与展示页数据聚合

### 5.4 Task Service

职责：

- 生成任务、评分任务、批量实验任务、导出任务
- Redis 队列投递与消费状态管理
- 任务状态机、失败重试、超时控制、取消
- 批量任务拆分与实验编排

### 5.5 Model Service

职责：

- 模型注册与模型版本管理
- Prompt 模板管理
- 电力行业关键词库管理
- 评分权重配置
- 系统级配置管理

### 5.6 Audit Service

职责：

- 操作审计日志
- API 访问日志
- 任务事件日志
- 告警事件记录
- 导出记录与审计报表支撑

### 5.7 Python AI Service

职责：

- 调用图像生成脚本
- 调用四维评分脚本
- 管理模型加载、释放、显存清理
- 统一返回生成与评分结果

说明：

- Python 服务不强行采用 Go 风格 MVC
- 建议采用 `api + service + runtime + schemas` 结构
- 所有具体模型与算法逻辑优先写成 Python 脚本与模块

## 6. Go 微服务内部 MVC 分层规范

每个 Go 微服务统一目录结构如下：

```text
service-name/
  cmd/
    server/
  config/
  router/
  controller/
  service/
  repository/
  model/
  middleware/
  pkg/
  docs/
```

职责约束：

- `router`：注册路由与中间件
- `controller`：接收请求、绑定参数、调用 service、返回统一响应
- `service`：承载业务编排、事务控制、调用 Redis 或其他服务
- `repository`：负责 MySQL 数据访问
- `model`：实体、DTO、VO、请求响应对象
- `middleware`：认证、审计、恢复、追踪、限流
- `pkg`：日志、JWT、错误码、响应体、数据库、Redis、配置等公共能力

设计要求：

- Controller 不写复杂业务逻辑
- Repository 不跨服务操作别的服务业务表
- Service 是核心业务边界
- 每个服务内部统一错误码与日志字段

## 7. 数据库设计

### 7.1 数据库策略

数据库连接：

- `jdbc:mysql://localhost:3306/electric_ai`

数据库策略：

- 物理上单库：`electric_ai`
- 逻辑上按服务前缀分表
- 后续如需拆库，可按域平滑迁移

### 7.2 通用字段规范

除中间关联表外，核心表建议统一包含：

- `id`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`
- `is_deleted`
- `remark`
- `version`

### 7.3 认证权限域表

- `auth_users`
- `auth_roles`
- `auth_permissions`
- `auth_menus`
- `auth_user_roles`
- `auth_role_permissions`
- `auth_role_menus`
- `auth_refresh_tokens`
- `auth_login_logs`

### 7.4 模型与策略域表

- `model_registry`
- `model_versions`
- `model_score_profiles`
- `model_prompt_templates`
- `model_power_keywords`
- `model_system_configs`

说明：

- `model_registry`：记录模型名称、模型类型、服务地址、启停状态
- `model_versions`：记录模型版本、权重路径、默认参数、兼容信息
- `model_score_profiles`：记录评分四维权重与总分算法
- `model_prompt_templates`：记录正负 Prompt 模板与适用业务场景
- `model_power_keywords`：记录电力行业关键词及其类别、权重、是否核心元素
- `model_system_configs`：存储系统级参数

### 7.5 图像资产域表

- `asset_images`
- `asset_image_prompts`
- `asset_image_scores`
- `asset_image_tags`
- `asset_image_files`

说明：

- `asset_images`：图片主表，对现有 `images` 升级
- `asset_image_prompts`：Prompt 参数表，对现有 `image_prompts` 升级
- `asset_image_scores`：四维评分与总分表
- `asset_image_tags`：按电力业务语义给图像打标签
- `asset_image_files`：多版本文件记录，如原图、缩略图、导出图

### 7.6 任务域表

- `task_jobs`
- `task_job_steps`
- `task_job_retry_logs`
- `task_batch_experiments`
- `task_batch_items`

说明：

- `task_jobs`：统一任务主表，支持 `generate`、`score`、`batch_experiment`、`export`
- `task_job_steps`：记录任务执行步骤
- `task_job_retry_logs`：记录失败重试
- `task_batch_experiments`：记录批量实验主信息
- `task_batch_items`：记录实验拆分项

### 7.7 审计运维域表

- `audit_operation_logs`
- `audit_api_logs`
- `audit_task_events`
- `audit_alerts`
- `audit_export_records`

### 7.8 现有表映射策略

现有 `DB.sql` 中主要有：

- `ai_models`
- `images`
- `image_prompts`

映射建议如下：

- `ai_models` 迁移为 `model_registry` 与 `model_versions`
- `images` 迁移为 `asset_images`
- `image_prompts` 迁移为 `asset_image_prompts`

另新增：

- `asset_image_scores`
- `task_jobs`
- `task_batch_experiments`
- 各类 `auth_*`
- 各类 `audit_*`

## 8. 评分模型设计映射

根据现有评分模型文档，平台内置四个评分维度：

- 视觉保真度 `visual_fidelity`
- 文本一致性 `text_consistency`
- 物理合理性 `physical_plausibility`
- 构图美观度 `composition_aesthetics`

### 8.1 评分服务设计要求

- Python 服务提供统一评分入口
- 支持高级评分器优先、基础评分器回退
- 支持电力行业关键词强化
- 支持评分权重配置化
- 支持模型加载失败时自动降级

### 8.2 总分建议

默认总分计算建议：

```text
total_score =
  visual_fidelity * 0.25 +
  text_consistency * 0.30 +
  physical_plausibility * 0.30 +
  composition_aesthetics * 0.15
```

说明：

- 文本一致性与物理合理性更贴近电力行业场景核心价值，权重略高
- 实际权重允许通过 `model_score_profiles` 动态调整

## 9. Redis 设计

Redis 在平台中承担以下职责：

- 任务队列
- 任务事件流转
- 分布式锁
- 幂等控制
- 热点配置缓存
- 登录态辅助缓存
- 网关限流

推荐键设计：

- `stream:generate:jobs`
- `stream:score:jobs`
- `stream:export:jobs`
- `lock:job:{job_id}`
- `cache:model:{model_id}`
- `cache:config:{config_key}`
- `rate_limit:{user_id}:{api}`

设计约束：

- 所有队列消息必须带 `job_id`
- 同一 `job_id` 消费前先做幂等校验
- 任务状态更新以 MySQL 为准，Redis 为加速层

## 10. 核心业务流程

### 10.1 登录与鉴权流程

1. 前端调用 `POST /api/v1/auth/login`
2. `auth-service` 校验用户名密码
3. 返回 `access_token`、`refresh_token`、用户信息和权限码
4. `gateway-service` 校验并透传用户上下文
5. 高风险操作写入审计日志

### 10.2 图像生成流程

1. 前端调用 `POST /api/v1/tasks/generate`
2. `task-service` 创建生成任务
3. 写入 `task_jobs`
4. 推送消息到 `stream:generate:jobs`
5. `python-ai-service` 消费消息并调用生成脚本
6. 生成图片并写入本地文件系统
7. `asset-service` 落库图片、Prompt、模型版本等信息
8. `task-service` 更新任务状态
9. `audit-service` 记录任务事件
10. 自动创建评分任务

### 10.3 评分流程

1. `task-service` 创建评分任务
2. 写入 `stream:score:jobs`
3. `python-ai-service` 调用四维评分脚本
4. 返回四维分数与总分
5. `asset-service` 更新 `asset_image_scores`
6. `task-service` 更新评分任务状态
7. `audit-service` 记录评分事件

### 10.4 批量实验流程

1. 前端提交模型集合、Prompt 模板和参数范围
2. `task-service` 创建实验主记录
3. 拆分成多个 `task_batch_items`
4. 为每个实验项串联生成与评分子任务
5. `asset-service` 汇总实验结果
6. 前端展示模型对比与结果排行

### 10.5 导出流程

1. 前端发起导出请求
2. `task-service` 创建导出任务
3. 异步生成 Excel、CSV 或 PDF
4. 导出文件写入本地存储
5. `audit-service` 记录导出行为

## 11. 接口设计

推荐接口分组如下：

- `/api/v1/auth/*`
- `/api/v1/users/*`
- `/api/v1/models/*`
- `/api/v1/prompts/*`
- `/api/v1/images/*`
- `/api/v1/scores/*`
- `/api/v1/tasks/*`
- `/api/v1/experiments/*`
- `/api/v1/audit/*`
- `/api/v1/system/*`

统一响应结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "trace_id": "trace-uuid"
}
```

异步任务建议接口：

- `POST /api/v1/tasks/generate`
- `POST /api/v1/tasks/score`
- `POST /api/v1/experiments`
- `POST /api/v1/exports`
- `GET /api/v1/tasks/{taskId}`
- `GET /api/v1/tasks/{taskId}/events`

实时进度建议：

- 第一版支持轮询
- 同时预留 `SSE` 接口用于任务进度实时推送

## 12. 前端设计

### 12.1 技术栈

- `Vue 3`
- `TypeScript`
- `Vite`
- `Pinia`
- `Vue Router`
- `Element Plus`

### 12.2 页面模块

- 登录页
- 工作台首页
- 图像生成工作台
- 图像评分分析页
- 批量实验页
- 模型与模板管理页
- 用户权限管理页
- 审计日志页
- 运维监控页
- 系统配置页

### 12.3 前端目录建议

```text
web-console/
  src/
    api/
    components/
    layouts/
    router/
    stores/
    types/
    utils/
    views/
```

前端约束：

- 页面只负责展示与交互
- 业务逻辑尽量下沉到 `stores` 与 `api`
- 权限码控制菜单、按钮与路由
- 所有任务型操作必须具备状态反馈

## 13. Python AI 服务设计

推荐目录结构：

```text
python-ai-service/
  app/
    api/
    schemas/
    services/
    runtimes/
    utils/
  scripts/
  models/
  tests/
```

职责说明：

- `api`：HTTP 接口层
- `schemas`：请求响应结构
- `services`：生成与评分服务
- `runtimes`：模型加载、释放、设备管理、显存清理
- `scripts`：具体模型运行脚本

建议接口：

- `POST /internal/generate`
- `POST /internal/score`
- `GET /health`
- `GET /models`

要求：

- 返回统一错误码
- 记录任务耗时
- 显式释放模型与显存
- 支持失败降级与超时保护

## 14. 文件存储设计

本期使用本地目录存储：

- `storage/images/`：生成图像
- `storage/thumbs/`：缩略图
- `storage/exports/`：导出文件
- `storage/temp/`：临时文件

路径策略：

- 按日期分层目录
- 文件名带唯一标识
- 数据库中只保存相对路径或业务路径

## 15. 安全设计

### 15.1 认证授权

- JWT + Refresh Token
- RBAC 权限模型
- 菜单权限、接口权限、按钮权限统一管理

### 15.2 安全措施

- 密码加密存储
- 登录失败限制与可选验证码
- 网关限流
- 文件类型校验
- 导出接口权限校验
- 高危操作审计

## 16. 异常处理与可靠性设计

统一错误处理要求：

- 所有服务统一错误码
- 统一日志字段
- 返回 `trace_id`

任务可靠性要求：

- 生成、评分、导出均支持失败重试
- 消费前做幂等校验
- 超时任务可标记 `timeout`
- 失败原因必须可追踪

推荐状态：

- 图片状态：`pending`、`generated`、`scoring`、`scored`、`failed`
- 任务状态：`queued`、`running`、`success`、`failed`、`cancelled`、`timeout`

## 17. 监控与告警设计

第一版至少提供以下能力：

- `/health` 与 `/ready` 健康检查
- 服务状态展示
- 队列积压监控
- 任务成功率、失败率、平均耗时统计
- AI 服务运行状态监控
- Redis、MySQL 基础连接状态
- 告警事件表与前端告警页

告警场景包括：

- AI 服务不可用
- 任务连续失败
- Redis 队列积压
- 导出失败
- 模型加载失败

## 18. 测试策略

### 18.1 Go 服务

- Controller 接口测试
- Service 单元测试
- Repository 集成测试
- 权限拦截测试
- 任务状态机测试
- Redis 队列消费测试

### 18.2 Python 服务

- 评分函数单元测试
- 模型加载失败回退测试
- 文件缺失与非法输入测试
- 输出结构一致性测试

### 18.3 前端

- 页面组件测试
- API Mock 联调
- 路由权限测试
- 关键流程交互测试

### 18.4 全链路测试

- 登录到生成到评分完成全链路
- 批量实验流程
- 导出流程
- 审计日志完整性
- 失败重试是否生效

## 19. 部署设计

推荐使用 Docker Compose 编排：

- `nginx`
- `gateway-service`
- `auth-service`
- `asset-service`
- `task-service`
- `model-service`
- `audit-service`
- `python-ai-service`
- `mysql`
- `redis`

交付物建议包括：

- 初始化 SQL
- `.env.example`
- Docker Compose 文件
- 本地开发启动说明
- 演示环境部署说明

## 20. 非功能性要求

- 具备基础可维护性与可扩展性
- 日志可追踪
- 配置可外置
- 页面响应清晰
- 核心链路可演示
- 代码结构适合论文撰写与答辩讲解

## 21. 实施建议

建议按以下顺序实施：

1. 初始化微服务骨架与公共组件
2. 完成认证授权与网关
3. 完成模型配置、图像资产、任务中心
4. 接入 Python AI 生成与评分服务
5. 完成前端工作台与分析页
6. 补齐实验、导出、审计、监控能力
7. 编写测试、部署脚本和演示文档

## 22. 结论

本设计将毕业设计题目收敛为一套可运行、可扩展、具备工程治理能力的微服务平台方案。该方案满足以下关键约束：

- 后端使用 `Golang Gin`
- 前端使用 `Vite`
- 模型与评分使用 `Python` 脚本实现
- 数据库使用已存在的 `MySQL electric_ai`
- 平台采用微服务架构
- Go 服务内部采用统一 `MVC` 分层
- 异步任务基础设施选择 `Redis`

该方案既满足论文课题中“生成 + 多维度评价”的研究主线，也覆盖了工业化使用所需的权限、任务、审计、监控与部署能力，适合作为后续实现与论文撰写的统一蓝图。
