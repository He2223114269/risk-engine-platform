# 风控引擎决策分析平台 — 开发进度追踪

> 每完成一个模块/功能，在此记录。

---

## 📋 全局进度

```
Phase 0: 骨架搭建     ████████████████████ 100% ✅
Phase 1: 数据底座     ░░░░░░░░░░░░░░░░░░░░   0% ⏳
Phase 2: 后端API      ░░░░░░░░░░░░░░░░░░░░   0%
Phase 3: 风控引擎     ░░░░░░░░░░░░░░░░░░░░   0%
Phase 4: 前端看板     ░░░░░░░░░░░░░░░░░░░░   0%
Phase 5: 生产化       ░░░░░░░░░░░░░░░░░░░░   0%
```

---

## Phase 0：骨架搭建 ✅

| 文件/模块 | 状态 | 日期 | 备注 |
|-----------|:----:|:----:|------|
| ARCHITECTURE.md | ✅ | 05-21 | 完整架构设计 v0.2 |
| risk_engine/README.md | ✅ | 05-21 | 风控引擎设计思想 |
| backend/README.md | ✅ | 05-21 | 后端设计思想 |
| frontend/README.md | ✅ | 05-21 | 前端设计思想 |
| CODE_STANDARDS.md | ✅ | 05-21 | 代码规范与文件头模板 |
| DEVELOPMENT_PLAN.md | ✅ | 05-21 | 开发计划 |
| pyproject.toml | ✅ | 05-21 | Python 项目配置 |
| Makefile | ✅ | 05-21 | 常用命令 |
| CI/CD workflows | ✅ | 05-21 | GitHub Actions |
| Docker 配置 | ✅ | 05-21 | docker-compose |
| 定时任务(cron) | ✅ | 05-21 | 每日23:00自动提交 |

---

## Phase 1：数据底座 + 核心工具包

### 1.1 数据连接器 — toolkit/connectors

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `factory.py` | ⏳ | - | 连接器工厂 |
| `starrocks.py` | ⏳ | - | StarRocks 连接器 |
| `mysql.py` | ⏳ | - | MySQL 连接器 |
| `kafka.py` | ⏳ | - | Kafka 生产者 |

### 1.2 风控指标库 — toolkit/metrics

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `pass_rate.py` | ⏳ | - | 通过率计算 |
| `overdue.py` | ⏳ | - | 逾期率计算 |
| `vintage.py` | ⏳ | - | Vintage 分析 |
| `store_quality.py` | ⏳ | - | 门店质态评分 |

### 1.3 数据库 ORM

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `orm/base.py` | ✅ | 05-21 | 基类骨架 |
| `orm/decision_record.py` | ⏳ | - | 决策记录表 |
| `orm/metric_record.py` | ⏳ | - | 指标记录表 |
| `orm/alert_log.py` | ⏳ | - | 告警日志表 |

---

## Phase 2：后端服务 + API

| 模块 | 文件 | 状态 | 完成日期 | 备注 |
|------|------|:----:|:--------:|------|
| API | `backend/main.py` | ⏳ | - | FastAPI 应用入口 |
| API | `routes/monitor.py` | ⏳ | - | 监控指标接口 |
| API | `routes/analysis.py` | ⏳ | - | 分析查询接口 |
| API | `routes/alert.py` | ⏳ | - | 告警配置接口 |
| 服务 | `monitor_service.py` | ⏳ | - | 每日指标聚合 |
| 服务 | `alert_service.py` | ⏳ | - | 多通道告警 |
| 服务 | `report_service.py` | ⏳ | - | 报表生成 |
| 调度 | `scheduler_service.py` | ⏳ | - | Celery 定时任务 |

---

## Phase 3：风控引擎

| 模块 | 文件 | 状态 | 完成日期 | 备注 |
|------|------|:----:|:--------:|------|
| 特征存储 | `registry.py` | ✅ | 05-21 | 骨架已建 |
| 特征存储 | `definitions/*.py` | ⏳ | - | 特征定义 |
| 决策引擎 | `orchestrator.py` | ✅ | 05-21 | 骨架已建 |
| 决策引擎 | `output_schema.py` | ✅ | 05-21 | 骨架已建 |
| 决策引擎 | `rules.py` | ⏳ | - | 规则定义 |
| 模型注册 | `version_control.py` | ⏳ | - | 版本管理 |
| 模型工程 | `pipelines/train_pipeline.py` | ⏳ | - | 训练流水线 |
| 模型工程 | `evaluation/metrics.py` | ⏳ | - | KS/AUC 实现 |

---

## Phase 4：前端看板

| 页面 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| 技术栈搭建(Vite+React+AntD) | ⏳ | - | |
| 实时大盘 Dashboard | ⏳ | - | P0 |
| 报表中心 | ⏳ | - | P0 |
| 模型监控 | ⏳ | - | P1 |
| 案例回溯 | ⏳ | - | P1 |
| 规则管理 | ⏳ | - | P2 |

---

## Phase 5：生产化

| 任务 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| 结构化日志 | ⏳ | - | JSON 格式 |
| Prometheus + Grafana | ⏳ | - | 指标看板 |
| Jaeger 链路追踪 | ⏳ | - | 全链路追踪 |
| 单元测试 ≥ 80% | ⏳ | - | pytest |
| K8s 部署配置 | ⏳ | - | |

---

## 📝 每日工作日志

| 日期 | 开发内容 | 完成模块 | 备注 |
|:----:|----------|:--------:|------|
| 05-21 | 架构设计 + 项目骨架搭建 | Phase 0 全部 | git push 成功 |
| - | - | - | - |

---

> 更新方式：每完成一个文件/功能，在此记录状态和日期。
> 每次 commit 后自动同步到 GitHub。
