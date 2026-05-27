#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : sync_models
功能描述 : 同步表 ORM 模型 — 从 StarRocks 同步到本地的各层数据表
          只读模型（不用于写入，写入由 sync 引擎负责）

用法:
    from backend.database.orm.sync_models import OdOrderComplete
    rows = session.query(OdOrderComplete).limit(10).all()

创建日期 : 2026-05-26
版本     : v1.0.0
============================================================================
"""

from sqlalchemy import DECIMAL, BigInteger, Column, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

SyncBase = declarative_base()


# ════════════════════════════════════════════════════════════════
#  ODS 层 — 原始数据
# ════════════════════════════════════════════════════════════════


class OdV3OrderStore(SyncBase):
    """门店等级表"""

    __tablename__ = "ods_ts_v3_order_store"
    __table_args__ = {"schema": "ods"}

    id = Column(BigInteger, primary_key=True)
    isv = Column(String(32))
    type = Column(String(32))
    province = Column(String(64))
    city = Column(String(64))
    store_code = Column(String(64))
    store_name = Column(String(256))
    channel_level = Column(String(32))
    notes = Column(Text)
    add_time = Column(DateTime)
    update_time = Column(DateTime)


class OdOrderWhiteListControl(SyncBase):
    """风控结果表"""

    __tablename__ = "ods_ts_order_white_list_control"
    __table_args__ = {"schema": "ods"}

    id = Column(BigInteger, primary_key=True)
    type = Column(String(32))
    province = Column(String(64))
    city = Column(String(64))
    order_no = Column(String(64))
    store_name = Column(String(256))
    store_id = Column(String(64))
    first_risk_result = Column(String(64))
    second_risk_result = Column(String(64))
    strategy_id = Column(String(32))
    recall_strategy = Column(String(32))
    operator_real = Column(String(16))
    online_duration = Column(String(16))
    pass_flag = Column(String(8))
    add_time = Column(DateTime)
    update_time = Column(DateTime)


class OdGrantApply(SyncBase):
    """授信申请表"""

    __tablename__ = "ods_ts_credit_yzf_order_grant_apply"
    __table_args__ = {"schema": "ods"}

    id = Column(BigInteger, primary_key=True)
    ct_user_id = Column(String(64))
    user_name = Column(String(128))
    mobile_no = Column(String(32))
    id_number = Column(String(64))
    province = Column(String(64))
    city = Column(String(64))
    business_type = Column(String(8))
    store_id = Column(String(64))
    store_name = Column(String(256))
    supplier_code = Column(String(32))
    seller_name = Column(String(64))
    apply_time = Column(DateTime)
    apply_status = Column(String(32))
    apply_msg = Column(Text)


class OdOrderComplete(SyncBase):
    """订单竣工表"""

    __tablename__ = "ods_ts_credit_yzf_order_info_complete"
    __table_args__ = {"schema": "ods"}

    id = Column(BigInteger, primary_key=True)
    order_no = Column(String(64))
    ct_user_id = Column(String(64))
    pack_name = Column(String(256))
    order_status = Column(String(32))
    complete_time = Column(DateTime)
    province = Column(String(64))
    city = Column(String(64))
    store_id = Column(String(64))
    store_name = Column(String(256))
    supplier_code = Column(String(32))
    order_amt = Column(Integer)
    order_type = Column(String(32))


class OdRepayment(SyncBase):
    """还款明细表"""

    __tablename__ = "ods_ts_credit_yzf_order_repayment"
    __table_args__ = {"schema": "ods"}

    id = Column(BigInteger, primary_key=True)
    order_id = Column(Integer)
    order_no = Column(String(64))
    instalment_num = Column(Integer)
    due_principal = Column(Integer)
    due_date = Column(String(16))
    principal = Column(Integer)
    interest = Column(Integer)
    amt = Column(Integer)
    repay_date = Column(String(16))
    status = Column(String(32))
    type = Column(String(8))


# ════════════════════════════════════════════════════════════════
#  DWS 层 — 汇总宽表
# ════════════════════════════════════════════════════════════════


class DwsOrderComplete(SyncBase):
    """订单+还款汇总宽表"""

    __tablename__ = "dws_credit_yzf_order_complete"
    __table_args__ = {"schema": "dws"}

    order_no = Column(String(64), primary_key=True)
    id_card_name = Column(String(128))
    ct_user_id = Column(String(64))
    order_status = Column(String(32))
    step_num_repay_status = Column(Integer)
    complete_time = Column(Date)
    order_amt_yuan = Column(DECIMAL(16, 2))
    pack_name = Column(String(256))
    store_id = Column(String(64))
    store_name = Column(String(256))
    supplier_code = Column(String(32))
    supplier_name = Column(String(256))
    province = Column(String(64))
    city = Column(String(64))
    custtype = Column(String(8))
    operator_real = Column(String(16))
    old_new_customer = Column(String(16))
    due_principal = Column(Integer)
    principal = Column(Integer)
    due_date = Column(String(16))
    repay_status = Column(String(32))
    order_amt = Column(Integer)
    source_business_type = Column(String(32))
