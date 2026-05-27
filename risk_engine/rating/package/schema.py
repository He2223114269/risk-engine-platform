"""套餐评级 - 写入侧数据契约"""

from dataclasses import dataclass
from datetime import date


@dataclass
class PackageEvaluation:
    pack_name: str
    province: str | None = None
    business_start_date: date | None = None
    last_active_date: date | None = None
    active_months: int | None = None
    total_transaction_count: int | None = None
    total_transaction_amount: float | None = None
    monthly_avg_count: float | None = None
    new_customer_count: int | None = None
    old_customer_count: int | None = None
    local_network_count: int | None = None
    external_network_count: int | None = None
    single_card_count: int | None = None
    fusion_count: int | None = None
    num_overdue_rate: float | None = None
    unsubscribe_rate: float | None = None
    risk_pass_rate: float | None = None
    compliance_score: float | None = None
    package_rating: str | None = None
    data_date: date | None = None
