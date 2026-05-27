"""
后端侧 - 套餐评级表 ORM 模型
"""

from sqlalchemy import DATE, DECIMAL, INT, VARCHAR, Column

from backend.database.orm.base import Base


class PackageEvaluation(Base):
    __tablename__ = "package_evaluation"

    pack_name = Column(VARCHAR(256), primary_key=True)
    data_date = Column(DATE, primary_key=True)
    province = Column(VARCHAR(64))

    total_transaction_count = Column(INT)
    num_overdue_rate = Column(DECIMAL(6, 5))
    unsubscribe_rate = Column(DECIMAL(6, 5))
    risk_pass_rate = Column(DECIMAL(6, 5))
    active_months = Column(INT)

    old_customer_count = Column(INT)
    new_customer_count = Column(INT)

    compliance_score = Column(DECIMAL(5, 2))
    package_rating = Column(VARCHAR(4))

    def to_dict(self) -> dict:
        return {
            "pack_name": self.pack_name,
            "province": self.province,
            "compliance_score": float(self.compliance_score) if self.compliance_score else None,
            "package_rating": self.package_rating,
            "num_overdue_rate": float(self.num_overdue_rate) if self.num_overdue_rate else None,
            "total_transaction_count": self.total_transaction_count,
            "data_date": str(self.data_date) if self.data_date else None,
        }
