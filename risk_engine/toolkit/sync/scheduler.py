#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : scheduler
功能描述 : 数据同步定时调度 — 支持 Cron 表达式配置

用法:
    # 每日凌晨 3 点全量同步
    python -m risk_engine.toolkit.sync.scheduler --cron "0 3 * * *"

    # 立即运行一次
    python -m risk_engine.toolkit.sync.scheduler --once

    # 只同步 ODS 层
    python -m risk_engine.toolkit.sync.scheduler --once --schema ods

创建日期 : 2026-05-26
============================================================================
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime

from risk_engine.toolkit.sync.runner import run_sync

logger = logging.getLogger("sync_scheduler")


def run_once(schema: str = None, table_names: list = None, mode: str = "full"):
    """立即执行一次同步"""
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始 {' '.join(table_names or ['全部'])} 同步"
    )
    results = run_sync(table_names=table_names, schema=schema, mode=mode)
    return results


def run_cron(cron_expr: str, schema: str = None):
    """按 Cron 表达式定时运行"""
    try:
        from crontab import CronTab

        cron = CronTab(cron_expr)
    except ImportError:
        print("⚠️ 未安装 python-crontab，请执行: pip install python-crontab")
        print("   改用 --once 模式单次运行")
        return

    print(f"定时同步已启动: {cron_expr}")
    print("按 Ctrl+C 停止")

    while True:
        datetime.now()
        if cron.next(default_utc=False) <= 0:
            run_once(schema=schema)
            time.sleep(60)  # 避免一分钟内重复触发
        time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据同步调度器")
    parser.add_argument("--once", action="store_true", help="立即运行一次")
    parser.add_argument("--cron", type=str, help="Cron 表达式 (如 '0 3 * * *' 每天凌晨3点)")
    parser.add_argument("--schema", type=str, help="同步特定层 (ods/dwd/dws/ads)")
    parser.add_argument("--tables", type=str, nargs="+", help="同步特定表名列表")
    parser.add_argument("--mode", type=str, default="full", choices=["full", "incremental"])
    args = parser.parse_args()

    if args.once:
        run_once(schema=args.schema, table_names=args.tables, mode=args.mode)
    elif args.cron:
        run_cron(args.cron, schema=args.schema)
    else:
        parser.print_help()
