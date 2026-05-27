"""
后端侧 - 代理商评级表 ORM 模型
================================

这是 supplier_evaluation 表的 SQLAlchemy ORM 模型定义，
供后端 API 查询使用。

与 risk_engine/rating/supplier/schema.py 的关系：
  两者指向同一张 MySQL 表，物理上分离，逻辑上对齐。

变更说明：
  如果后端 API 需要读取新字段，先在这里加定义，
  同时通知风控引擎侧同步 schema.py。
"""

from sqlalchemy import (
    DATE,
    DATETIME,
    DECIMAL,
    INT,
    VARCHAR,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from backend.database.orm.base import Base


class SupplierEvaluation(Base):
    """代理商评价数据表 ORM 模型"""

    __tablename__ = "supplier_evaluation"
    __table_args__ = {"comment": "代理商综合评价数据表 v2.0 — 保障金评级用"}

    # ── 主键 ──
    supplier_id = Column(VARCHAR(32), primary_key=True, comment="代理商唯一编码")

    # ── 基本信息 ──
    supplier_name = Column(VARCHAR(128), comment="代理商名称")
    province = Column(VARCHAR(64), comment="省份")
    cooperate_status = Column(VARCHAR(16), default="正常", comment="合作状态（正常/暂停/终止）")

    # ── 展业稳定性 ──
    business_start_date = Column(DATE, comment="首次展业时间")
    last_active_date = Column(DATE, comment="最后一次展业时间")
    business_duration_days = Column(INT, comment="已展业天数")
    active_months = Column(INT, comment="活跃月份数")
    recent_inactive_days = Column(INT, comment="距最后一次展业天数")

    # ── 规模指标 ──
    store_count = Column(INT, comment="门店总数")
    staff_count = Column(INT, comment="营业员人数")
    high_quality_store_count = Column(INT, comment="优质门店数")
    regulated_store_count = Column(INT, comment="监管门店数")

    # ── 翼支付评级 ──
    yzf_rating = Column(VARCHAR(16), comment="翼支付评级（A/B/C/D/E）")
    previous_rating = Column(VARCHAR(16), comment="上一期翼支付评级")
    yzf_rating_trend = Column(VARCHAR(8), comment="评级变化趋势")

    # ── 交易活跃度 ──
    total_transaction_amount = Column(DECIMAL(16, 2), comment="历史累计交易总额")
    total_transaction_count = Column(INT, comment="历史累计交易笔数")
    monthly_avg_amount = Column(DECIMAL(16, 2), comment="近6个月月均交易额")
    last_month_amount = Column(DECIMAL(16, 2), comment="最近一个月交易额")
    amount_growth_rate = Column(DECIMAL(8, 4), comment="交易额环比增速")

    # ── 逾期与坏账 ──
    amt_overdue_rate = Column(DECIMAL(6, 5), comment="金额逾期率")
    num_overdue_rate = Column(DECIMAL(6, 5), comment="订单逾期率")
    overdue_order_count = Column(INT, comment="逾期订单数")
    overdue_amount = Column(DECIMAL(16, 2), comment="逾期未还总金额")
    bad_debt_rate = Column(DECIMAL(6, 5), comment="坏账率")

    # ── 客群结构 ──
    new_customer_count = Column(INT, comment="新客数")
    old_customer_count = Column(INT, comment="老客数")
    local_network_count = Column(INT, comment="本网客户数")
    external_network_count = Column(INT, comment="异网客户数")
    single_card_count = Column(INT, comment="单卡客户数")
    fusion_count = Column(INT, comment="融合客户数")

    # ── 退订 ──
    unsubscribe_rate = Column(DECIMAL(6, 5), comment="退订率")

    # ── 风控通过率 ──
    risk_pass_rate = Column(DECIMAL(6, 5), comment="风控通过率（剔除保证金白名单+特批白名单）")
    risk_pass_rate_deviation = Column(
        DECIMAL(6, 5), comment="风控通过率偏离度（该代理商 - 全省均值）"
    )

    # ── 风险合规 ──
    penalty_count = Column(INT, comment="违规处罚次数")
    compliance_score = Column(DECIMAL(5, 2), comment="合规评分（0~100分）")
    supplier_rating = Column(VARCHAR(4), comment="最终评级（A/B/C）")

    # ── 审计 ──
    data_date = Column(DATE, comment="数据截止日期")
    remark = Column(Text, comment="备注")
    update_time = Column(
        DATETIME,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="最后更新时间",
    )

    def to_dict(self) -> dict:
        """转换为 API 返回用的字典"""
        return {
            "supplier_id": self.supplier_id,
            "province": self.province,
            "compliance_score": float(self.compliance_score) if self.compliance_score else None,
            "supplier_rating": self.supplier_rating,
            "yzf_rating": self.yzf_rating,
            "amt_overdue_rate": float(self.amt_overdue_rate) if self.amt_overdue_rate else None,
            "num_overdue_rate": float(self.num_overdue_rate) if self.num_overdue_rate else None,
            "store_count": self.store_count,
            "total_transaction_count": self.total_transaction_count,
            "active_months": self.active_months,
            "data_date": str(self.data_date) if self.data_date else None,
            "update_time": str(self.update_time) if self.update_time else None,
        }
