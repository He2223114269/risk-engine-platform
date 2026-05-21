"""
使用示例
展示如何使用风险建模分析助手的工作流程
"""

from workflow import workflow
import pandas as pd

# 示例1: 获取训练数据并训练模型
def example_model_training():
    """示例：模型训练流程"""
    
    print("=== 示例1: 模型训练 ===")
    
    # 1. 获取训练数据
    print("1. 获取模型训练数据...")
    training_data = workflow.get_training_data_for_model(
        model_type='credit_risk', 
        days=90
    )
    
    if training_data.empty:
        print("未获取到训练数据")
        return
    
    print(f"获取到 {len(training_data)} 条训练记录")
    
    # 2. 检查数据质量
    print("2. 检查数据质量...")
    quality_report = workflow.check_quality(training_data)
    print(f"数据质量检查完成")
    
    # 3. 训练模型
    print("3. 训练风险模型...")
    result = workflow.train_risk_model(
        data=training_data,
        target_col='target_variable',
        model_type='random_forest',
        model_name='credit_risk_model'
    )
    
    print("4. 训练结果:")
    for metric, value in result['metrics'].items():
        print(f"   {metric}: {value:.4f}")
    
    return result

# 示例2: 数据监控和告警
def example_data_monitoring():
    """示例：数据监控流程"""
    
    print("\n=== 示例2: 数据监控 ===")
    
    # 1. 获取指标数据
    print("1. 获取风险指标数据...")
    indicator_data = workflow.get_indicator_statistics(days=30)
    
    if indicator_data.empty:
        print("未获取到指标数据")
        return
    
    print(f"获取到 {len(indicator_data)} 条指标记录")
    
    # 2. 运行监控
    print("2. 运行数据监控...")
    monitoring_report = workflow.run_data_monitoring(
        data=indicator_data,
        auto_alert=False
    )
    
    print(f"3. 监控结果:")
    print(f"   总异常数: {monitoring_report['summary']['total_anomalies_detected']}")
    
    if monitoring_report['summary']['anomaly_type_distribution']:
        print("   异常类型分布:")
        for anomaly_type, count in monitoring_report['summary']['anomaly_type_distribution'].items():
            print(f"     - {anomaly_type}: {count}")
    
    # 4. 检查数据质量
    quality_report = workflow.check_quality(indicator_data)
    print(f"5. 数据质量:")
    print(f"   缺失值字段数: {len([v for v in quality_report['missing_values'].values() if v['count'] > 0])}")
    print(f"   重复行数: {quality_report['duplicate_rows']}")
    
    return monitoring_report

# 示例3: 业务取数需求处理
def example_business_request():
    """示例：业务取数需求"""
    
    print("\n=== 示例3: 业务取数需求 ===")
    
    # 1. 获取数据（示例）
    print("1. 获取业务数据...")
    # 这里可以用自定义查询或者现有的获取函数
    
    # 模拟请求信息
    request_info = {
        'requester': '张经理',
        'department': '风控部',
        'description': '获取最近30天的风险指标数据',
        'request_time': '2026-04-27 10:00',
        'date_range': '最近30天'
    }
    
    # 2. 模拟获取数据（实际使用时替换为真实数据获取）
    # data = workflow.get_indicator_statistics(days=30)
    
    # 由于没有真实数据，我们创建模拟数据
    print("2. 创建模拟数据用于演示...")
    import numpy as np
    
    dates = pd.date_range('2026-03-28', '2026-04-27')
    data = pd.DataFrame({
        'date': dates,
        'fraud_rate': np.random.uniform(0.02, 0.08, len(dates)),
        'default_rate': np.random.uniform(0.01, 0.05, len(dates)),
        'loss_amount': np.random.uniform(10000, 50000, len(dates))
    })
    
    print(f"生成模拟数据: {len(data)} 条记录")
    
    # 3. 检查数据质量
    quality_report = workflow.check_quality(data)
    print(f"4. 数据质量检查完成")
    
    # 4. 发送数据（需要先配置邮件）
    print("5. 注意: 需要先配置邮件服务才能发送数据")
    print("   使用: configure_email('your_email@gmail.com', 'your_password')")
    
    # 模拟发送流程（注释掉实际发送）
    # success = workflow.send_data_to_colleague(
    #     data=data,
    #     recipient='colleague@company.com',
    #     request_info=request_info,
    #     subject='风险指标数据报告'
    # )
    
    print("数据准备完成，等待邮件配置...")
    
    return data, request_info

# 示例4: 自定义查询
def example_custom_query():
    """示例：自定义SQL查询"""
    
    print("\n=== 示例4: 自定义查询 ===")
    
    # 示例SQL查询（需要根据实际数据库结构调整）
    sql = """
    SELECT 
        date,
        fraud_rate,
        default_rate,
        COUNT(*) as transaction_count
    FROM risk_indicators 
    WHERE date >= '2026-04-01'
    GROUP BY date, fraud_rate, default_rate
    ORDER BY date
    """
    
    try:
        # 执行查询
        result = workflow.execute_custom_query(sql)
        print(f"查询成功，获取 {len(result)} 条记录")
        
        if not result.empty:
            print("数据预览:")
            print(result.head())
        
        return result
    except Exception as e:
        print(f"查询执行失败: {e}")
        print("请检查SQL语句和数据库连接配置")
        return pd.DataFrame()

# 主函数 - 运行所有示例
def run_examples():
    """运行所有示例"""
    
    print("风险建模分析助手 - 使用示例")
    print("="*50)
    
    # 配置示例（需要实际配置）
    print("\n注意: 运行某些示例前，请确保:")
    print("1. 数据库配置正确")
    print("2. 邮件服务已配置 (configure_email)")
    print("3. 数据库中有可用的测试数据")
    
    # 运行各个示例
    try:
        # 示例1: 模型训练
        model_result = example_model_training()
        
        # 示例2: 数据监控
        monitoring_result = example_data_monitoring()
        
        # 示例3: 业务取数
        business_data, request_info = example_business_request()
        
        # 示例4: 自定义查询
        query_result = example_custom_query()
        
        print("\n" + "="*50)
        print("所有示例执行完成")
        print("查看详细日志: 检查 memory/ 目录下的日志文件")
        
    except Exception as e:
        print(f"执行示例时出错: {e}")
        print("请检查配置和依赖项")

if __name__ == "__main__":
    run_examples()