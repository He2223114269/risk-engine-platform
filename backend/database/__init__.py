#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : database
功能描述 : 数据库层 — 引擎管理、ORM 模型、表初始化、Alembic 迁移入口

用法:
    from backend.database import engine, SessionLocal, init_db

    # 程序启动时建表
    init_db()

    # 增删改查
    with SessionLocal() as db:
        rows = db.query(SomeModel).all()

环境变量覆盖:
    DATABASE_URL=mysql+pymysql://root:222311@localhost:3306/risk_control
    DATABASE_ECHO=true

创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.2.0
更新历史 :
  2026-05-26, Jingluo, v0.2.0 — 引擎管理标准化，支持自动建表
============================================================================
"""

from __future__ import annotations

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from backend.config.settings import BackendSettings
from backend.database.orm.base import Base

__all__ = [
    "engine",
    "SessionLocal",
    "init_db",
    "check_db_connection",
]

logger = logging.getLogger(__name__)

# ── 加载配置 ──
_settings = BackendSettings()

# ── 创建引擎 ──
engine = create_engine(
    _settings.DATABASE_URL,
    echo=_settings.DATABASE_ECHO,
    pool_pre_ping=True,          # 连接前检查可用性
    pool_recycle=3600,           # 一小时后回收连接
    pool_size=10,                # 连接池大小
    max_overflow=20,             # 最大溢出连接数
)

# ── 会话工厂 ──
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)


def init_db():
    """
    数据库初始化 — 建表 + 基础数据播种。

    流程:
        1. 检查数据库连接
        2. 如果 DATABASE_AUTO_CREATE_TABLES=True，自动建表
        3. 打印建表结果

    用法:
        from backend.database import init_db
        init_db()
    """
    logger.info("初始化数据库...")

    # 1. 检查连接
    check_db_connection()

    # 2. 自动建表
    if _settings.DATABASE_AUTO_CREATE_TABLES:
        logger.info("正在创建数据库表...")
        # 导入所有 ORM 模型确保它们被 Base 注册
        _import_all_models()
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表创建完成")

        # 打印已建表清单
        _print_tables()
    else:
        logger.info("已跳过自动建表（DATABASE_AUTO_CREATE_TABLES=False）")


def check_db_connection():
    """检查数据库连接是否正常。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"✅ 数据库连接正常: {_settings.DATABASE_URL}")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise


def _import_all_models():
    """
    导入所有 ORM 模型模块，确保被 Base.metadata 注册。
    
    每新增 ORM 模型文件，需要在这里加一行 import，
    否则 create_all 不会创建该表。
    """
    # 导入各 ORM 模型（按需添加）
    import backend.database.orm.supplier_rating  # noqa: F401
    import backend.database.orm.store_rating      # noqa: F401
    import backend.database.orm.package_rating    # noqa: F401


def _print_tables():
    """打印已注册的表清单"""
    tables = sorted(Base.metadata.tables.keys())
    logger.info(f"已注册 {len(tables)} 张表:")
    for t in tables:
        logger.info(f"  - {t}")


def get_db():
    """
    FastAPI 依赖注入 — 获取数据库会话。

    用法:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
