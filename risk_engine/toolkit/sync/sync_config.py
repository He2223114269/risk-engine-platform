"""
数据同步配置
============

定义需要从 StarRocks 同步到本地 MySQL 的数据表清单。
"""

from dataclasses import dataclass


@dataclass
class SyncTableConfig:
    """单张表的同步配置"""

    name: str  # 本地表名
    db_name: str = "risk_control"  # 目标库 (ods/dws/risk_control)
    starrocks_table: str  # StarRocks 原始表名
    description: str  # 说明
    row_estimate: int  # 行数估算
    filter_sql: str  # 筛选条件（淘顺实时授信）
    batch_size: int = 10000  # 分批写入大小
    columns: list = None  # 需要同步的字段列表（None=全部）
    index_cols: list = None  # 本地主键/索引
    incremental_key: str = None  # 增量同步的时间字段


SYNC_TABLES = [
    SyncTableConfig(
        name="dws_credit_yzf_order_complete",
        db_name="dws",
        starrocks_table="dws.dws_credit_yzf_order_complete",
        description="订单+还款主宽表",
        row_estimate=1_393_089,
        filter_sql="source_business_type = '淘顺实时授信'",
        batch_size=10000,
        incremental_key="complete_time",
    ),
    SyncTableConfig(
        name="dwd_credit_yzf_order_complete_repayment",
        db_name="dwd",
        starrocks_table="dwd.dwd_credit_yzf_order_complete_repayment",
        description="DWD 还款宽表（按订单号关联）",
        row_estimate=5_000_000,
        filter_sql="source_business_type = '淘顺实时授信'",
        batch_size=10000,
        incremental_key="repay_date",
    ),
    SyncTableConfig(
        name="ods_ts_credit_yzf_order_repayment",
        db_name="ods",
        starrocks_table="ods.ods_ts_credit_yzf_order_repayment",
        description="还款明细原始表",
        row_estimate=50_530_527,
        filter_sql="1=1",
        batch_size=20000,
        incremental_key="repay_date",
    ),
    SyncTableConfig(
        name="ods_ts_credit_yzf_order_grant_apply",
        db_name="ods",
        starrocks_table="ods.ods_ts_credit_yzf_order_grant_apply",
        description="授信申请表",
        row_estimate=2_310_465,
        filter_sql="business_type = '02'",
        batch_size=10000,
        incremental_key="add_time",
    ),
    SyncTableConfig(
        name="ods_ts_order_white_list_control",
        db_name="ods",
        starrocks_table="ods.ods_ts_order_white_list_control",
        description="风控结果表",
        row_estimate=928_107,
        filter_sql="type = '淘顺实时授信'",
        batch_size=10000,
        incremental_key="add_time",
    ),
    SyncTableConfig(
        name="ods_ts_credit_yzf_order_info_complete",
        db_name="ods",
        starrocks_table="ods.ods_ts_credit_yzf_order_info_complete",
        description="竣工表",
        row_estimate=1_515_653,
        filter_sql="1=1",
        batch_size=10000,
        incremental_key="complete_time",
    ),
    SyncTableConfig(
        name="ods_ts_v3_order_store",
        db_name="ods",
        starrocks_table="ods.ods_ts_v3_order_store",
        description="门店等级表（全量，不需要筛选）",
        row_estimate=15_843,
        filter_sql="1=1",
        batch_size=5000,
    ),
]
