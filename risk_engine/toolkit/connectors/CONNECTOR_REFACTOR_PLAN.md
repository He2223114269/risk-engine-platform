# 数据连接器重构计划 🏗️

## 为什么要改

### 现状
```
┌──────────────┐
│   pass_rate  │──── get_data(data_type='risk') ────▶ 直连 pymysql
│   overdue    │──── get_data(data_type='risk') ────▶ 直连 pymysql
│   vintage    │──── get_data(data_type='risk') ────▶ 直连 pymysql
│   store_q.   │──── get_data(data_type='risk') ────▶ 直连 pymysql
│   ...        │
└──────────────┘
```
每个模块各自 import `get_data`，各自建连，各自关。

### 四个硬伤

**1. 一个类管所有数据库，越来越胖**
`db_connector.py` 现在 300 行，一个 `get_data` 类管了：
- 配置加载（3 种来源 + 优先级）
- 连接管理（建连/关连/心跳）
- 数据查询（单查/分批/批量写）
- 数据写入（INSERT/REPLACE/UPSERT）
- 数据更新（批量/逐条）
- 工具方法（表检查/字段检查）

以后加 ClickHouse、加 Kafka、加 Redis，是继续往这个类里塞，还是拆？

**2. 接口不统一，上层代码被数据库类型侵入**
```python
# 现在：pass_rate 需要知道自己在连什么库
calc = PassRateCalculator(get_data(data_type='risk'))

# 期望：pass_rate 只关心"我有一个连接，能跑 SQL"
calc = PassRateCalculator(conn)   # conn 是什么？我不在乎
```

**3. 没法测试**
```python
# 想单测 pass_rate.report()？
# 不行，它真的会去查 StarRocks
# 除非你有测试数据库，而且数据还得对得上
```

改进后应该能做到：
```python
# 测试时注入 MockConnector，不查库也能跑
mock_conn = MockConnector(return_df=pd.DataFrame({...}))
calc = PassRateCalculator(mock_conn)
df = calc.report(days=7)
assert df.shape == expected
```

**4. 连接管理原始**
- 每个 `get_data()` 新建连接，用完不关就泄漏
- 没有连接池，频繁建连开销大
- 失败不会自动重试
- 没有超时配置统一入口

---

## 目标架构

```
┌────────────────────────────────────────────┐
│              ConnectorFactory               │
│  create(engine_type, **options) → Connector │
└────────────────┬───────────────────────────┘
                 │
     ┌───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│StarRocks│ │  MySQL  │ │ClickHouse│ │  Mock   │
│Connector│ │Connector│ │Connector │ │Connector│
└─────────┘ └─────────┘ └─────────┘ └─────────┘
     │           │           │           │
     └───────────┴───────────┴───────────┘
                    │
         都实现 BaseConnector 接口
```

### 核心接口设计

```python
class BaseConnector(ABC):
    """所有连接器必须实现的接口"""

    @abstractmethod
    def query(self, sql: str) -> pd.DataFrame:
        """执行 SQL 查询，返回 DataFrame"""
        ...

    @abstractmethod
    def execute(self, sql: str) -> int:
        """执行写操作（INSERT/UPDATE/DELETE），返回影响行数"""
        ...

    @abstractmethod
    def close(self):
        """释放连接"""
        ...

    def __enter__(self): ...
    def __exit__(self, ...): ...
```

### 工厂设计

```python
class ConnectorFactory:
    _registry: dict[str, type[BaseConnector]] = {}

    @classmethod
    def register(cls, engine_type: str, connector_cls: type[BaseConnector]):
        """注册连接器类型"""
        cls._registry[engine_type] = connector_cls

    @classmethod
    def create(cls, engine_type: str, **options) -> BaseConnector:
        """创建连接器实例"""
        if engine_type not in cls._registry:
            raise ValueError(f"不支持的引擎类型: {engine_type}")
        return cls._registry[engine_type](**options)
```

---

## 实施步骤（回来时从这里开始）

### Step 1：定义接口 + 工厂骨架

```
risk_engine/toolkit/connectors/
├── __init__.py
├── factory.py         ← 新写：ConnectorFactory
├── base.py            ← 新写：BaseConnector 抽象基类
├── starrocks.py       ← 新写：StarRocksConnector
├── mysql.py           ← 新写：MySQLConnector
├── mock.py            ← 新写：MockConnector（用于测试）
└── db_connector.py    ← 保留旧文件不动，逐步淘汰
```

### Step 2：把现有的 `get_data` 适配进去

把 `get_data` 类的核心逻辑提取为 `StarRocksConnector` 和 `MySQLConnector`，注册到工厂。

### Step 3：改造一个指标模块做验证

选最简单的（比如 `pass_rate.py`），把构造参数从 `get_data` 改成 `BaseConnector`，用工厂创建：
```python
# 改之前
calc = PassRateCalculator(get_data(data_type='risk'))

# 改之后
conn = ConnectorFactory.create('starrocks', config='risk')
calc = PassRateCalculator(conn)
```

### Step 4：写单元测试

用 `MockConnector` 测试 `pass_rate.py` 的 `report()` 方法，不依赖真实数据库。

### Step 5：逐个替换其他模块

`overdue.py` → `vintage.py` → `store_quality.py` → 后续所有需要连库的模块。

---

## 验收标准

```bash
# 1. 工厂能创建连接器
python -c "
from risk_engine.toolkit.connectors.factory import ConnectorFactory
conn = ConnectorFactory.create('starrocks')
df = conn.query('SELECT 1')
print(df)
"

# 2. Mock 连接器能用于单测
python -c "
from risk_engine.toolkit.connectors.mock import MockConnector
from risk_engine.toolkit.metrics.pass_rate import PassRateCalculator
mock = MockConnector(return_df=pd.DataFrame({'申请数': [100], '通过率': [0.6]}))
calc = PassRateCalculator(mock)
print(calc.overall(days=7))
"

# 3. 旧代码兼容运行不变
python -c "
from risk_engine.toolkit.connectors import get_data
conn = get_data(data_type='risk')
df = conn.get_data('SELECT 1')
"
```

---

## 不会碰的部分（保持现状）

- `db_config.py` / `db_config_secret.py` — 配置格式不动，连接器直接复用
- 已经在用的旧 `get_data` 调用 — 先不改，等有空再逐模块替换
- `injion_data` / `insert_data` / `for_update_sql` 等特殊方法 — 需要时再抽象
