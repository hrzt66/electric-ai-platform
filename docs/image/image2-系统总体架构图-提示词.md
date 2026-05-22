# Electric AI Platform 总体架构图 `image2` 提示词

## 用途

这份文档用于给 `image2` 生成本项目的“系统总体架构图”。  
图中不仅要体现项目本身的前后端与 AI 执行链路，还要体现“部署到网站后的公网访问方式”。

本提示词基于以下项目事实整理：

- 仓库根说明：`README.md`
- Docker 编排：`deploy/docker-compose.platform.yml`
- 前端部署方式：`deploy/docker/web-console.Dockerfile`
- 前端反向代理：`deploy/docker/web-console.nginx.conf`
- 网关路由：`services/gateway-service/router/router.go`
- 公网部署设计：`docs/superpowers/specs/2026-04-25-vercel-local-backend-design.md`

## 推荐画图目标

生成一张适合毕业设计论文、答辩 PPT、项目汇报使用的“平台总体架构图”，要求：

- 中文标注
- 风格专业、清晰、工整
- 同时表现“公网网站入口”和“本地 GPU 后端执行中心”
- 强调“Go 微服务 + Python AI 运行时中心 + Vue 3 前端工作台”
- 强调“统一网关入口”
- 强调“Redis Stream 异步任务调度”
- 强调“生成 + 评分 + 资产落库 + 审计追踪”

## 可直接复制给 `image2` 的完整提示词

```md
请绘制一张“Electric AI Platform 面向工业电力场景的图像生成与评分平台总体架构图”，要求是中文科技风、论文级信息图、适合毕业设计答辩 PPT 使用。

一、图像整体风格要求

- 画成正式的软件系统总体架构图，不是插画，不是网页截图，不是流程漫画
- 白色或浅灰背景，蓝色+青色+少量绿色作为主色，体现工业、电力、AI、平台化风格
- 使用扁平化矢量信息图风格，线条清晰，模块边框规整，箭头明确，层次分明
- 所有文字使用中文，标题醒目，模块名称清晰可读
- 整张图要有“公网访问层、前端展示层、网关接入层、后端微服务层、AI运行时层、数据与存储层、部署环境说明”这几个层次
- 布局采用从上到下、从左到右结合的分层架构图
- 图面简洁但信息完整，不要堆砌无关图标，不要使用过度炫光，不要做成科幻海报

二、图的标题

标题写为：
“Electric AI Platform 系统总体架构图”

副标题可以写为：
“Go 微服务边界 + Python AI 运行时中心 + Vue 3 工作台 + 公网网站部署”

三、总体布局要求

请把整张图分成 6 个大层：

1. 最上层：公网访问与网站部署层
2. 第二层：前端展示层
3. 第三层：统一网关接入层
4. 第四层：后端业务微服务层
5. 第五层：Python AI 运行时与任务执行层
6. 最下层：数据存储与文件输出层

右侧额外增加一个“部署说明/运行环境”信息栏，用于说明 Vercel、本地 GPU 主机、统一 API 域名、仅网关对外暴露等要点。

四、必须出现的节点

1. 公网访问与网站部署层
- 用户浏览器
- www.camartshub.xyz
- api.camartshub.xyz
- Vercel 静态部署
- 本地 GPU 主机 / 本地后端服务器

2. 前端展示层
- Vue 3 Web Console
- 登录页
- 生成工作台
- 历史中心
- 模型中心
- 任务审计页

3. 统一网关接入层
- gateway-service
- 标注“统一 HTTP API 入口 / 鉴权转发 / 静态图片访问”

4. 后端业务微服务层
- auth-service
- model-service
- task-service
- asset-service
- audit-service

每个服务请附带一句简短说明：
- auth-service：登录认证、JWT签发
- model-service：模型目录、模型可用性探测
- task-service：任务创建、状态推进、Redis Stream 投递
- asset-service：生成结果、评分结果、历史中心查询
- audit-service：任务审计事件、时间线追踪

5. Python AI 运行时与任务执行层
- python-ai-service API
- python-ai-worker
- Redis Stream 队列
- 生成模型运行时
- 评分模型运行时

生成模型运行时框内请体现：
- sd15-electric
- unipic2-kontext

评分模型运行时框内请体现：
- ImageReward
- CLIP-IQA
- Aesthetic Predictor
- electric-score-v2

并在 AI 层强调：
- 模型按需加载
- Worker 异步消费
- 生成完成后评分
- 任务结束后释放显存/资源

6. 数据存储与文件输出层
- MySQL
- Redis
- 本地模型与输出目录
- 输出图片
- 检查图
- 运行日志

本地模型与输出目录请标注：
- G:\\electric-ai-runtime

五、必须体现的连接关系

请严格画出以下主链路：

1. 用户浏览器访问 www.camartshub.xyz
2. www.camartshub.xyz 对应 Vercel 部署的 Vue 3 Web Console
3. 前端页面通过 api.camartshub.xyz 访问后端统一入口
4. api.camartshub.xyz 指向本地 GPU 主机上的 gateway-service
5. gateway-service 分发到：
   - auth-service
   - model-service
   - task-service
   - asset-service
   - audit-service
6. gateway-service 同时提供 /files/images 和 /files/image-checks 的静态图片访问能力
7. task-service 将生成任务写入 Redis Stream
8. python-ai-worker 从 Redis Stream 异步消费任务
9. python-ai-worker 调用生成模型运行时完成图像生成
10. python-ai-worker 调用评分模型运行时完成图像评分
11. python-ai-worker 将任务状态更新回 task-service
12. python-ai-worker 将结果保存到 asset-service
13. python-ai-worker 将审计事件写入 audit-service
14. 各个 Go 微服务共享 MySQL 作为核心业务数据存储
15. Redis 为任务队列与异步调度中心
16. 生成模型、评分模型、输出图片、检查图和日志统一落到 G:\\electric-ai-runtime
17. 历史中心和图片展示最终通过 gateway-service 暴露给前端

六、必须体现的架构特征

请在图中明显体现以下设计思想：

- 前端公网部署，后端和 AI 保留在本地 GPU 电脑
- 公网只暴露一个统一 API 入口，不直接暴露数据库、Redis、Python 内部端口
- Go 微服务负责业务边界和平台能力
- Python 运行时中心负责真实模型执行、评分与资源管理
- Redis Stream 负责异步任务 FIFO 流转
- 资产服务与审计服务负责结果追踪和可视化回溯
- 平台既支持 Docker 部署，也支持本机原生运行

七、图中建议的模块分组方式

建议使用分组框或泳道：

- 公网访问区
- 前端工作台区
- 网关接入区
- Go 微服务区
- Python AI 执行区
- 数据存储区
- 部署说明区

八、部署说明信息栏内容

请在右侧单独画一个“部署说明”说明栏，写出：

- 前端站点：www.camartshub.xyz
- 前端托管：Vercel
- 后端统一入口：api.camartshub.xyz
- 后端承载位置：本地 GPU 主机
- 对外暴露策略：仅 gateway-service 对公网开放
- 内部依赖：MySQL、Redis、Python AI Worker、模型运行时
- 部署模式：Docker / Windows 原生双模式

九、图面文字要求

- 所有模块名和说明都用中文
- 可以保留少量英文技术名，例如 Vue 3、Vercel、Redis Stream、MySQL、JWT、Python AI Worker
- 字体工整、清晰、排版均衡
- 不要出现乱码，不要出现英文占位符，不要把模块名拼错

十、输出质量要求

- 输出 16:9 横版高清架构图
- 风格像毕业设计论文或项目汇报中的正式总架构图
- 保证所有模块之间的箭头关系清晰
- 保证层次清楚，避免拥挤
- 保证“网站部署链路”和“AI执行链路”同时完整可见
```

## 建议追加给 `image2` 的负面约束

如果 `image2` 支持负面提示词，可以再加这一段：

```md
不要画成手绘风，不要画成漫画，不要画成 UI 截图拼贴，不要出现 Kubernetes、Service Mesh、Kafka、云原生集群等项目中没有的组件，不要凭空添加对象存储、消息总线、负载均衡集群、手机端、小程序端、移动 App，不要把 Python AI Worker 画成前端直接调用，不要遗漏 gateway-service 统一入口，不要遗漏 Redis Stream，不要遗漏 MySQL，不要遗漏本地 GPU 主机与 Vercel 的分工。
```

## 如果你想让图更适合论文，可以补充这一句

```md
请让整张图更像“论文第3章系统总体架构图”，强调模块边界、数据流向、部署位置和职责分层，减少装饰性图标，增强学术型与工程型表达。
```

## 如果你想让图更适合答辩 PPT，可以补充这一句

```md
请适当增强模块标题的可读性和主链路视觉强调，让答辩现场远距离观看时也能快速看懂“浏览器 -> 前端站点 -> API网关 -> 微服务 -> Redis -> Python AI Worker -> 生成评分 -> 资产与审计”的完整流程。
```

## 使用建议

- 如果你只画“一张总图”，优先使用上面的完整提示词。
- 如果 `image2` 一次生成信息过多，你可以先用完整提示词，再补一句“优先保证结构准确，其次再优化美观”。
- 如果后面还要画论文插图，建议再拆两张子图：
  - 一张“平台前后端与 AI 运行时协同流程图”
  - 一张“公网网站部署图”

## 当前文档采用的默认假设

- 默认采用仓库现有平台结构作为主架构。
- 默认把 `docs/superpowers/specs/2026-04-25-vercel-local-backend-design.md` 中的公网网站部署方案一起纳入展示。
- 默认用途为“毕业设计论文 + 答辩 PPT”。

