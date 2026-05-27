"""
门店评级 - 写入侧数据契约
========================

与 backend/database/orm/store_rating.py 指向同一张 MySQL 表。
此文件声明 run.py 需要写入哪些字段，不关心完整 DDL。
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class StoreEvaluation:
    """门店评价数据 — 写入侧契约"""

    store_id: str

    # ── 基本信息 ──
    store_name: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_name: Optional[str] = None

    # ── 经营基础 ──
    business_start_date: Optional[date] = None
    last_active_date: Optional[date] = None
    business_duration_days: Optional[int] = None
    active_months: Optional[int] = None
    recent_inactive_days: Optional[int] = None
    total_transaction_count: Optional[int] = None
    total_transaction_amount: Optional[float] = None
    monthly_avg_amount: Optional[float] = None
    last_month_amount: Optional[float] = None
    amount_growth_rate: Optional[float] = None

    # ── 客群质量 ──
    new_customer_count: Optional[int] = None
    old_customer_count: Optional[int] = None
    local_network_count: Optional[int] = None
    external_network_count: Optional[int] = None
    single_card_count: Optional[int] = None
    fusion_count: Optional[int] = None

    # ── 资产质量 ──
    num_overdue_rate: Optional[float] = None
    overdue_order_count: Optional[int] = None
    matured_order_count: Optional[int] = None
    unsubscribe_rate: Optional[float] = None
    bad_debt_rate: Optional[float] = None

    # ── 风控通过率 ──
    risk_pass_rate: Optional[float] = None
    risk_pass_rate_deviation: Optional[float] = None

    # ── 渠道关联 ──
    channel_level: Optional[str] = None
    supplier_rating: Optional[str] = None
    penalty_count: Optional[int] = None

    # ── 经营健康度 ──
    volume_cv: Optional[float] = None
    month_end_ratio: Optional[float] = None

    # ── 趋势 ──
    overdue_trend: Optional[float] = None
    new_customer_trend: Optional[float] = None

    # ── 评分输出 ──
    compliance_score: Optional[float] = None
    store_rating: Optional[str] = None

    # ── 审计 ──
    data_date: Optional[date] = None
