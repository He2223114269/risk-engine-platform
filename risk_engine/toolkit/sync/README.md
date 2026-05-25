# 数据同步模块

从 StarRocks 同步淘顺实时授信相关数据表到本地 MySQL。

## 用法

```python
# 全量同步所有表
from risk_engine.toolkit.sync.sync_runner import run_sync
run_sync()  # 默认全量，回溯 24 个月

# 只同步指定表
run_sync(table_names=["ods_v3_store", "dws_order_complete"])

# 增量同步（只同步上次以来新增的数据）
run_sync(mode="incremental")
```

## 表清单

| 本地表名 | StarRocks 源表 | 行数 | 筛选 |
|:---------|:--------------|:----:|:-----|
| dws_order_complete | dws.dws_credit_yzf_order_complete | 139万 | 淘顺实时授信 |
| dwd_repayment | dwd.dwd_credit_yzf_order_complete_repayment | ~500万 | 淘顺实时授信 |
| ods_repayment | ods.ods_ts_credit_yzf_order_repayment | 5053万 | 全量(order_no关联) |
| ods_grant_apply | ods.ods_ts_credit_yzf_order_grant_apply | 231万 | business_type='02' |
| ods_risk_control | ods.ods_ts_order_white_list_control | 93万 | type='淘顺实时授信' |
| ods_order_complete | ods.ods_ts_credit_yzf_order_info_complete | 152万 | 全量 |
| ods_v3_store | ods.ods_ts_v3_order_store | 1.6万 | 全量 |

## 架构

```
sync/
├── __init__.py
├── sync_config.py      ← 表配置清单
├── sync_runner.py      ← 同步执行器
└── sync_tracker.py     ← 同步状态追踪
```

同步过程记录在本地 `sync_journal` 表，支持断点续传。
