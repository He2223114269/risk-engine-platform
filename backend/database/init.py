#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : init
功能描述 : 数据库初始化脚本 — 一键建表 + 播种基础数据

用法:
    # 使用默认配置（读取 .env 或环境变量）
    python -m backend.database.init

    # 指定连接字符串
    DATABASE_URL="mysql+pymysql://root:222311@localhost:3306/risk_control" \\
        python -m backend.database.init

    # 仅查看已注册表，不执行建表
    python -m backend.database.init --dry-run

============================================================================
"""

from __future__ import annotations

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("db_init")


def main():
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅查看注册的表，不实际建表",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="是否插入基础种子数据",
    )
    args = parser.parse_args()

    from backend.database import _import_all_models
    from backend.database.orm.base import Base

    _import_all_models()

    tables = sorted(Base.metadata.tables.keys())
    print(f"\n{'='*50}")
    print("  数据库初始化工具")
    print(f"{'='*50}")
    print(f"\n已注册 {len(tables)} 张表:")
    for t in tables:
        print(f"  ✔ {t}")

    if args.dry_run:
        print("\n[DRY RUN] 未执行任何操作\n")
        return

    # 真实建表
    from backend.database import engine

    Base.metadata.create_all(bind=engine)

    print("\n✅ 建表完成")

    # 种子数据（可选）
    if args.seed:
        _seed_data()

    print()


def _seed_data():
    """播种基础数据（通过率参数等）"""
    from sqlalchemy import text

    from backend.config.settings import BackendSettings
    from backend.database import SessionLocal

    settings = BackendSettings()
    # 只在 MySQL 下播种
    if "mysql" not in settings.DATABASE_URL:
        return

    db = SessionLocal()
    try:
        # 检查是否已有数据
        result = db.execute(text("SELECT COUNT(*) FROM risk_parameter_pass_radio"))
        if result.scalar() > 0:
            return

        logger.info("播种通过率参数...")
        db.execute(text("""
            INSERT INTO risk_parameter_pass_radio (province, pass_rate) VALUES
            ('湖南省', 55.0), ('贵州省', 70.0), ('甘肃省', 70.0),
            ('江苏省', 40.0), ('安徽省', 55.0), ('江西省', 50.0),
            ('海南省', 60.0), ('宁夏回族自治区', 50.0), ('青海省', 50.0)
        """))
        db.commit()
        logger.info("✅ 基础数据播种完成")
    except Exception as e:
        db.rollback()
        logger.warning(f"播种跳过: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
