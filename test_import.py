"""测试导入 — 在 PowerShell 里跑这个，看哪个环节出问题"""
import sys, os

print(f"Python 路径: {sys.executable}")
print(f"当前目录:   {os.getcwd()}")
print(f"Python 版本: {sys.version}")

# 项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"项目根目录: {project_root}")

# 当前 sys.path
print(f"\nsys.path 前3项:")
for p in sys.path[:3]:
    print(f"  {p}")

# 手动加入
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"\n✅ 已加入项目路径")

# 测试导入
print(f"\n--- 测试导入 ---")
try:
    from risk_engine.config import db_config_secret
    print(f"✅ db_config_secret: {db_config_secret.__file__}")
    print(f"   'risk' 存在: {'risk' in db_config_secret.DB_CONFIG}")
except Exception as e:
    print(f"❌ db_config_secret 失败: {type(e).__name__}: {e}")

try:
    from risk_engine.config import db_config
    print(f"✅ db_config: {db_config.__file__}")
    print(f"   'risk' 存在: {'risk' in db_config.DB_CONFIG}")
except Exception as e:
    print(f"❌ db_config 失败: {type(e).__name__}: {e}")

try:
    from risk_engine.toolkit.connectors.db_connector import _load_config
    print(f"✅ _load_config 导入成功")
    cfg = _load_config("risk")
    print(f"   拿到配置: {cfg['host']}")
except Exception as e:
    print(f"❌ _load_config 失败: {type(e).__name__}: {e}")
