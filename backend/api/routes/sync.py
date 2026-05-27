#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : sync
功能描述 : 数据同步 API — 手动触发同步、查看同步状态

路由:
    POST /api/sync/run         — 触发数据同步
    GET  /api/sync/status      — 查看同步状态和日志
    GET  /api/sync/tables      — 查看可同步的表清单

创建日期 : 2026-05-26
============================================================================
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from risk_engine.toolkit.sync.ddl_registry import ALL_TABLES
from risk_engine.toolkit.sync.runner import run_sync

router = APIRouter(prefix="/api/sync", tags=["数据同步"])


# ── 请求/响应模型 ──


class SyncRequest(BaseModel):
    tables: list[str] | None = None
    schema: str | None = None
    mode: str = "full"


class SyncResponse(BaseModel):
    success: bool
    message: str
    results: dict | None = None


# ── 路由 ──


@router.post("/run", response_model=SyncResponse)
def trigger_sync(req: SyncRequest):
    """
    触发数据同步。

    请求体:
        tables:  可选，指定表名列表
        schema:  可选，指定层 (ods/dwd/dws)
        mode:    "full"=全量 / "incremental"=增量
    """
    try:
        results = run_sync(
            table_names=req.tables,
            schema=req.schema,
            mode=req.mode,
        )
        return SyncResponse(
            success=True,
            message="同步完成",
            results=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
def list_tables():
    """查看所有可同步的表。"""
    return [
        {
            "schema": t.schema_name,
            "table": t.table_name,
            "description": t.description,
            "row_estimate": t.row_estimate,
        }
        for t in ALL_TABLES
    ]


@router.get("/status")
def sync_status(table: str | None = None):
    """查看同步状态。"""
    from risk_engine.toolkit.connectors import get_data
    from risk_engine.toolkit.sync.sync_tracker import ensure_tracker_table

    ensure_tracker_table()
    conn = get_data(data_type="local")

    where = f"WHERE table_name = '{table}'" if table else ""
    df = conn.get_data(f"""
        SELECT table_name, sync_date, start_time, end_time,
               row_count, status, remark
        FROM sync_journal
        {where}
        ORDER BY start_time DESC
        LIMIT 50
    """)
    conn.close()

    return df.to_dict(orient="records") if not df.empty else {"message": "暂无同步记录"}
