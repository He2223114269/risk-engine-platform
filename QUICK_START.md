# 风险建模分析助手 - 快速开始指南

## 🎯 概述
这是一个专门为您设计的风险建模分析框架，帮助您完成日常的风险控制工作。

## 📁 项目结构
```
/home/gelpians/.openclaw/workspace/
├── config/          # 配置文件
│   ├── database.py  # 数据库配置
│   └── email_service.py  # 邮件配置
├── data/           # 数据目录
│   ├── raw/        # 原始数据
│   ├── processed/   # 处理后数据
│   ├── models/      # 训练好的模型
│   ├── reports/     # 报告文件
│   └── config/     # 配置文件
├── models/         # 模型训练模块
├── examples/        # 使用示例
└── memory/         # 工作记录
└── workflow.py     # 主工作流程
```

## 🚀 四大核心功能

### 1️⃣ 数据获取
```python
from workflow import get_training_data, get_indicators, run_query

# 获取模型训练数据
training_data = get_training_data('credit_risk', days=90)

# 获取风险指标数据
indicators = get_indicators(days=30)

# 自定义SQL查询
result = run_query("SELECT * FROM risk_indicators WHERE date >= '2026-04-01'")
```

### 2️⃣ 模型训练
```python
from workflow import train_model, get_training_data

# 获取训练数据
data = get_training_data('credit_risk', days=90)

# 训练模型
result = train_model(
    data=data,
    target_col='target_variable',  # 目标列名
    model_type='random_forest',    # 模型类型
    model_name='my_risk_model'     # 模型名称
)

# 查看结果
print("模型性能指标:")
for metric, value in result['metrics'].items():
    print(f"{metric}: {value:.4f}")
```

**支持的模型类型:**
- `random_forest` - 随机森林
- `gradient_boosting` - 梯度提升
- `logistic` - 逻辑回归

### 3️⃣ 数据监控
```python
from workflow import monitor_data, check_quality

# 运行数据监控
report = monitor_data(indicators, auto_alert=False)

# 检查数据质量
quality = check_quality(indicators)

print(f"发现异常: {report['summary']['total_anomalies_detected']}")
print(f"缺失值字段数: {len(quality['missing_values'])}")
```

**检测的异常类型:**
- 统计异常 (Z-score)
- IQR异常
- 时间序列异常

### 4️⃣ 业务取数需求
```python
from workflow import configure_email, send_data

# 配置邮件服务
configure_email('your_email@gmail.com', 'your_password')

# 准备请求信息
request_info = {
    'requester': '张经理',
    'department': '风控部',
    'description': '获取最近30天的风险指标数据',
    'request_time': '2026-04-27',
    'date_range': '最近30天'
}

# 发送数据
success = send_data(
    data=indicators,
    recipient='colleague@company.com',
    request_info=request_info,
    subject='风险指标数据报告'
)
```

## ⚙️ 初始配置

### 1. 数据库配置
编辑 `config/database.py` 文件:
```python
DB_CONFIG = {
    'host': 'your_database_host',      # 数据库主机
    'port': 5432,                      # 端口
    'database': 'risk_db',             # 数据库名
    'user': 'risk_user',              # 用户名
    'password': 'your_password',      # 密码
    'table_prefix': 'risk_'           # 表名前缀
}
```

### 2. 邮件配置
在代码中配置邮件服务:
```python
from workflow import configure_email
configure_email('your_email@gmail.com', 'your_password')
```

## 📋 日常工作流程

### 日常任务清单
```
☑️ 获取最新数据 (get_training_data/get_indicators)
☑️ 检查数据质量 (check_quality)
☑️ 运行数据监控 (monitor_data)
☑️ 训练模型 (train_model)
☑️ 处理业务需求 (send_data)
☑️ 记录工作日志 (自动生成)
```

### 每日例行流程
```python
# 1. 获取数据
training_data = get_training_data('credit_risk', days=90)
indicators = get_indicators(days=30)

# 2. 检查质量和监控
quality = check_quality(training_data)
monitor_report = monitor_data(indicators)

# 3. 如果需要，训练模型
if model_need_training:
    result = train_model(training_data, 'target_variable')

# 4. 处理业务需求
# send_data(data, recipient, request_info)
```

## 📊 返回结果说明

### 数据质量报告
```python
quality = {
    'total_rows': 1000,        # 总行数
    'total_columns': 15,       # 总列数
    'missing_values': {...},   # 各字段缺失值情况
    'duplicate_rows': 5,      # 重复行数
    'date_range': {...}       # 日期范围
}
```

### 模型性能报告
```python
metrics = {
    'accuracy': 0.8756,       # 准确率
    'precision': 0.8234,     # 精确率
    'recall': 0.7654,        # 召回率
    'f1': 0.7934,            # F1分数
    'roc_auc': 0.8765,       # ROC AUC
    'cv_mean_f1': 0.7890,    # 交叉验证F1均值
    'cv_std_f1': 0.0234      # 交叉验证F1标准差
}
```

### 监控报告
```python
monitor_report = {
    'total_anomalies_detected': 5,         # 总异常数
    'anomaly_type_distribution': {          # 异常类型分布
        'statistical': 3,
        'iqr': 2
    }
}
```

## 🛠️ 故障排除

### 常见问题
1. **数据库连接失败**: 检查 `config/database.py` 中的配置
2. **邮件发送失败**: 检查邮箱配置和网络连接
3. **数据为空**: 确认数据库中有数据且时间范围正确
4. **模型训练失败**: 检查目标列是否存在，数据是否完整

### 日志查看
- 工作日志: `memory/YYYY-MM-DD.md`
- 监控报告: `data/reports/`
- 模型文件: `data/models/`

## 📞 获取帮助

查看完整示例: `examples/usage_examples.py`
查看工作日志: `memory/` 目录
查看详细配置: `config/` 目录

---

🎉 现在您已经了解了所有功能，开始您的风险建模之旅吧！