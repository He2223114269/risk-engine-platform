# 风控引擎决策分析平台 — 架构设计 v0.2

> 大厂风控平台标准 · 生产级 · 模块化 · 可观测 · 可灰度

---

## 一、整体架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          风控引擎决策分析平台                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │   Frontend    │   │     Backend      │   │      Risk Engine       │  │
│  │   (前端)      │   │     (后端)       │   │      (风控引擎)        │  │
│  │               │   │                  │   │                        │  │
│  │  实时大盘      │   │  API (REST/gRPC) │   │  决策引擎              │  │
│  │  案例回溯     │◄──►│  服务层          │◄──►│  模型注册表 + 版本管理 │  │
│  │  模型监控     │   │  消息队列(Kafka) │   │  特征存储(线上线下)     │  │
│  │  规则管理     │   │  定时调度(Celery)│   │  规则编排              │  │
│  │  报表中心     │   │  可观测性        │   │  Pipeline 流水线       │  │
│  └──────────────┘   └──────┬───────────┘   └──────────┬─────────────┘  │
│                            │                          │                  │
│                    ┌───────▼──────────────────────────▼───────┐          │
│                    │           Infrastructure                 │          │
│                    │  ┌──────────┬────────┬──────────────┐   │          │
│                    │  │ Redis    │ Kafka  │ 数据库(多源)  │   │          │
│                    │  │ 缓存/限流 │ 事件总线 │ StarRocks    │   │          │
│                    │  │ 特征缓存  │ 解耦异步 │ MySQL / PG  │   │          │
│                    │  └──────────┴────────┴──────────────┘   │          │
│                    └─────────────────────────────────────────┘          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Observability (可观测性)                      │    │
│  │   结构化日志(JSON)  │  Prometheus 指标  │  Jaeger 链路追踪       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心数据流

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ 进件请求  │───►│  决策引擎    │───►│  结果落库    │───►│  Kafka   │
│          │    │ (模型+规则)   │    │ (数据库)     │    │  事件总线 │
└──────────┘    └──────┬───────┘    └──────────────┘    └────┬─────┘
                       │                                      │
                       ▼                                      ▼
                ┌──────────────┐                     ┌──────────────────┐
                │  特征存储     │                     │  异步消费者      │
                │ (Redis离线)   │                     │  指标统计        │
                └──────────────┘                     │  告警判断        │
                                                     │  报表生成        │
                                                     └──────────────────┘
```

---

## 三、项目目录结构

```
风控引擎决策分析平台/
│
├── README.md
├── ARCHITECTURE.md              # 架构文档（本文）
├── .gitignore
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # lint → unit-test → integration-test → build
│       └── cd.yml               # deploy-dev → smoke-test → deploy-prod(manual)
│
├── risk_engine/                 # ═══════════ 风控引擎 ═══════════
│   │
│   ├── feature_store/           # ▸ 特征存储层 ★核心
│   │   ├── __init__.py
│   │   ├── definitions/         #   特征定义（Schema）
│   │   │   ├── __init__.py
│   │   │   ├── user_features.py #     用户维度特征定义
│   │   │   ├── order_features.py#     订单维度特征定义
│   │   │   └── store_features.py#     门店维度特征定义
│   │   ├── online/              #   线上特征（Redis / 内存表）
│   │   │   ├── __init__.py
│   │   │   ├── cache.py         #     Redis 缓存层
│   │   │   └── realtime.py      #     实时特征计算
│   │   ├── offline/             #   离线特征（Hive / Iceberg / 数据库）
│   │   │   ├── __init__.py
│   │   │   ├── batch.py         #     批量特征计算
│   │   │   └── backtest.py      #     回溯特征（用于训练/回测）
│   │   ├── registry.py          #   特征注册中心（统一管理所有特征元数据）
│   │   └── validator.py         #   特征一致性校验（线上线下对比）
│   │
│   ├── model_registry/          # ▸ 模型注册表 ★核心
│   │   ├── __init__.py
│   │   ├── versions/            #   模型版本管理
│   │   │   ├── __init__.py
│   │   │   └── version_control.py#    版本号、标签、回滚
│   │   ├── artifacts/           #   模型产物存储
│   │   │   ├── __init__.py
│   │   │   └── storage.py       #     模型文件 + 预处理逻辑打包
│   │   ├── deployment.yaml      #   灰度/全量/回滚策略配置
│   │   └── evaluator.py         #   离线评估（PSI / KS / AUC / 分数分布）
│   │
│   ├── decision_engine/         # ▸ 决策引擎 ★核心
│   │   ├── __init__.py
│   │   ├── rule_group/          #   规则组
│   │   │   ├── __init__.py
│   │   │   ├── rules.py         #     规则定义（黑名单、多头、年龄限制...）
│   │   │   └── compiler.py      #     规则编译（DSL → 可执行）
│   │   ├── orchestrator.py      #   模型+规则编排（串行/并行/分支）
│   │   ├── ab_test.py           #   AB测试分流
│   │   └── output_schema.py     #   输出标准化（风险分、拒绝原因码、建议策略）
│   │
│   ├── core/                    # ▸ 模型工程流水线
│   │   ├── __init__.py
│   │   ├── models/              #   模型定义与注册
│   │   │   ├── __init__.py
│   │   │   ├── base.py          #     模型基类
│   │   │   ├── classifiers/     #     分类模型
│   │   │   └── regressors/      #     回归/评分模型
│   │   ├── pipelines/           #   流水线
│   │   │   ├── __init__.py
│   │   │   ├── train_pipeline.py
│   │   │   └── batch_predict.py #     批量预测（非线上实时，用于评估或离线）
│   │   ├── feature_engineering/ #   特征工程
│   │   │   ├── __init__.py
│   │   │   ├── transformers.py  #     WOE/分箱/归一化/编码
│   │   │   └── selectors.py     #     特征选择
│   │   └── evaluation/          #   评估
│   │       ├── __init__.py
│   │       ├── metrics.py       #     KS/AUC/混淆矩阵/LIFT
│   │       ├── stability.py     #     PSI 稳定性监控
│   │       └── reporting.py     #     评估报告生成
│   │
│   ├── toolkit/                 # ▸ 函数包（通用工具库）
│   │   ├── __init__.py
│   │   ├── connectors/          #   数据连接器
│   │   │   ├── __init__.py
│   │   │   ├── factory.py       #     连接器工厂
│   │   │   ├── starrocks.py
│   │   │   ├── mysql.py
│   │   │   └── kafka.py
│   │   ├── metrics/             #   风控专用指标
│   │   │   ├── __init__.py
│   │   │   ├── pass_rate.py
│   │   │   ├── overdue.py
│   │   │   ├── vintage.py
│   │   │   └── store_quality.py
│   │   ├── transformers/        #   数据变换
│   │   │   ├── __init__.py
│   │   │   ├── woe.py
│   │   │   ├── binning.py
│   │   │   └── normalizer.py
│   │   ├── validator.py         #   数据质量校验（空值、漂移、异常值）
│   │   └── utils/               #   通用工具
│   │       ├── __init__.py
│   │       ├── date_utils.py
│   │       ├── decorators.py    #     重试/缓存/日志装饰器
│   │       └── serialization.py
│   │
│   └── config/                  # ▸ 风控配置
│       ├── __init__.py
│       ├── settings.py          #   pydantic-settings（环境变量驱动）
│       ├── model_config.yaml
│       ├── database.yaml
│       ├── monitoring_rules.yaml#   监控规则（阈值/告警条件）
│       └── features.yaml        #   特征注册配置
│
├── backend/                     # ═══════════ 后端服务 ═══════════
│   │
│   ├── api/                     # ▸ API 层
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── decision.py      #     线上决策接口（风控核心调用）
│   │   │   ├── monitor.py       #     监控看板数据接口
│   │   │   ├── analysis.py      #     分析报表接口
│   │   │   ├── admin.py         #     模型/规则管理接口
│   │   │   └── alert.py         #     告警配置接口
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          #     鉴权
│   │   │   ├── rate_limit.py    #     限流
│   │   │   ├── request_log.py   #     请求日志（结构化）
│   │   │   └── trace_id.py      #     链路追踪ID
│   │   ├── dependencies.py      #   依赖注入
│   │   ├── errors.py            #   统一错误码
│   │   └── schemas/             #   Pydantic 请求/响应模型
│   │       ├── __init__.py
│   │       ├── decision.py
│   │       ├── monitor.py
│   │       └── analysis.py
│   │
│   ├── services/                # ▸ 业务服务层
│   │   ├── __init__.py
│   │   ├── decision_service.py  #   调用 risk_engine 做决策
│   │   ├── monitor_service.py   #   实时/离线指标聚合
│   │   ├── analysis_service.py  #   分析服务
│   │   ├── alert_service.py     #   告警（钉钉/邮件/企微）
│   │   ├── report_service.py    #   周期报表生成
│   │   └── scheduler_service.py #   定时任务编排（Celery / Airflow）
│   │
│   ├── database/                # ▸ 数据库层
│   │   ├── __init__.py
│   │   ├── orm/                 #   SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py          #     基类（id, created_at, updated_at, version, deleted_at）
│   │   │   ├── decision_record.py#    决策记录
│   │   │   ├── metric_record.py #     指标记录
│   │   │   ├── alert_log.py     #     告警日志
│   │   │   └── report_task.py   #     报表任务
│   │   ├── repositories/        #   Repository Pattern
│   │   │   ├── __init__.py
│   │   │   ├── decision_repo.py
│   │   │   ├── metric_repo.py
│   │   │   └── alert_repo.py
│   │   ├── migrations/          #   Alembic 迁移
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   └── read_write_split.py  #   读写分离
│   │
│   ├── cache/                   # ▸ 缓存层 ★新增
│   │   ├── __init__.py
│   │   ├── redis_client.py      #   Redis 连接池
│   │   ├── feature_cache.py     #   实时特征缓存
│   │   ├── rate_limiter.py      #   限流
│   │   └── session_store.py     #   会话存储
│   │
│   ├── message_queue/           # ▸ 消息队列 ★新增
│   │   ├── __init__.py
│   │   ├── producer.py          #   决策事件、监控事件生产者
│   │   └── consumer.py          #   异步消费者（指标统计、落库）
│   │
│   ├── observability/           # ▸ 可观测性 ★新增
│   │   ├── __init__.py
│   │   ├── logger.py            #   结构化日志（JSON格式）
│   │   ├── metrics.py           #   Prometheus 指标暴露
│   │   ├── tracer.py            #   Jaeger 链路追踪
│   │   └── alert_rules.yaml     #   告警规则定义
│   │
│   └── config/                  # ▸ 后端配置
│       ├── __init__.py
│       ├── settings.py          #   pydantic-settings
│       ├── logging.yaml
│       └── celery.py            #   Celery 配置
│
├── frontend/                    # ═══════════ 前端 ═══════════
│   │
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── routes/
│   │   ├── pages/
│   │   │   ├── realtime_dashboard/  # 实时大盘（TPS、拒绝率、模型调用量）
│   │   │   ├── case_analysis/       # 案例回溯（输入特征+决策结果）
│   │   │   ├── model_ops/           # 模型监控（PSI、分数分布、AUC趋势）
│   │   │   ├── rule_management/     # 规则配置（低代码化）
│   │   │   └── report_center/       # 周期报表
│   │   ├── components/
│   │   │   ├── charts/              # ECharts / AntV 封装
│   │   │   ├── tables/
│   │   │   └── layout/
│   │   ├── stores/                  # 状态管理（Pinia / Redux）
│   │   ├── api/                     # API 调用层
│   │   ├── hooks/
│   │   └── utils/
│   │
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docs/                        # ═══════════ 文档 ═══════════
│   ├── api/                     #   OpenAPI / Swagger
│   ├── database/                #   数据库设计文档（ER图）
│   ├── guides/
│   │   ├── quick_start.md
│   │   ├── developer_guide.md
│   │   └── oncall.md            #   常见故障处理手册
│   └── decisions/               #   架构决策记录（ADR）
│
├── scripts/                     # ═══════════ 运维脚本 ═══════════
│   ├── init_db.py
│   ├── seed_data.py
│   ├── deploy.sh
│   └── migrate_features.sh
│
├── tests/                       # ═══════════ 测试 ═══════════
│   ├── unit/
│   │   ├── risk_engine/
│   │   │   ├── test_feature_store.py
│   │   │   ├── test_decision_engine.py
│   │   │   ├── test_model_registry.py
│   │   │   └── test_toolkit.py
│   │   └── backend/
│   │       ├── test_api.py
│   │       └── test_services.py
│   ├── integration/
│   │   ├── test_decision_flow.py   # 端到端: 特征→决策→输出
│   │   └── test_monitor_pipeline.py
│   ├── e2e/
│   │   └── test_frontend.py
│   ├── conftest.py
│   └── fixtures/
│       ├── sample_features.json
│       └── mock_decision_data.json
│
├── docker/                      # ═══════════ 容器化 ═══════════
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml       #   本地开发环境
│   └── docker-compose.prod.yml  #   生产环境
│
├── k8s/                         # ═══════════ K8s 部署 ═══════════
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── redis-deployment.yaml
│   ├── configmap.yaml
│   └── hpa.yaml                 #   水平自动扩缩容
│
├── requirements.txt
├── pyproject.toml               # Python 项目配置（现代标准）
│
└── Makefile                     # 常用命令入口

---

## 四、模块接口契约

### 4.1 risk_engine → backend 输出

```python
# 决策结果标准化输出
@dataclass
class DecisionOutput:
    request_id: str              # 请求唯一ID（链路追踪）
    risk_score: float            # 风险分（0-1000）
    decision: str                # accept / reject / manual_review
    reject_reason: str | None    # 拒绝原因码
    model_version: str           # 决策使用的模型版本
    rule_hit: list[str]          # 命中的规则列表
    feature_snapshot: dict       # 决策时的特征快照
    decision_time_ms: int        # 决策耗时
```

### 4.2 backend → frontend 输出

```python
# 监控看板数据
@dataclass
class DashboardMetrics:
    timestamp: datetime
    total_requests: int
    accept_rate: float
    reject_rate: float
    manual_review_rate: float
    avg_response_time_ms: float
    p99_response_time_ms: float
    model_psi: dict[str, float]  # 各模型PSI
    feature_drift: dict[str, float]  # 特征漂移检测
```

### 4.3 Kafka 事件 Schema

```python
# 决策事件（生产者 → 异步消费者）
@dataclass
class DecisionEvent:
    event_id: str
    request_id: str
    timestamp: datetime
    decision_output: DecisionOutput
    source: str  # online / batch_test
```

---

## 五、CI/CD 流水线

```yaml
stages:
  - lint                          # 代码规范检查
  - unit-test                     # 单元测试（≥80%覆盖率）
  - integration-test              # 集成测试（需测试数据库/Redis）
  - build-image                   # 构建Docker镜像
  - deploy-dev                    # 自动部署开发环境
  - smoke-test                    # 冒烟测试
  - deploy-prod (manual)          # 手工触发生产部署
```

| 阶段 | Python | TypeScript |
|------|--------|------------|
| 格式化 | black + isort | Prettier |
| Lint | ruff | ESLint |
| 类型检查 | mypy --strict | tsc --strict |
| 测试 | pytest + pytest-cov | vitest |

---

## 六、工程规范

### 6.1 代码规范
- **Python**：black + isort + ruff + mypy --strict
- **TypeScript**：ESLint + Prettier + TypeScript strict mode
- **禁止硬编码**：所有配置走 pydantic-settings / YAML / 环境变量

### 6.2 数据库规范
- 所有表必有字段：`id`, `created_at`, `updated_at`, `version`
- 软删除：`deleted_at` 字段
- 索引评审：所有查询路径必须覆盖索引
- 读写分离：读流量走从库，写流量走主库

### 6.3 安全规范
- 接口鉴权：JWT / OAuth2
- 敏感数据脱敏：身份证、手机号、银行卡
- 操作审计日志：谁、什么时间、做了什么、结果
- 限流：每用户/每接口 QPS 限流

### 6.4 配置与环境管理
| 环境 | 用途 | 部署方式 |
|------|------|----------|
| dev | 本地开发 | docker-compose |
| test | CI 测试 | GitHub Actions 临时环境 |
| staging | 预发布验证 | K8s namespace |
| prod | 生产环境 | K8s + HPA + 灰度发布 |

### 6.5 文档要求
- README.md：项目简介 + 快速启动（一条命令能跑起来）
- ARCHITECTURE.md：架构图 + 模块职责（本文）
- API 文档：Swagger/OpenAPI 自动生成
- ONCALL.md：常见故障处理手册（线上出问题怎么查）
- ADR：重要架构决策记录（为什么这么设计）

---

## 七、技术选型

| 层 | 技术 | 选型理由 |
|----|------|----------|
| 风控引擎 | Python 3.12+ | 数据科学生态最成熟，sklearn/xgboost/statsmodels |
| 后端框架 | FastAPI | 异步高性能，自动 OpenAPI 文档，Pydantic 集成 |
| 前端框架 | React 18 + TypeScript | 生态丰富，Ant Design Pro 开箱即用 |
| 图表 | ECharts / AntV | 专业数据可视化，大屏场景成熟 |
| ORM | SQLAlchemy 2.0 | 异步支持，Repository Pattern 友好 |
| 特征缓存 | Redis | 高性能 KV 存储，成熟风控标配 |
| 消息队列 | Kafka | 高吞吐、持久化、异步解耦 |
| 调度 | Celery + Redis | Python 生态最成熟的任务队列 |
| 可观测性 | Prometheus + Grafana + Jaeger | 开源标准，社区活跃 |
| 容器化 | Docker + K8s | 环境一致性，弹性伸缩 |
| CI/CD | GitHub Actions | 与仓库原生集成 |
| 包管理 | Poetry (Python) / pnpm (前端) | 依赖锁定 + 版本管理 |

---

## 八、实施路线

```
Phase 1 — 核心骨架搭建（当前阶段）
├── 创建项目目录结构
├── 定义模块间接口契约（Pydantic Schema）
├── toolkit 函数包：数据连接器 + 指标库
├── 最小后端：FastAPI 脚手架 + 一个 /health 端点
└── CI 基础流水线：lint → test

Phase 2 — 决策链路打通
├── feature_store 特征注册中心 + 离线特征计算
├── decision_engine 规则引擎 + 模型编排
├── 消息队列：决策事件 → Kafka → 异步消费者
├── 后端 API：决策接口 + 监控接口
└── 集成测试：特征 → 决策 → 输出 端到端

Phase 3 — 可观测性 & 运维
├── 结构化日志 + Prometheus 指标 + Jaeger 追踪
├── 告警服务（钉钉/邮件/企微）
├── 定时调度（日报/周报/模型评估）
├── 数据库迁移（Alembic）
└── K8s 部署配置

Phase 4 — 前端 + 完善
├── 实时大盘 Dashboard
├── 模型监控页面
├── 案例回溯页面
├── 规则管理页面
└── 报表中心
```

---

> **📌 v0.2 架构设计 — 基于你的反馈全面升级。**
> 下一步：确认架构 → 创建项目骨架 → Phase 1 逐步填充。
