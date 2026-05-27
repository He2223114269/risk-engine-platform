"""套餐评级 - 写入侧数据契约"""

from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class PackageEvaluation:
    pack_name: str
    province: Optional[str] = None
    business_start_date: Optional[date] = None
    last_active_date: Optional[date] = None
    active_months: Optional[int] = None
    total_transaction_count: Optional[int] = None
    total_transaction_amount: Optional[float] = None
    monthly_avg_count: Optional[float] = None
    new_customer_count: Optional[int] = None
    old_customer_count: Optional[int] = None
    local_network_count: Optional[int] = None
    external_network_count: Optional[int] = None
    single_card_count: Optional[int] = None
    fusion_count: Optional[int] = None
    num_overdue_rate: Optional[float] = None
    unsubscribe_rate: Optional[float] = None
    risk_pass_rate: Optional[float] = None
    compliance_score: Optional[float] = None
    package_rating: Optional[str] = None
    data_date: Optional[date] = None
