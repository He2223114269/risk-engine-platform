# 风控引擎决策分析平台 — 开发进度追踪

> 每完成一个模块/功能，在此记录。

---

## 📋 全局进度

```
Phase 0: 骨架搭建     ████████████████████ 100% ✅
Phase 1: 数据底座     ████████░░░░░░░░░░░░  40% ⏳
Phase 2: 后端API      ██░░░░░░░░░░░░░░░░░░  10%
Phase 3: 风控引擎     ████████████████░░░░  80% ⚡ (评级三层已完成)
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
| pyproject.toml | ✅ | 05-21→05-27 | Python 项目配置（已完善 CI 配置） |
| Makefile | ✅ | 05-21 | 常用命令 |
| CI/CD workflows | ✅ | 05-27 | GitHub Actions — lint / unit-test / integration-test 全绿 |
| Docker 配置 | ✅ | 05-21 | docker-compose |
| 定时任务(cron) | ✅ | 05-21 | 每日23:00自动提交 |

---

## Phase 1：数据底座 + 核心工具包

### 1.1 数据连接器 — toolkit/connectors ✅

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `db_connector.py` | ✅ | 05-21 | 单类 get_data，通吃 risk/ts/bl/bl_risk/tr_risk/tr_fusing/ts_risk/ts_fusing/tsck/hive/dws/dwd/local 共 13 种数据源 |
| `db_config.py` | ✅ | 05-21 | 数据库配置模板（无密码，可提交到 GitHub） |
| `db_config_secret.py` | ✅ | 05-21 | 含明文密码（已 gitignore，不上传） |

### 1.2 风控指标库 — toolkit/metrics

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `pass_rate.py` | ✅ | 05-22 | v0.2.0：METRICS_REGISTRY 注册表架构 + 动态 GROUP BY/PIVOT（日期/省份/套餐类型/运营商/新老客/策略ID/渠道） |
| `overdue.py` | ⏳ | - | 逾期率计算 |
| `vintage.py` | ⏳ | - | Vintage 分析 |
| `store_quality.py` | ⏳ | - | 门店质态评分 |

### 1.3 数据同步 — toolkit/sync

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `sync_all.py` | ✅ | 05-25 | 全量同步 6 张表 |
| `run_basic.py` | ✅ | 05-25 | 基础表同步脚本 |
| `ddl_registry.py` | ✅ | 05-26 | DDL 注册管理 |
| `runner.py` | ✅ | 05-26 | 同步执行引擎（含 bug 修复：补充 `get_last_sync` import） |
| `scheduler.py` | ✅ | 05-26 | 同步调度器 |
| `sync_tracker.py` | ✅ | 05-26 | 同步进度追踪 |
| `sync_config.py` | ✅ | 05-26 | 同步配置 |
| `sync_runner.py` | ✅ | 05-26 | 同步运行器 |
| `sync_models.py` | ✅ | 05-26 | ORM 同步模型 |

> ⚠️ 逐行 INSERT 性能瓶颈，待优化为 executemany

---

## Phase 2：后端服务 + API

### 2.1 数据库 ORM

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `orm/base.py` | ✅ | 05-21 | Base + BaseModel 基类 |
| `orm/supplier_rating.py` | ✅ | 05-26 | 代理商评级 ORM |
| `orm/store_rating.py` | ✅ | 05-26 | 门店评级 ORM |
| `orm/package_rating.py` | ✅ | 05-26 | 套餐评级 ORM |
| `orm/sync_models.py` | ✅ | 05-26 | 同步模型 ORM |
| `orm/decision_record.py` | ⏳ | - | 决策记录表 |
| `orm/metric_record.py` | ⏳ | - | 指标记录表 |
| `orm/alert_log.py` | ⏳ | - | 告警日志表 |

### 2.2 API 路由

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `backend/main.py` | ⏳ | - | FastAPI 应用入口 |
| `routes/sync.py` | ✅ | 05-26 | 数据同步路由 |
| `routes/monitor.py` | ⏳ | - | 监控指标接口 |
| `routes/analysis.py` | ⏳ | - | 分析查询接口 |
| `routes/alert.py` | ⏳ | - | 告警配置接口 |

### 2.3 服务层

| 服务 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `monitor_service.py` | ⏳ | - | 每日指标聚合 |
| `alert_service.py` | ⏳ | - | 多通道告警 |
| `report_service.py` | ⏳ | - | 报表生成 |
| `scheduler_service.py` | ⏳ | - | Celery 定时任务 |

### 2.4 数据库迁移

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `migrations/env.py` | ✅ | 05-26 | Alembic 迁移环境 |
| `migrations/script.py.mako` | ✅ | 05-26 | 迁移模板 |
| `init_all_tables.py` | ✅ | 05-26 | 全表初始化迁移 |

---

## Phase 3：风控引擎 — 三层次评级体系 ✅

### 3.1 代理商评级 — supplier v3.1

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `config.py` | ✅ | 05-26 | 动态权重配置（翼支付28%/逾期32%/企查查9%/其余） |
| `extract.py` | ✅ | 05-26 | StarRocks 取数（含 supplier_name, 过滤空 code） |
| `score.py` | ✅ | 05-26 | 8 维度评分（含企查查：企业正规度+资本实力） |
| `rate.py` | ✅ | 05-26 | 按省份独立评级（A=B级=10%，不再全国统一） |
| `run.py` | ✅ | 05-26 | 一键运行（含 _merge_qichacha、动态权重重分配） |
| `schema.py` | ✅ | 05-26 | 写入数据契约 |
| `README.md` | ✅ | 05-26 | v3.1 完整文档（效果验证、权重 4 场景表格） |
| `代理商综合评级体系说明.md` | ✅ | 05-26 | 对外说明文档 |

> **核心特性**：有数据重点评，没数据权重自动重分配，总分始终可比

### 3.2 门店评级 — store ✅

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `config.py` | ✅ | 05-25 | 维度权重配置 |
| `extract.py` | ✅ | 05-25 | 数据提取 |
| `score.py` | ✅ | 05-25 | 评分映射 |
| `rate.py` | ✅ | 05-25 | 评级分配 |
| `run.py` | ✅ | 05-25 | 运行脚本 |
| `schema.py` | ✅ | 05-25 | 数据契约 |
| `analysis_report.py` | ✅ | 05-25 | 分析报告生成 |
| `README.md` | ✅ | 05-25 | 说明文档 |

### 3.3 套餐评级 — package ✅

| 文件 | 状态 | 完成日期 | 备注 |
|------|:----:|:--------:|------|
| `config.py` | ✅ | 05-25 | 维度权重配置 |
| `extract.py` | ✅ | 05-25 | 数据提取 |
| `score.py` | ✅ | 05-25 | 评分映射 |
| `rate.py` | ✅ | 05-25 | 评级分配 |
| `run.py` | ✅ | 05-25 | 运行脚本 |
| `schema.py` | ✅ | 05-25 | 数据契约 |
| `analysis_report.py` | ✅ | 05-25 | 分析报告生成 |
| `README.md` | ✅ | 05-25 | 说明文档 |

### 3.4 其他风控引擎模块

| 模块 | 文件 | 状态 | 完成日期 | 备注 |
|------|------|:----:|:--------:|------|
| 特征存储 | `registry.py` | ✅ | 05-21 | 骨架已建 |
| 特征存储 | `definitions/*.py` | ⏳ | - | 特征定义 |
| 决策引擎 | `orchestrator.py` | ✅ | 05-21 | 骨架已建 |
| 决策引擎 | `output_schema.py` | ✅ | 05-21 | 骨架已建 |
| 决策引擎 | `rules.py` | ⏳ | - | 规则定义 |
| 模型注册 | `evaluator.py` | ✅ | 05-21 | 骨架已建 |
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
| 单元测试 ≥ 80% | ⏳ | - | 仅占位文件 |
| K8s 部署配置 | ⏳ | - | |

---

## 📝 开发日志

| 日期 | 开发内容 | 完成模块 | 备注 |
|:----:|----------|:--------:|------|
| 05-21 | 架构设计 + 项目骨架搭建 | Phase 0 全部 | |
| 05-21 | connectors 连接器模块 | Phase 1.1 | 单类 get_data |
| 05-21 | pass_rate 通过率指标模块 | Phase 1.2 | 基础版本 |
| 05-22 | pass_rate v0.2.0 重构 | Phase 1.2 | METRICS_REGISTRY + 动态 PIVOT |
| 05-24 | 代理商品级 + 门店评级 + 套餐评级 | Phase 3 | 三级评级体系完整提交 |
| 05-25 | 数据同步脚本 | Phase 1.3 | sync_all + run_basic |
| 05-26 | 代理商品级 v2→v3.1 迭代 | Phase 3 | 企查查整合 + 动态权重 + 按省评级 |
| 05-26 | 同步工具包补全 | Phase 1.3 | ddl_registry / runner / scheduler 等 |
| 05-26 | 后端 ORM + 迁移 + 路由 | Phase 2 | sync_models / migrations / sync route |
| 05-27 | CI 全面修复 | Phase 0 | Run #11→#20 全线红→绿 |
| 05-27 | 占位测试文件 | Phase 0 | unit-test / integration-test 通过 |

---

> 更新方式：每完成一个模块，在此记录状态和日期。
> 上次全量更新：2026-05-27
