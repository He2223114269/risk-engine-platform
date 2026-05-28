#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : settings
功能描述 : 风控引擎全局配置 — pydantic-settings 环境变量驱动
          支持 .env 文件覆盖，禁止硬编码配置值
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

from __future__ import annotations

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # 未安装 pydantic-settings 时降级（Windows 常见）
    from pydantic import BaseSettings


__all__ = ["RiskEngineSettings"]


class RiskEngineSettings(BaseSettings):
    """风控引擎配置"""

    # 环境
    ENV: str = "dev"  # dev / test / staging / prod

    # 数据库连接
    STARROCKS_HOST: str = "localhost"
    STARROCKS_PORT: int = 9030
    STARROCKS_USER: str = ""
    STARROCKS_PASSWORD: str = ""
    STARROCKS_DATABASE: str = ""

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # 模型
    MODEL_STORAGE_PATH: str = "./data/models"

    # 监控阈值
    PSI_THRESHOLD: float = 0.1
    NULL_RATE_THRESHOLD: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
