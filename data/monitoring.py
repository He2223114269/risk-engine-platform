"""
数据监控和异常检测模块
"""

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class DataMonitor:
    """数据监控器"""
    
    def __init__(self, db_config_path: str = "/home/gelpians/.openclaw/workspace/config/database.py"):
        self.db_config = None
        self.anomalies = []
        
    def calculate_statistical_anomalies(self, data: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """
        基于统计方法的异常检测
        
        Args:
            data: 输入数据
            threshold: Z-score阈值
            
        Returns:
            包含异常数据的DataFrame
        """
        anomalies = []
        
        for column in data.select_dtypes(include=[np.number]).columns:
            if column in ['date', 'timestamp']:
                continue
                
            # 计算Z-score
            z_scores = np.abs(stats.zscore(data[column].dropna()))
            outlier_mask = z_scores > threshold
            
            if outlier_mask.any():
                outliers = data.loc[outlier_mask, [column]]
                outliers['column'] = column
                outliers['z_score'] = z_scores[outlier_mask]
                outliers['anomaly_type'] = 'statistical'
                outliers['timestamp'] = pd.Timestamp.now()
                anomalies.append(outliers)
        
        if anomalies:
            return pd.concat(anomalies, ignore_index=True)
        return pd.DataFrame()
    
    def calculate_iqr_anomalies(self, data: pd.DataFrame, multiplier: float = 1.5) -> pd.DataFrame:
        """
        基于IQR方法的异常检测
        
        Args:
            data: 输入数据
            multiplier: IQR乘数
            
        Returns:
            包含异常数据的DataFrame
        """
        anomalies = []
        
        for column in data.select_dtypes(include=[np.number]).columns:
            if column in ['date', 'timestamp']:
                continue
                
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR
            
            outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
            if not outliers.empty:
                outliers['column'] = column
                outliers['lower_bound'] = lower_bound
                outliers['upper_bound'] = upper_bound
                outliers['anomaly_type'] = 'iqr'
                outliers['timestamp'] = pd.Timestamp.now()
                anomalies.append(outliers)
        
        if anomalies:
            return pd.concat(anomalies, ignore_index=True)
        return pd.DataFrame()
    
    def time_series_anomalies(self, data: pd.DataFrame, column: str, window: int = 7) -> pd.DataFrame:
        """
        时间序列异常检测
        
        Args:
            data: 输入数据（必须包含date列）
            column: 检测列名
            window: 滚动窗口大小
            
        Returns:
            包含异常数据的DataFrame
        """
        df = data.copy()
        df = df.sort_values('date')
        
        # 计算移动平均和标准差
        df['moving_avg'] = df[column].rolling(window=window).mean()
        df['moving_std'] = df[column].rolling(window=window).std()
        
        # 计算上下限
        df['upper_bound'] = df['moving_avg'] + 2 * df['moving_std']
        df['lower_bound'] = df['moving_avg'] - 2 * df['moving_std']
        
        # 检测异常
        outliers = df[(df[column] > df['upper_bound']) | (df[column] < df['lower_bound'])]
        
        if not outliers.empty:
            outliers['anomaly_type'] = 'time_series'
            outliers['window'] = window
            outliers['timestamp'] = pd.Timestamp.now()
        
        return outliers
    
    def monitor_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        数据质量监控
        
        Args:
            data: 输入数据
            
        Returns:
            数据质量报告
        """
        quality_report = {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'missing_values': {},
            'data_types': {},
            'duplicate_rows': 0,
            'date_range': {}
        }
        
        # 缺失值统计
        for column in data.columns:
            missing_count = data[column].isnull().sum()
            quality_report['missing_values'][column] = {
                'count': int(missing_count),
                'percentage': float(missing_count / len(data) * 100) if len(data) > 0 else 0
            }
            quality_report['data_types'][column] = str(data[column].dtype)
        
        # 重复行统计
        quality_report['duplicate_rows'] = int(data.duplicated().sum())
        
        # 日期范围统计
        date_columns = data.select_dtypes(include=['datetime64']).columns
        for column in date_columns:
            if len(data[column].dropna()) > 0:
                quality_report['date_range'][column] = {
                    'min': str(data[column].min()),
                    'max': str(data[column].max()),
                    'days_covered': int((data[column].max() - data[column].min()).days)
                }
        
        return quality_report
    
    def generate_monitoring_report(self, data: pd.DataFrame, anomaly_threshold: float = 3.0) -> Dict[str, Any]:
        """
        生成监控报告
        
        Args:
            data: 输入数据
            anomaly_threshold: 异常检测阈值
            
        Returns:
            完整监控报告
        """
        report = {
            'timestamp': pd.Timestamp.now(),
            'data_quality': self.monitor_data_quality(data),
            'statistical_anomalies': self.calculate_statistical_anomalies(data, anomaly_threshold),
            'iqr_anomalies': self.calculate_iqr_anomalies(data),
            'summary': {}
        }
        
        # 汇总信息
        total_anomalies = (
            len(report['statistical_anomalies']) + 
            len(report['iqr_anomalies'])
        )
        report['summary']['total_anomalies_detected'] = total_anomalies
        
        # 按类型统计异常
        anomaly_types = []
        if not report['statistical_anomalies'].empty:
            anomaly_types.extend(['statistical'] * len(report['statistical_anomalies']))
        if not report['iqr_anomalies'].empty:
            anomaly_types.extend(['iqr'] * len(report['iqr_anomalies']))
        
        report['summary']['anomaly_type_distribution'] = pd.Series(anomaly_types).value_counts().to_dict()
        
        return report
    
    def save_monitoring_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """
        保存监控报告
        
        Args:
            report: 监控报告
            filename: 文件名（如果为None则自动生成）
            
        Returns:
            保存路径
        """
        import os
        from datetime import datetime
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"monitoring_report_{timestamp}.json"
        
        save_path = f"/home/gelpians/.openclaw/workspace/data/reports/{filename}"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        import json
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        return save_path