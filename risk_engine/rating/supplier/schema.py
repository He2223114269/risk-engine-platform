"""
风险引擎侧 - 代理商评级数据契约
================================

这张文件不是 ORM 模型，是风控引擎写入 supplier_evaluation 表时的"数据契约"：
它只声明 run.py 需要写入哪些字段，不关心完整的 DDL。

与 backend/database/orm/supplier_rating.py 的关系：
  两者指向同一张 MySQL 表，物理上分离，逻辑上对齐。

变更说明：
  如果这里加了字段，后端 ORM 需要同步加（通过代码审查保证）。
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date, datetime


@dataclass
class SupplierEvaluation:
    """
    代理商评价数据 — 写入侧契约

    字段 = supplier_evaluation 表的 subset（写入方关心的字段）
    """

    # ── 主键 ──
    supplier_id: str

    # ── 基本信息 ──
    supplier_name: Optional[str] = None
    province: Optional[str] = None
    cooperate_status: Optional[str] = "正常"

    # ── 展业稳定性（权重 10%） ──
    business_start_date: Optional[date] = None
    last_active_date: Optional[date] = None
    business_duration_days: Optional[int] = None
    active_months: Optional[int] = None
    recent_inactive_days: Optional[int] = None

    # ── 规模体量（权重 12%） ──
    store_count: Optional[int] = None
    staff_count: Optional[int] = None
    high_quality_store_count: Optional[int] = None
    regulated_store_count: Optional[int] = None

    # ── 翼支付评级（权重 10%） ──
    yzf_rating: Optional[str] = None
    previous_rating: Optional[str] = None
    yzf_rating_trend: Optional[str] = None

    # ── 交易活跃度 ──
    total_transaction_amount: Optional[float] = None
    total_transaction_count: Optional[int] = None
    monthly_avg_amount: Optional[float] = None
    last_month_amount: Optional[float] = None
    amount_growth_rate: Optional[float] = None

    # ── 逾期与坏账（权重 40%） ──
    amt_overdue_rate: Optional[float] = None
    num_overdue_rate: Optional[float] = None
    overdue_order_count: Optional[int] = None
    overdue_amount: Optional[float] = None
    bad_debt_rate: Optional[float] = None

    # ── 客群结构（权重 15%） ──
    new_customer_count: Optional[int] = None
    old_customer_count: Optional[int] = None
    local_network_count: Optional[int] = None
    external_network_count: Optional[int] = None
    single_card_count: Optional[int] = None
    fusion_count: Optional[int] = None

    # ── 退订 ──
    unsubscribe_rate: Optional[float] = None

    # ── 风控通过率异常（权重 5%） ──
    risk_pass_rate: Optional[float] = None
    risk_pass_rate_deviation: Optional[float] = None

    # ── 风险合规 ──
    penalty_count: Optional[int] = None
    compliance_score: Optional[float] = None
    supplier_rating: Optional[str] = None

    # ── 审计 ──
    data_date: Optional[date] = None


def df_to_records(df, data_date: date) -> list[dict]:
    """
    将 extract.py 返回的 DataFrame 转换为 schema 格式的字典列表。

    参数:
        df: extract.py 提数后的原始 DataFrame
        data_date: 数据截止日期

    返回:
        list[dict]，每个 dict 的 key 对应 supplier_evaluation 表的列名
    """
    records = []
    for _, row in df.iterrows():
        record = SupplierEvaluation(
            supplier_id=row.get("supplier_code"),
            supplier_name=row.get("supplier_name"),
            province=row.get("province"),
            # extract 阶段只填充原始维度，评分字段由 score.py 填充
            data_date=data_date,
        )
        # 只把非 None 的字段写入 dict
        records.append({k: v for k, v in record.__dict__.items() if v is not None})
    return records
