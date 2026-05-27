#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : settings
功能描述 : 后端服务全局配置 — pydantic-settings 环境变量驱动
          包含 API 服务、数据库、Redis、Kafka、可观测性等配置
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
更新历史 :
  2026-05-26, Jingluo, v0.2.0 — 添加 MySQL 数据库配置，支持建表开关
============================================================================
"""

from __future__ import annotations

from pydantic_settings import BaseSettings

__all__ = ["BackendSettings"]


class BackendSettings(BaseSettings):
    """后端服务配置"""

    # ── 环境 ──
    ENV: str = "dev"  # dev / test / staging / prod
    DEBUG: bool = True

    # ── API 服务 ──
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_TIMEOUT_SECONDS: int = 30

    # ── 数据库（连接字符串，支持 mysql / sqlite 切换） ──
    # MySQL: mysql+pymysql://root:222311@localhost:3306/risk_control
    # SQLite: sqlite:///./data/backend.db
    DATABASE_URL: str = "mysql+pymysql://root:222311@localhost:3306/risk_control"
    DATABASE_ECHO: bool = False

    # 启动时是否自动建表（生产环境建议 False，用 Alembic 迁移）
    DATABASE_AUTO_CREATE_TABLES: bool = True

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Kafka ──
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_DECISION_TOPIC: str = "risk_engine.decisions"

    # ── 可观测性 ──
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9090
    JAEGER_AGENT_HOST: str = "localhost"
    JAEGER_AGENT_PORT: int = 6831

    # ── 告警 ──
    ALERT_CHANNELS: list[str] = ["dingtalk", "email", "wechat"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
