# Backend — 后端服务

> **设计思想：** 后端是平台的骨架，连接风控引擎和前端展示，负责 API 暴露、数据编排、定时调度和可观测性。
> 核心原则：**API 只编排不计算**、**异步解耦高频决策与低频统计**、**全链路可观测**。

## 模块划分

```
backend/
├── api/               # API 层 — 路由、中间件、请求/响应 Schema
├── services/          # 服务层 — 业务逻辑编排
├── database/          # 数据库层 — ORM、Repository Pattern、迁移
├── cache/             # 缓存层 — Redis 连接池、特征缓存、限流
├── message_queue/     # 消息队列 — Kafka 生产/消费
├── observability/     # 可观测性 — 日志、指标、追踪、告警
└── config/            # 配置 — pydantic-settings、日志配置、Celery
```

## 设计要点

### API 层
- RESTful 风格，版本化 (`/api/v1/`)
- Middleware 链：trace_id → auth → rate_limit → request_log
- 统一错误码体系，见 `errors.py`
- 请求响应通过 Pydantic Schema 校验

### 服务层
- 只做编排，不下放计算逻辑（计算在 risk_engine 完成）
- `scheduler_service` 管理定时任务（日报/周报/模型评估）
- `alert_service` 支持多通道推送（钉钉/邮件/企微）

### 数据库层
- Repository Pattern 屏蔽 ORM 实现
- 所有表必有 `id, created_at, updated_at, version, deleted_at`
- 读写分离通过 `read_write_split.py` 配置

### 消息队列
- 决策事件 → Kafka → 异步消费者（指标统计、预警判断）
- 解耦线上决策链路与离线分析链路

### 可观测性
- 结构化日志：JSON 格式，自动携带 trace_id
- Metrics：Prometheus 标准（请求量、延迟、错误率）
- Tracing：Jaeger 链路追踪，贯穿请求全路径

## 调度体系

```
Celery Beat (定时触发器)
    │
    ▼
scheduler_service
    ├── monitor_service   → 每日通过率/逾期率计算
    ├── report_service    → 日报/周报 Excel 生成 + 推送
    ├── alert_service     → 异常指标告警判断 + 通知
    └── evaluator(调用)   → 模型离线评估（PSI/AUC）
```
