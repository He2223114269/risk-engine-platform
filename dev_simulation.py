#!/usr/bin/env python3
"""
仿真调试脚本 — 入口（实现见 risk_engine/simulation/dev_simulation.py）
===================================================================

用法：直接运行

配置：编辑 risk_engine/simulation/config/zhejiang_proxy.py
"""

import os, sys, runpy
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
os.chdir(str(_ROOT))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

runpy.run_path(str(_ROOT / "risk_engine" / "simulation" / "dev_simulation.py"), run_name="__main__")
