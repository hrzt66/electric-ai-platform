# Electric AI Platform 数据库表设计

本文档依据 [001_schema.sql](/Users/hrzt/code/vibe%20coding/codex/%E6%AF%95%E4%B8%9A%E8%AE%BE%E8%AE%A1/electric-ai-platform/deploy/mysql/init/001_schema.sql) 中的真实表结构整理，用于直接插入毕业设计论文的数据库设计章节。由于当前仓库未提供学校 `docx` 模板，本文档默认采用常见毕业论文 Word 表格样式生成。字段中文含义根据表名、字段名与项目设计说明综合归纳。

表3.1 核心数据表清单

| 序号 | 表名 | 中文名称 | 作用说明 |
| --- | --- | --- | --- |
| 1 | auth_users | 用户认证表 | 存储平台登录用户的账号信息、密码摘要与状态信息。 |
| 2 | model_registry | 模型注册表 | 维护生成模型与评分模型的注册信息、服务归属与默认提示词。 |
| 3 | model_prompt_templates | 提示词模板表 | 存储不同业务场景下的正向与反向提示词模板。 |
| 4 | task_jobs | 任务主表 | 统一记录生成任务与评分任务的状态、阶段和请求负载。 |
| 5 | asset_images | 图像资产表 | 保存任务生成的图像文件路径、模型来源和状态信息。 |
| 6 | asset_image_prompts | 图像提示词参数表 | 保存单张图像对应的提示词、采样步数、随机种子等参数。 |
| 7 | asset_image_scores | 图像评分结果表 | 保存图像在多个评价维度上的评分结果及总分。 |
| 8 | asset_image_score_explanations | 图像评分解释表 | 保存评分解释结果与检查后的图像路径。 |
| 9 | audit_task_events | 任务审计事件表 | 记录任务执行过程中的阶段事件、消息与扩展载荷。 |

### auth_users 用户认证表

`auth_users` 表用于保存系统登录用户的基础身份信息，是平台认证域中的核心数据表。

表3.2 auth_users 用户认证表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 用户主键。 |
| username | VARCHAR(64) | 否 | 是 | - | 登录账号，设置唯一约束。 |
| password_hash | VARCHAR(255) | 否 | 是 | - | 用户密码摘要，不直接保存明文密码。 |
| display_name | VARCHAR(128) | 否 | 是 | - | 用户显示名称。 |
| status | VARCHAR(32) | 否 | 是 | active | 用户状态，如启用或停用。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录创建时间。 |
| updated_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 记录最后更新时间。 |

### model_registry 模型注册表

`model_registry` 表用于维护平台可调用的生成模型与评分模型元数据，为模型中心与任务编排提供配置依据。

表3.3 model_registry 模型注册表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 模型记录主键。 |
| model_name | VARCHAR(255) | 否 | 是 | - | 模型内部唯一名称，设置唯一约束。 |
| display_name | VARCHAR(255) | 否 | 是 | - | 模型对外展示名称。 |
| model_type | VARCHAR(32) | 否 | 是 | - | 模型类型，如生成模型或评分模型。 |
| service_name | VARCHAR(128) | 否 | 是 | - | 模型所属服务名称。 |
| status | VARCHAR(32) | 否 | 是 | active | 模型状态，如启用、停用。 |
| description | TEXT | 否 | 否 | NULL | 模型说明信息。 |
| default_positive_prompt | TEXT | 否 | 否 | NULL | 默认正向提示词。 |
| default_negative_prompt | TEXT | 否 | 否 | NULL | 默认反向提示词。 |
| local_path | TEXT | 否 | 否 | NULL | 模型本地路径或挂载路径。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录创建时间。 |
| updated_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 记录最后更新时间。 |

### model_prompt_templates 提示词模板表

`model_prompt_templates` 表用于沉淀不同电力业务场景下的提示词模板，便于前端快速套用标准提示词。

表3.4 model_prompt_templates 提示词模板表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 模板主键。 |
| template_name | VARCHAR(255) | 否 | 是 | - | 模板名称。 |
| scene_type | VARCHAR(64) | 否 | 是 | - | 场景类型，如变电站、输电线路等。 |
| positive_prompt | TEXT | 否 | 是 | - | 正向提示词模板内容。 |
| negative_prompt | TEXT | 否 | 否 | NULL | 反向提示词模板内容。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录创建时间。 |
| updated_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 记录最后更新时间。 |

### task_jobs 任务主表

`task_jobs` 表是平台任务域的核心主表，用于统一记录图像生成、评分等任务的状态流转与请求参数。

表3.5 task_jobs 任务主表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 任务主键。 |
| job_type | VARCHAR(32) | 否 | 是 | - | 任务类型，如生成任务、评分任务。 |
| status | VARCHAR(32) | 否 | 是 | - | 任务状态。 |
| stage | VARCHAR(32) | 否 | 是 | queued | 任务执行阶段，默认排队中。 |
| model_name | VARCHAR(128) | 否 | 是 | - | 当前任务使用的生成模型名称。 |
| scoring_model_name | VARCHAR(128) | 否 | 是 | electric-score-v1 | 当前任务使用的评分模型名称。 |
| prompt | TEXT | 否 | 否 | NULL | 正向提示词内容。 |
| negative_prompt | TEXT | 否 | 否 | NULL | 反向提示词内容。 |
| payload_json | LONGTEXT | 否 | 是 | - | 任务请求载荷，按 JSON 格式保存。 |
| error_message | TEXT | 否 | 否 | NULL | 任务失败时的错误消息。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录任务创建时间。 |
| updated_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 记录任务最后更新时间。 |

### asset_images 图像资产表

`asset_images` 表用于保存任务生成出的图像结果，是平台历史中心和资产管理功能的核心主表。该表通过 `job_id` 与 `task_jobs` 建立多对一关联。

表3.6 asset_images 图像资产表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 图像资产主键。 |
| job_id | BIGINT | 否 | 是 | - | 所属任务编号，外键关联 `task_jobs.id`。 |
| image_name | VARCHAR(255) | 否 | 是 | - | 图像名称。 |
| file_path | VARCHAR(512) | 否 | 是 | - | 图像文件存储路径。 |
| model_name | VARCHAR(255) | 否 | 是 | - | 生成该图像的模型名称。 |
| status | VARCHAR(32) | 否 | 是 | generated | 图像状态，默认已生成。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录创建时间。 |
| updated_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 记录最后更新时间。 |

### asset_image_prompts 图像提示词参数表

`asset_image_prompts` 表用于记录单张图像对应的提示词及生成参数，为结果复现与实验对比提供依据。该表通过 `image_id` 与 `asset_images` 建立关联，并在图像删除时级联删除。

表3.7 asset_image_prompts 图像提示词参数表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 提示词记录主键。 |
| image_id | BIGINT | 否 | 是 | - | 对应图像编号，外键关联 `asset_images.id`。 |
| positive_prompt | TEXT | 否 | 是 | - | 正向提示词。 |
| negative_prompt | TEXT | 否 | 否 | NULL | 反向提示词。 |
| sampling_steps | INT | 否 | 是 | - | 采样步数。 |
| seed | BIGINT | 否 | 是 | - | 随机种子。 |
| guidance_scale | DECIMAL(5,2) | 否 | 是 | - | 提示词引导系数。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录创建时间。 |

### asset_image_scores 图像评分结果表

`asset_image_scores` 表用于保存图像在多个评分维度上的评价结果，为排序展示、模型对比与论文实验分析提供支撑。该表通过 `image_id` 与 `asset_images` 建立关联，并在图像删除时级联删除。

表3.8 asset_image_scores 图像评分结果表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 评分记录主键。 |
| image_id | BIGINT | 否 | 是 | - | 对应图像编号，外键关联 `asset_images.id`。 |
| visual_fidelity | DECIMAL(5,2) | 否 | 是 | - | 视觉保真度评分。 |
| text_consistency | DECIMAL(5,2) | 否 | 是 | - | 文本一致性评分。 |
| physical_plausibility | DECIMAL(5,2) | 否 | 是 | - | 物理合理性评分。 |
| composition_aesthetics | DECIMAL(5,2) | 否 | 是 | - | 构图美观度评分。 |
| total_score | DECIMAL(5,2) | 否 | 是 | - | 综合总分。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录评分生成时间。 |

### asset_image_score_explanations 图像评分解释表

`asset_image_score_explanations` 表用于保存评分解释结果和检查后的图像路径。该表通过 `image_id` 与 `asset_images` 建立关联，同时对 `image_id` 设置唯一约束，用于保证同一图像至多对应一条解释记录。

表3.9 asset_image_score_explanations 图像评分解释表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 评分解释记录主键。 |
| image_id | BIGINT | 否 | 是 | - | 对应图像编号，外键关联 `asset_images.id`，并设置唯一约束。 |
| checked_image_path | VARCHAR(512) | 否 | 否 | NULL | 标注或检查后的图像路径。 |
| explanation_json | LONGTEXT | 否 | 是 | - | 评分解释内容，按 JSON 格式保存。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录解释生成时间。 |

### audit_task_events 任务审计事件表

`audit_task_events` 表用于记录任务在执行过程中产生的各类事件日志，可用于前端时间线展示、问题排查与任务审计追踪。该表通过 `job_id` 与 `task_jobs` 建立多对一关联。

表3.10 audit_task_events 任务审计事件表结构

| 字段名 | 数据类型 | 主键 | 非空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| id | BIGINT | 是 | 是 | 自增 | 审计事件主键。 |
| job_id | BIGINT | 否 | 是 | - | 所属任务编号，外键关联 `task_jobs.id`。 |
| event_type | VARCHAR(128) | 否 | 是 | - | 事件类型。 |
| message | TEXT | 否 | 否 | NULL | 事件说明消息。 |
| payload_json | LONGTEXT | 否 | 否 | NULL | 扩展事件载荷，按 JSON 格式保存。 |
| created_at | TIMESTAMP | 否 | 否 | CURRENT_TIMESTAMP | 记录事件发生时间。 |

### 关系说明

根据当前真实表结构，可以归纳出以下核心关系：

1. `task_jobs` 与 `asset_images` 为一对多关系，一个任务可生成多张图像。
2. `asset_images` 与 `asset_image_prompts` 为一对多或近似一对一关系，当前数据库仅约束外键，不强制唯一。
3. `asset_images` 与 `asset_image_scores` 为一对多或近似一对一关系，当前数据库仅约束外键，不强制唯一。
4. `asset_images` 与 `asset_image_score_explanations` 为一对零或一关系，数据库通过唯一约束保证一张图像最多只有一条解释记录。
5. `task_jobs` 与 `audit_task_events` 为一对多关系，一个任务对应多条审计事件。

### 使用说明

如果后续你补充学校论文模板或样文 `docx`，可以在当前内容基础上继续提取样式，并重新生成与学校模板一致的 Word 版本。
