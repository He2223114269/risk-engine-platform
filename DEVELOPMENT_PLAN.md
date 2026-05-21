# 风控引擎决策分析平台 — 开发计划

> 版本: v1.0 | 日期: 2026-05-21 | 开发者: Jingluo

---

## 开发理念

**先跑通，再优化。先数据，再决策，最后看板。**

不做大而全的一次性建设，而是按价值排序、逐个模块迭代。每个阶段产出可验证的成果。

---

## 阶段总览

```
Phase 0 ── 骨架搭建 ✅ (已完成)
Phase 1 ── 数据底座 + 核心工具包 (2周)
Phase 2 ── 后端服务 + API (2周)  
Phase 3 ── 风控指标引擎 (2周)
Phase 4 ── 前端看板 (2周)
Phase 5 ── 生产化 (持续)
```

---

## Phase 0：骨架搭建 ✅ 完成

| 任务 | 文件 | 状态 |
|------|------|:----:|
| 架构设计文档 | `ARCHITECTURE.md` | ✅ |
| 模块设计说明 | `risk_engine/README.md` / `backend/README.md` / `frontend/README.md` | ✅ |
| 代码规范 | `CODE_STANDARDS.md` | ✅ |
| 项目骨架 | 67 个文件，完整目录结构 | ✅ |
| 工程配置 | `pyproject.toml` / `Makefile` / CI/CD / Docker | ✅ |
| 定时提交 | cron: 每日23:00 | ✅ |

---

## Phase 1：数据底座 + 核心工具包（当前阶段）

**目标：数据库能连上，指标能算出来，结果能存进去。**

### 1.1 数据连接器 — toolkit/connectors

| 文件 | 内容 |
|------|------|
| `factory.py` | 连接器工厂 `ConnectorFactory.create('starrocks')` |
| `starrocks.py` | StarRocks 连接器（mysql协议，pymysql） |
| `mysql.py` | MySQL 连接器 |
| `kafka.py` | Kafka 生产者骨架 |

**验收标准：**
```python
conn = ConnectorFactory.create('starrocks')
df = conn.query("SELECT * FROM dws.dws_credit_yzf_order_complete LIMIT 10")
print(df.head())  # ✅ 能查到数据
```

### 1.2 风控指标库 — toolkit/metrics

| 文件 | 内容 |
|------|------|
| `pass_rate.py` | 通过率计算（去重/不去重两种口径） |
| `overdue.py` | 逾期率计算（M0/M1/M3+ 多维度） |
| `vintage.py` | Vintage 分析（含特批剔除逻辑） |
| `store_quality.py` | 门店质态评分（逾期率+通过率+新客占比综合） |

**验收标准：**
```python
pr = PassRateCalculator(conn)
rate = pr.calculate(start_date='2026-04-01', province='湖南省')
print(f"通过率: {rate}%")  # ✅ 算出来
```

### 1.3 数据库 ORM — backend/database/orm

| 文件 | 内容 |
|------|------|
| `base.py` | 基类 ✅ 已有骨架 |
| `decision_record.py` | 决策记录表 |
| `metric_record.py` | 指标记录表 |
| `alert_log.py` | 告警日志表 |

**验收标准：**
```python
# 初始化数据库，生成表
alembic upgrade head
# 能写入和查询
```

### 1.4 测试数据

| 文件 | 内容 |
|------|------|
| `tests/fixtures/sample_features.json` | 示例特征数据 |
| `scripts/seed_data.py` | 种子数据脚本 |

**Phase 1 产出物：** 能跑 `make test` 全部通过，`python -c "from risk_engine.toolkit.metrics.pass_rate import *"` 不报错。

---

## Phase 2：后端服务 + API

**目标：后端能响应请求，能定时跑指标，能推送告警。**

### 2.1 FastAPI 应用入口

| 文件 | 内容 |
|------|------|
| `backend/main.py` | FastAPI app 创建，注册路由，启动中间件 |
| `backend/api/routes/monitor.py` | 监控指标 API |
| `backend/api/routes/analysis.py` | 分析查询 API |
| `backend/api/routes/alert.py` | 告警配置 API |
| `backend/api/middleware/auth.py` | 简单鉴权 |
| `backend/api/middleware/request_log.py` | 请求日志 |

### 2.2 指标服务

| 文件 | 内容 |
|------|------|
| `backend/services/monitor_service.py` | 每日通过率、逾期率聚合 |
| `backend/services/alert_service.py` | 钉钉/邮件告警通道 |
| `backend/services/report_service.py` | Excel 报表生成 |

### 2.3 Celery 定时任务

| 文件 | 内容 |
|------|------|
| `backend/config/celery.py` | Celery app 配置 |
| `backend/services/scheduler_service.py` | 每日 09:00 通过率推送 |
| | 每周一 Vintage 分析 |
| | 每月初 月度报告 |

### 2.4 Repository 实现

| 文件 | 内容 |
|------|------|
| `backend/database/repositories/metric_repo.py` | 指标读写 |
| `backend/database/repositories/alert_repo.py` | 告警日志读写 |

**Phase 2 产出物：**
```bash
# 启动后端
make run-dev
# 访问 http://localhost:8000/docs 能看到 Swagger 文档
# 访问 http://localhost:8000/api/v1/monitor/pass-rate?province=湖南省 返回 JSON
# 每天 09:00 自动推送通过率日报
```

---

## Phase 3：风控指标引擎

**目标：能做商业分析级别的数据探查，覆盖日常所有分析场景。**

### 3.1 特征存储

| 文件 | 内容 |
|------|------|
| `risk_engine/feature_store/registry.py` | 特征注册中心实现 |
| `risk_engine/feature_store/definitions/*.py` | 用户/订单/门店特征定义 |
| `risk_engine/feature_store/offline/batch.py` | 批量特征计算 |

### 3.2 决策引擎

| 文件 | 内容 |
|------|------|
| `risk_engine/decision_engine/rule_group/rules.py` | 规则定义（黑名单、多头、年龄限制） |
| `risk_engine/decision_engine/rule_group/compiler.py` | 规则 DSL 编译 |
| `risk_engine/decision_engine/orchestrator.py` | 决策编排实现 |
| `risk_engine/decision_engine/ab_test.py` | AB 测试分流 |

### 3.3 模型注册表

| 文件 | 内容 |
|------|------|
| `risk_engine/model_registry/versions/version_control.py` | 版本管理 |
| `risk_engine/model_registry/artifacts/storage.py` | 模型产物存储 |
| `risk_engine/model_registry/evaluator.py` | 评估器实现（PSI/KS/AUC） |

### 3.4 模型工程

| 文件 | 内容 |
|------|------|
| `risk_engine/core/models/base.py` | 基类实现 ✅ 已有骨架 |
| `risk_engine/core/pipelines/train_pipeline.py` | 训练流水线 |
| `risk_engine/core/feature_engineering/transformers.py` | WOE/分箱实现 |
| `risk_engine/core/evaluation/metrics.py` | KS/AUC/LIFT 实现 |

**Phase 3 产出物：**
- 能从数据库拉特征，跑一遍决策链
- 能训练一个简单的评分卡模型
- 能输出决策结果到 Kafka

---

## Phase 4：前端看板

**目标：不用 SQL 也能看到数据。**

### 4.1 技术栈搭建

| 文件 | 内容 |
|------|------|
| `frontend/package.json` | React + Vite + Ant Design |
| `frontend/src/App.tsx` | 路由配置 |
| `frontend/src/api/` | API 调用封装 |
| `frontend/src/stores/` | Pinia/Redux 状态 |

### 4.2 页面开发顺序

| 页面 | 优先级 | 说明 |
|------|:------:|------|
| `realtime_dashboard/` | P0 | 总览大盘：通过率、逾期率、申请量趋势 |
| `report_center/` | P0 | 日报/月报查看和下载 |
| `model_ops/` | P1 | 模型监控：PSI、分数分布 |
| `case_analysis/` | P1 | 案例回溯：下单→决策全过程 |
| `rule_management/` | P2 | 规则配置页面 |

### 4.3 图表组件

| 组件 | 用途 |
|------|------|
| `components/charts/LineChart.tsx` | 趋势图（通过率/逾期率） |
| `components/charts/BarChart.tsx` | 对比图（各省对比） |
| `components/charts/HeatmapChart.tsx` | 热力图（省份×月份） |
| `components/charts/PieChart.tsx` | 分布图（渠道/用户类型） |

**Phase 4 产出物：**
```bash
# 启动前端
cd frontend && pnpm dev
# 打开 http://localhost:5173 能看到 Dashboard
# 能看到三个核心图表：通过率趋势、逾期率排名、申请量热力图
```

---

## Phase 5：生产化（持续）

**目标：稳定可靠，出问题能快速定位。**

### 5.1 可观测性

| 任务 | 描述 |
|------|------|
| 结构化日志 | JSON 格式，自动带 trace_id |
| Prometheus 指标 | 请求量、延迟 P50/P99、错误率 |
| Grafana 看板 | 系统监控大屏 |
| Jaeger 链路追踪 | 请求全链路追踪 |

### 5.2 测试覆盖

| 类型 | 目标 |
|------|:----:|
| 单元测试 | 核心模块 ≥ 90% |
| 集成测试 | 决策链路端到端 |
| 性能测试 | 单机 QPS 压测 |

### 5.3 部署

| 任务 | 描述 |
|------|------|
| Docker Compose | 本地一键启动 |
| K8s 部署 | dev/staging/prod 三环境 |
| CI/CD 完善 | lint → test → build → deploy 全自动 |
| HPA 自动伸缩 | 根据 CPU/内存/QPS 自动扩缩容 |

---

## 时间线估算

```
Week 1-2   ████████░░░░░░░░░░░░  Phase 1 数据底座
Week 3-4   ████████████░░░░░░░░  Phase 2 后端API
Week 5-6   ████████████████░░░░  Phase 3 风控引擎
Week 7-8   ████████████████████  Phase 4 前端看板
Week 9+    ████████████████████  Phase 5 生产化（持续）
```

---

## 每日工作流

```
23:00  ── cron 自动 commit + push（已有 ✅）
日常   ── 按照 Phase 顺序逐个文件填实现代码
       ── 每写完一个文件 run 一下测试
       ── commit 信息格式: feat(module): 做了什么
```

---

## 第一个可交付物（Phase 1 完成时）

```bash
# 一行命令安装
pip install -e ".[dev,test]"

# 配置数据库
cp .env.example .env
# 编辑 .env 填入 StarRocks/MySQL 连接信息

# 跑通指标计算
python -c "
from risk_engine.toolkit.connectors import ConnectorFactory
from risk_engine.toolkit.metrics import PassRateCalculator

conn = ConnectorFactory.create('starrocks')
calc = PassRateCalculator(conn)
print(calc.calculate(days=7))
# 输出: {'整体通过率': 63.26, '申请量': 1987, ...}
"
```

---

> 📌 这是开发计划的 v1.0 版本。
> 每个 Phase 开始前可以调整范围，根据当时的实际需求决定优先级。
