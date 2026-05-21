#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
============================================================================
模块名称 : conftest
功能描述 : pytest 共享 fixtures — 提供 mock 数据和测试基础设施
创建日期 : 2026-05-21
开发者   : Jingluo
版本     : v0.1.0
============================================================================
"""

import pytest


@pytest.fixture
def sample_features() -> dict:
    """示例风控特征数据"""
    return {
        "user_age": 35,
        "online_duration": 24,
        "operator_real": "1",
        "order_amount": 5000,
        "store_overdue_rate": 0.05,
    }


@pytest.fixture
def sample_decision_request() -> dict:
    """示例决策请求"""
    return {
        "request_id": "test-req-001",
        "user_id": "user_12345",
        "order_id": "order_67890",
        "features": {
            "user_age": 35,
            "online_duration": 24,
            "operator_real": "1",
            "order_amount": 5000,
        },
    }
