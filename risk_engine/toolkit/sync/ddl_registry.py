"""
数据同步 DDL 注册表
===================

每张同步表的建表 DDL 定义在这里。
明确定义字段类型、索引、注释，不依赖 StarRocks 自动推断。
"""

from dataclasses import dataclass


@dataclass
class DDLEntry:
    """一张表的 DDL 定义"""

    schema_name: str  # 目标库 (ods/dwd/dws/ads)
    table_name: str  # 表名
    ddl: str  # CREATE TABLE 语句
    description: str  # 说明
    row_estimate: int  # 预估行数
    batch_size: int = 10000  # 每批条数


# ════════════════════════════════════════════════════════════════
#  ODS 层 — 原始数据
# ════════════════════════════════════════════════════════════════

ODS_STORE_TABLE = DDLEntry(
    schema_name="ods",
    table_name="ods_ts_v3_order_store",
    description="门店等级表",
    row_estimate=15_843,
    batch_size=5000,
    ddl="""
    CREATE TABLE IF NOT EXISTS ods.ods_ts_v3_order_store (
        id BIGINT PRIMARY KEY COMMENT '主键',
        isv VARCHAR(32) COMMENT 'ISV标识',
        type VARCHAR(32) COMMENT '类型',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        store_code VARCHAR(64)  COMMENT '门店编码',
        store_name VARCHAR(256) COMMENT '门店名称',
        channel_level VARCHAR(32) COMMENT '渠道等级',
        notes TEXT COMMENT '备注',
        add_time DATETIME COMMENT '添加时间',
        update_time DATETIME COMMENT '更新时间',
        lh_time DATETIME COMMENT '拉黑时间',
        lh_js_time DATETIME COMMENT '拉黑结束时间',
        adjust_type VARCHAR(32) COMMENT '调整类型'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='门店等级表'
    """,
)

ODS_RISK_TABLE = DDLEntry(
    schema_name="ods",
    table_name="ods_ts_order_white_list_control",
    description="风控结果表",
    row_estimate=928_107,
    batch_size=10000,
    ddl="""
    CREATE TABLE IF NOT EXISTS ods.ods_ts_order_white_list_control (
        id BIGINT PRIMARY KEY COMMENT '主键',
        type VARCHAR(32) COMMENT '业务类型',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        user_name VARCHAR(128) COMMENT '用户名',
        id_card VARCHAR(64) COMMENT '身份证号',
        network_access_time VARCHAR(32) COMMENT '入网时间',
        online_duration VARCHAR(16) COMMENT '在网时长',
        operator_real VARCHAR(16) COMMENT '运营商',
        order_no VARCHAR(64) COMMENT '订单号',
        store_name VARCHAR(256) COMMENT '门店名称',
        store_id VARCHAR(64) COMMENT '门店编码',
        first_risk_result VARCHAR(64) COMMENT '初审结果',
        second_risk_result VARCHAR(64) COMMENT '复审结果',
        strategy_id VARCHAR(32) COMMENT '策略ID',
        recall_strategy VARCHAR(32) COMMENT '捞回策略',
        order_id VARCHAR(64) COMMENT '订单ID',
        pass_flag VARCHAR(8) COMMENT '通过标记',
        refuse_sum VARCHAR(8) COMMENT '拒绝次数',
        guarantee_amount INT COMMENT '保证金金额',
        add_time DATETIME COMMENT '添加时间',
        update_time DATETIME COMMENT '更新时间',
        remarks TEXT COMMENT '备注',
        meur_name VARCHAR(128) COMMENT 'MEUR名称',
        store_level VARCHAR(32) COMMENT '门店级别',
        INDEX idx_order_no (order_no),
        INDEX idx_store_id (store_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风控结果表'
    """,
)

ODS_GRANT_APPLY_TABLE = DDLEntry(
    schema_name="ods",
    table_name="ods_ts_credit_yzf_order_grant_apply",
    description="授信申请表",
    row_estimate=2_310_465,
    batch_size=10000,
    ddl="""
    CREATE TABLE IF NOT EXISTS ods.ods_ts_credit_yzf_order_grant_apply (
        id BIGINT PRIMARY KEY COMMENT '主键',
        ct_user_id VARCHAR(64) COMMENT '用户ID(关联风控表)',
        user_name VARCHAR(128) COMMENT '用户名',
        mobile_no VARCHAR(32) COMMENT '手机号',
        id_number VARCHAR(64) COMMENT '身份证号',
        change_mobile VARCHAR(32) COMMENT '换号',
        id_type VARCHAR(16) COMMENT '证件类型',
        nation VARCHAR(16) COMMENT '民族',
        education VARCHAR(32) COMMENT '学历',
        bank_no VARCHAR(64) COMMENT '银行卡号',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        business_type VARCHAR(8) COMMENT '业务类型',
        store_id VARCHAR(64) COMMENT '门店编码',
        store_name VARCHAR(256) COMMENT '门店名称',
        supplier_code VARCHAR(32) COMMENT '代理商编码',
        seller_name VARCHAR(64) COMMENT '营业员',
        apply_time DATETIME COMMENT '申请时间',
        apply_status VARCHAR(32) COMMENT '申请状态',
        apply_msg TEXT COMMENT '申请结果描述',
        INDEX idx_ct_user_id (ct_user_id),
        INDEX idx_store_id (store_id),
        INDEX idx_supplier_code (supplier_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='授信申请表'
    """,
)

ODS_ORDER_COMPLETE_TABLE = DDLEntry(
    schema_name="ods",
    table_name="ods_ts_credit_yzf_order_info_complete",
    description="订单竣工表",
    row_estimate=1_515_653,
    batch_size=10000,
    ddl="""
    CREATE TABLE IF NOT EXISTS ods.ods_ts_credit_yzf_order_info_complete (
        id BIGINT PRIMARY KEY COMMENT '主键',
        order_no VARCHAR(64) COMMENT '订单号',
        ct_user_id VARCHAR(64) COMMENT '用户ID',
        user_name VARCHAR(128) COMMENT '用户名',
        id_card VARCHAR(64) COMMENT '身份证号',
        pack_name VARCHAR(256) COMMENT '套餐名称',
        pack_price INT COMMENT '套餐价格(分)',
        goods_name VARCHAR(256) COMMENT '商品名称',
        goods_price INT COMMENT '商品价格(分)',
        order_status VARCHAR(32) COMMENT '订单状态',
        complete_time DATETIME COMMENT '竣工时间',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        store_id VARCHAR(64) COMMENT '门店编码',
        store_name VARCHAR(256) COMMENT '门店名称',
        supplier_code VARCHAR(32) COMMENT '代理商编码',
        order_amt INT COMMENT '订单金额(分)',
        order_type VARCHAR(32) COMMENT '订单类型',
        INDEX idx_order_no (order_no),
        INDEX idx_ct_user_id (ct_user_id),
        INDEX idx_supplier_code (supplier_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单竣工表'
    """,
)

ODS_REPAYMENT_TABLE = DDLEntry(
    schema_name="ods",
    table_name="ods_ts_credit_yzf_order_repayment",
    description="还款明细表",
    row_estimate=50_530_527,
    batch_size=20000,
    ddl="""
    CREATE TABLE IF NOT EXISTS ods.ods_ts_credit_yzf_order_repayment (
        id BIGINT PRIMARY KEY COMMENT '主键',
        order_id INT COMMENT '订单ID',
        order_no VARCHAR(64) COMMENT '订单号',
        instalment_num INT COMMENT '当前期数',
        due_principal INT COMMENT '应还本金(分)',
        due_date VARCHAR(16) COMMENT '应还日期',
        principal INT COMMENT '实还本金(分)',
        interest INT COMMENT '利息(分)',
        penalty INT COMMENT '罚金(分)',
        amt INT COMMENT '实还总金额(分)',
        repay_date VARCHAR(16) COMMENT '实还日期',
        status VARCHAR(32) COMMENT '还款状态',
        type VARCHAR(8) COMMENT '还款类型',
        INDEX idx_order_no (order_no),
        INDEX idx_due_date (due_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='还款明细表'
    """,
)

# ════════════════════════════════════════════════════════════════
#  DWS 层 — 汇总宽表
# ════════════════════════════════════════════════════════════════

DWS_ORDER_COMPLETE_TABLE = DDLEntry(
    schema_name="dws",
    table_name="dws_credit_yzf_order_complete",
    description="订单+还款汇总宽表",
    row_estimate=1_393_089,
    batch_size=10000,
    ddl="""
    CREATE TABLE IF NOT EXISTS dws.dws_credit_yzf_order_complete (
        order_no VARCHAR(64) NOT NULL COMMENT '订单号',
        id_card_name VARCHAR(128) COMMENT '客户姓名',
        ct_user_id VARCHAR(64) COMMENT '用户ID',
        order_status VARCHAR(32) COMMENT '订单状态',
        step_num_repay_status INT COMMENT '当期状态(0无需还/1已还/2未还)',
        complete_time DATE COMMENT '竣工日期',
        order_amt_yuan DECIMAL(16,2) COMMENT '订单金额(元)',
        pack_name VARCHAR(256) COMMENT '套餐名称',
        store_id VARCHAR(64) COMMENT '门店编码',
        store_name VARCHAR(256) COMMENT '门店名称',
        supplier_code VARCHAR(32) COMMENT '代理商编码',
        supplier_name VARCHAR(256) COMMENT '代理商名称',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        custtype VARCHAR(8) COMMENT '客户类型',
        age INT COMMENT '年龄',
        operator_real VARCHAR(16) COMMENT '运营商',
        old_new_customer VARCHAR(16) COMMENT '新老客户',
        total_due_count INT COMMENT '应还总次数',
        total_repaid_count INT COMMENT '已还次数',
        due_principal INT COMMENT '应还本金(分)',
        principal INT COMMENT '实还本金(分)',
        due_date VARCHAR(16) COMMENT '应还日期',
        repay_status VARCHAR(32) COMMENT '还款状态',
        order_amt INT COMMENT '订单金额(分)',
        store_addr_province VARCHAR(64) COMMENT '门店地址省',
        store_addr_city VARCHAR(64) COMMENT '门店地址市',
        order_channel_id VARCHAR(64) COMMENT '订单渠道',
        source_business_type VARCHAR(32) COMMENT '业务来源',
        PRIMARY KEY (order_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单+还款汇总宽表'
    """,
)

# ════════════════════════════════════════════════════════════════
#  汇总注册表
# ════════════════════════════════════════════════════════════════

ALL_TABLES = [
    ODS_STORE_TABLE,
    ODS_RISK_TABLE,
    ODS_GRANT_APPLY_TABLE,
    ODS_ORDER_COMPLETE_TABLE,
    ODS_REPAYMENT_TABLE,
    DWS_ORDER_COMPLETE_TABLE,
]


def get_tables_by_schema(schema: str = None) -> list:
    """按层筛选"""
    if schema:
        return [t for t in ALL_TABLES if t.schema_name == schema]
    return ALL_TABLES


def get_table(table_name: str) -> DDLEntry:
    """按表名查找"""
    matches = [t for t in ALL_TABLES if t.table_name == table_name]
    return matches[0] if matches else None


def get_starrocks_mapping(table_name: str) -> str:
    """获取 StarRocks 源表全名"""
    mapping = {
        "ods_ts_v3_order_store": "ods.ods_ts_v3_order_store",
        "ods_ts_order_white_list_control": "ods.ods_ts_order_white_list_control",
        "ods_ts_credit_yzf_order_grant_apply": "ods.ods_ts_credit_yzf_order_grant_apply",
        "ods_ts_credit_yzf_order_info_complete": "ods.ods_ts_credit_yzf_order_info_complete",
        "ods_ts_credit_yzf_order_repayment": "ods.ods_ts_credit_yzf_order_repayment",
        "dws_credit_yzf_order_complete": "dws.dws_credit_yzf_order_complete",
    }
    return mapping.get(table_name, table_name)
