"""
后端侧 - 门店评级表 ORM 模型
================================
"""

from sqlalchemy import Column, String, Integer, Date, Text, VARCHAR, INT, DECIMAL, DATE

from backend.database.orm.base import Base


class StoreEvaluation(Base):
    __tablename__ = "store_evaluation"

    store_id = Column(VARCHAR(64), primary_key=True)
    data_date = Column(DATE, primary_key=True)
    store_name = Column(VARCHAR(256))
    province = Column(VARCHAR(64))
    city = Column(VARCHAR(64))
    supplier_code = Column(VARCHAR(32))
    supplier_name = Column(VARCHAR(256))

    business_start_date = Column(DATE)
    last_active_date = Column(DATE)
    business_duration_days = Column(INT)
    active_months = Column(INT)
    recent_inactive_days = Column(INT)

    total_transaction_count = Column(INT)
    total_transaction_amount = Column(DECIMAL(16, 2))
    monthly_avg_amount = Column(DECIMAL(16, 2))
    last_month_amount = Column(DECIMAL(16, 2))
    amount_growth_rate = Column(DECIMAL(8, 4))

    new_customer_count = Column(INT)
    old_customer_count = Column(INT)
    local_network_count = Column(INT)
    external_network_count = Column(INT)
    single_card_count = Column(INT)
    fusion_count = Column(INT)

    num_overdue_rate = Column(DECIMAL(6, 5))
    overdue_order_count = Column(INT)
    matured_order_count = Column(INT)
    unsubscribe_rate = Column(DECIMAL(6, 5))

    risk_pass_rate = Column(DECIMAL(6, 5))
    risk_pass_rate_deviation = Column(DECIMAL(6, 5))

    channel_level = Column(VARCHAR(32))
    supplier_rating = Column(VARCHAR(4))
    penalty_count = Column(INT, default=0)

    compliance_score = Column(DECIMAL(5, 2))
    store_rating = Column(VARCHAR(4))
