"""
浙江 v1 仿真配置 — 继承江西决策树，换浙江省数据
"""

from risk_engine.simulation.config.presets import Jiangxi_v1

# 浙江 v1：直接继承江西的决策树和分箱方案，只换省份
Zhejiang_v1 = Jiangxi_v1.clone(
    province="浙江省",
    version="v1",
    description="浙江 v1 — 继承江西决策树，使用浙江省数据",
    base="jiangxi_v1",
)

# 全局配置注册表
PRESETS = {
    "jiangxi_v1": Jiangxi_v1,
    "zhejiang_v1": Zhejiang_v1,
}
