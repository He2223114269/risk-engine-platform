"""
主要工作流程
整合数据库访问、模型训练、数据监控和邮件发送功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/gelpians/.openclaw/workspace')

from config.database import query_data, get_model_training_data, get_risk_indicators
from models.model_trainer import ModelTrainer
from data.monitoring import DataMonitor
from config.email_service import EmailService, DataRequestTemplate
import pandas as pd
from datetime import datetime
import json

class RiskAnalysisWorkflow:
    """风险分析工作流程"""
    
    def __init__(self):
        self.model_trainer = ModelTrainer()
        self.data_monitor = DataMonitor()
        self.email_service = EmailService()
        
        # 记录工作日志
        self.log_file = f"/home/gelpians/.openclaw/workspace/memory/{datetime.now().strftime('%Y-%m-%d')}.md"
    
    def log_work(self, task: str, details: str):
        """记录工作日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"\n## {timestamp} - {task}\n\n{details}\n"
        
        # 确保日志文件存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    # ==================== 数据获取 ====================
    
    def get_training_data_for_model(self, model_type: str, days: int = 90) -> pd.DataFrame:
        """
        获取模型训练数据
        
        Args:
            model_type: 模型类型
            days: 数据天数
            
        Returns:
            训练数据
        """
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=days)
        
        data = get_model_training_data(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            model_type
        )
        
        self.log_work(
            f"获取{model_type}模型训练数据",
            f"时间范围: {start_date.date()} 到 {end_date.date()}\\n"
            f"数据量: {len(data)} 条记录"
        )
        
        return data
    
    def get_indicator_statistics(self, days: int = 30) -> pd.DataFrame:
        """
        获取指标统计数据
        
        Args:
            days: 天数
            
        Returns:
            指标数据
        """
        data = get_risk_indicators(f'{days}d')
        
        self.log_work(
            "获取风险指标统计",
            f"时间范围: 最近 {days} 天\\n"
            f"指标数量: {len(data)} 条记录"
        )
        
        return data
    
    def execute_custom_query(self, sql: str, params: dict = None) -> pd.DataFrame:
        """
        执行自定义SQL查询
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            查询结果
        """
        data = query_data(sql, params)
        
        self.log_work(
            "执行自定义查询",
            f"SQL: {sql[:100]}...\\n"
            f"查询结果: {len(data)} 条记录"
        )
        
        return data
    
    # ==================== 模型训练 ====================
    
    def train_risk_model(
        self, 
        data: pd.DataFrame, 
        target_col: str,
        model_type: str = 'random_forest',
        model_name: str = 'risk_model',
        save_model: bool = True
    ) -> dict:
        """
        训练风险模型
        
        Args:
            data: 训练数据
            target_col: 目标列名
            model_type: 模型类型
            model_name: 模型名称
            save_model: 是否保存模型
            
        Returns:
            训练结果
        """
        # 准备数据
        X, y = self.model_trainer.prepare_data(data, target_col)
        
        # 训练模型
        result = self.model_trainer.train_model(X, y, model_type)
        
        self.log_work(
            f"训练{model_type}模型",
            f"模型名称: {model_name}\\n"
            f"训练样本: {len(X)}\\n"
            f"性能指标:\\n"
            f"  - 准确率: {result['metrics']['accuracy']:.4f}\\n"
            f"  - 精确率: {result['metrics']['precision']:.4f}\\n"
            f"  - 召回率: {result['metrics']['recall']:.4f}\\n"
            f"  - F1分数: {result['metrics']['f1']:.4f}\\n"
            f"  - ROC AUC: {result['metrics']['roc_auc']:.4f}"
        )
        
        if save_model:
            save_path = self.model_trainer.save_model(
                result['model'],
                model_name,
                result['metrics'],
                result['scaler']
            )
            result['save_path'] = save_path
        
        return result
    
    # ==================== 数据监控 ====================
    
    def run_data_monitoring(self, data: pd.DataFrame, auto_alert: bool = False) -> dict:
        """
        运行数据监控
        
        Args:
            data: 要监控的数据
            auto_alert: 是否自动发送告警
            
        Returns:
            监控报告
        """
        report = self.data_monitor.generate_monitoring_report(data)
        
        self.log_work(
            "数据监控检查",
            f"数据量: {report['data_quality']['total_rows']} 条记录\\n"
            f"发现异常: {report['summary']['total_anomalies_detected']} 个\\n"
            f"异常类型分布: {report['summary']['anomaly_type_distribution']}"
        )
        
        # 保存监控报告
        report_path = self.data_monitor.save_monitoring_report(report)
        print(f"监控报告已保存到: {report_path}")
        
        return report
    
    def check_data_quality(self, data: pd.DataFrame) -> dict:
        """
        检查数据质量
        
        Args:
            data: 要检查的数据
            
        Returns:
            数据质量报告
        """
        quality_report = self.data_monitor.monitor_data_quality(data)
        
        self.log_work(
            "数据质量检查",
            f"总行数: {quality_report['total_rows']}\\n"
            f"总列数: {quality_report['total_columns']}\\n"
            f"重复行: {quality_report['duplicate_rows']}\\n"
            f"缺失值字段: {len([v for v in quality_report['missing_values'].values() if v['count'] > 0])}"
        )
        
        return quality_report
    
    # ==================== 邮件发送 ====================
    
    def configure_email(self, email: str, password: str):
        """配置邮件服务"""
        self.email_service.configure(email, password)
        self.log_work("邮件服务配置", f"发件人: {email}")
    
    def send_data_to_colleague(
        self,
        data: pd.DataFrame,
        recipient: str,
        request_info: dict,
        subject: str = None
    ) -> bool:
        """
        发送数据给同事
        
        Args:
            data: 数据
            recipient: 收件人
            request_info: 请求信息
            subject: 邮件主题
            
        Returns:
            是否发送成功
        """
        # 生成报告
        report = DataRequestTemplate.create_basic_report(data, request_info)
        
        if subject is None:
            subject = f"数据取数结果 - {request_info.get('department', '未知')}"
        
        success = self.email_service.send_data_report(
            recipient=recipient,
            subject=subject,
            data=data,
            message=report
        )
        
        if success:
            self.log_work(
                "发送数据给同事",
                f"收件人: {recipient}\\n"
                f"数据量: {len(data)} 条记录\\n"
                f"需求: {request_info.get('description', '未知')}"
            )
        
        return success
    
    def send_monitoring_alert(self, recipient: str, report: dict) -> bool:
        """
        发送监控告警
        
        Args:
            recipient: 收件人
            report: 监控报告
            
        Returns:
            是否发送成功
        """
        anomaly_count = report['summary']['total_anomalies_detected']
        anomaly_types = list(report['summary']['anomaly_type_distribution'].keys())
        
        success = self.email_service.send_monitoring_alert(
            recipient=recipient,
            anomaly_count=anomaly_count,
            anomaly_types=anomaly_types
        )
        
        if success:
            self.log_work(
                "发送监控告警",
                f"收件人: {recipient}\\n"
                f"异常数量: {anomaly_count}\\n"
                f"异常类型: {', '.join(anomaly_types)}"
            )
        
        return success

# 全局工作流程实例
workflow = RiskAnalysisWorkflow()

# 便捷函数
def get_training_data(model_type: str, days: int = 90):
    """获取训练数据"""
    return workflow.get_training_data_for_model(model_type, days)

def get_indicators(days: int = 30):
    """获取指标数据"""
    return workflow.get_indicator_statistics(days)

def run_query(sql: str, params: dict = None):
    """运行查询"""
    return workflow.execute_custom_query(sql, params)

def train_model(data, target_col, model_type='random_forest', model_name='risk_model'):
    """训练模型"""
    return workflow.train_risk_model(data, target_col, model_type, model_name)

def monitor_data(data, auto_alert=False):
    """监控数据"""
    return workflow.run_data_monitoring(data, auto_alert)

def check_quality(data):
    """检查数据质量"""
    return workflow.check_data_quality(data)

def configure_email(email, password):
    """配置邮件"""
    return workflow.configure_email(email, password)

def send_data(data, recipient, request_info, subject=None):
    """发送数据"""
    return workflow.send_data_to_colleague(data, recipient, request_info, subject)