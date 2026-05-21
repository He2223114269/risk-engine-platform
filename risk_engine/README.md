# Risk Engine — 风控引擎

> **设计思想：** 风控引擎是平台的核心大脑，负责所有与风险决策相关的逻辑。
> 三大设计原则：**线上线下特征一致性**、**模型与规则可编排**、**产物可追溯可回滚**。

## 模块划分

```
risk_engine/
├── feature_store/      # 特征存储 — 统一特征定义，解决离线/线上不一致
├── model_registry/     # 模型注册表 — 版本管理、灰度、回滚、AB测试
├── decision_engine/    # 决策引擎 — 模型+规则联合编排与输出标准化
├── core/               # 模型工程 — 训练/预测/评估流水线
├── toolkit/            # 函数包 — 通用工具（连接器/指标/变换/校验）
└── config/             # 配置 - 环境/模型/数据库/监控规则
```

## 核心数据流

```
原始数据 → feature_store 计算特征
                ↓
        decision_engine.orchestrator
           ↓              ↓
        model(评分)    rule(拦截)
           ↓              ↓
        output_schema 标准化输出
                ↓
        Kafka 事件 → 异步消费(统计/告警/落库)
```

## 设计要点

| 模块 | 关键设计 |
|------|----------|
| feature_store | registry 统一注册所有特征；validator 校验线上线下一致性 |
| model_registry | version_control 管理版本号/标签/回滚；deployment.yaml 定义灰度策略 |
| decision_engine | orchestrator 编排模型+规则执行顺序；ab_test 分流新旧策略 |
| core | pipeline 模式标准化训练/预测流程；evaluation 产出一份完整评估报告 |
| toolkit | factory 模式创建数据连接器；metrics 无状态纯函数，可独立测试 |

## 开发规范

- 所有模块必须通过 `__init__.py` 暴露统一入口
- toolkit 中的函数必须是**纯函数**（无状态、无副作用）
- 新增特征需在 registry 注册，严禁硬编码特征名
- 模型版本必须递增，禁止覆盖已有版本
