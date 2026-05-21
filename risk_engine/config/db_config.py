#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : db_config
功能描述 : 数据库连接配置 — 模板文件（无密码版本）
          复制本文件为 db_config_secret.py 并填入真实密码
          db_config_secret.py 已被 .gitignore 排除，不会上传到 GitHub

用法:
    from risk_engine.config.db_config_secret import DB_CONFIG
    # 或自动降级到模板（仅 local 可用）
============================================================================
"""

# ===== 数据库连接配置（模板） =====
# 复制此文件为 db_config_secret.py 并填入真实密码
# 密码字段留空时会自动尝试读取环境变量，都不存在则报错

DB_CONFIG = {
    # ── 风险 StarRocks ──────────────────────────────────
    "risk": {
        "host": "47.119.181.195",
        "port": 9030,
        "user": "taoshun_fk_zf",
        "password": "",
        "env_var": "RISK_DB_PASSWORD",
        "database": "ods",
    },

    # ── 淘顺分期 MySQL ────────────────────────────────
    "ts": {
        "host": "taoshunfq.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_ZF",
        "password": "",
        "env_var": "TS_DB_PASSWORD",
        "database": "taoshun_fenqi",
    },

    # ── 百旅 ──────────────────────────────────────
    "bl": {
        "host": "bailv.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_ZF",
        "password": "",
        "env_var": "BL_DB_PASSWORD",
        "database": "bailv_np",
    },

    # ── 百旅风控 ──────────────────────────────────────
    "bl_risk": {
        "host": "bailv.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "risk_zhangfan",
        "password": "",
        "env_var": "BL_RISK_DB_PASSWORD",
        "database": "bailv_np",
    },

    # ── 通融分期 ──────────────────────────────────────
    "tr_risk": {
        "host": "lb-b3eaquue-arcsolybxgzn4ew8.clb.gz-tencentclb.com",
        "port": 3306,
        "user": "fusing_tongrong_fenqi_fk",
        "password": "",
        "env_var": "TR_RISK_DB_PASSWORD",
        "database": "bailv_np",
    },

    "tr_fusing": {
        "host": "lb-b3eaquue-arcsolybxgzn4ew8.clb.gz-tencentclb.com",
        "port": 3306,
        "user": "fusing_tongrong_fenqi_fk",
        "password": "",
        "env_var": "TR_FUSING_DB_PASSWORD",
        "database": "bailv_np",
    },

    # ── 淘顺风控（旧） ─────────────────────────────────
    "ts_risk": {
        "host": "taoshunfq.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_rank",
        "password": "",
        "env_var": "TS_RISK_DB_PASSWORD",
        "database": "taoshun_fenqi",
    },

    "ts_fusing": {
        "host": "taoshunfq.rwlb.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_rank",
        "password": "",
        "env_var": "TS_FUSING_DB_PASSWORD",
        "database": "taoshun_fenqi",
    },

    # ── 淘顺全库 ──────────────────────────────────────
    "tsck": {
        "host": "rm-wz93sqg82m6y8cu56so.mysql.rds.aliyuncs.com",
        "port": 3306,
        "user": "taoshunfenqi_fk_ZF",
        "password": "",
        "env_var": "TSCK_DB_PASSWORD",
        "database": "taoshun_all",
    },

    # ── Hive（大数据平台） ─────────────────────────────
    "hive": {
        "host": "47.107.182.51",
        "port": 10000,
        "user": "emr_fk_lqbtest",
        "password": "",
        "env_var": "HIVE_DB_PASSWORD",
        "database": "ods",
    },

    # ── 本地库 ────────────────────────────────────────
    "local": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "222311",
        "env_var": "LOCAL_DB_PASSWORD",
        "database": "risk_control",
    },
}
