"""
门店评级 - 写入侧数据契约
========================

与 backend/database/orm/store_rating.py 指向同一张 MySQL 表。
此文件声明 run.py 需要写入哪些字段，不关心完整 DDL。
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class StoreEvaluation:
    """门店评价数据 — 写入侧契约"""

    store_id: str

    # ── 基本信息 ──
    store_name: str | None = None
    province: str | None = None
    city: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None

    # ── 经营基础 ──
    business_start_date: date | None = None
    last_active_date: date | None = None
    business_duration_days: int | None = None
    active_months: int | None = None
    recent_inactive_days: int | None = None
    total_transaction_count: int | None = None
    total_transaction_amount: float | None = None
    monthly_avg_amount: float | None = None
    last_month_amount: float | None = None
    amount_growth_rate: float | None = None

    # ── 客群质量 ──
    new_customer_count: int | None = None
    old_customer_count: int | None = None
    local_network_count: int | None = None
    external_network_count: int | None = None
    single_card_count: int | None = None
    fusion_count: int | None = None

    # ── 资产质量 ──
    num_overdue_rate: float | None = None
    overdue_order_count: int | None = None
    matured_order_count: int | None = None
    unsubscribe_rate: float | None = None
    bad_debt_rate: float | None = None

    # ── 风控通过率 ──
    risk_pass_rate: float | None = None
    risk_pass_rate_deviation: float | None = None

    # ── 渠道关联 ──
    channel_level: str | None = None
    supplier_rating: str | None = None
    penalty_count: int | None = None

    # ── 经营健康度 ──
    volume_cv: float | None = None
    month_end_ratio: float | None = None

    # ── 趋势 ──
    overdue_trend: float | None = None
    new_customer_trend: float | None = None

    # ── 评分输出 ──
    compliance_score: float | None = None
    store_rating: str | None = None

    # ── 审计 ──
    data_date: date | None = None
