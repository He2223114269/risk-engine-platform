"""
模型训练模块
支持常见的风险控制模型训练和评估
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import json
import os
from datetime import datetime
from typing import Dict, Any, Tuple, List

class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, model_save_dir: str = "/home/gelpians/.openclaw/workspace/data/models"):
        self.model_save_dir = model_save_dir
        self.scaler = StandardScaler()
        
    def prepare_data(self, df: pd.DataFrame, target_col: str, feature_cols: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            df: 输入数据
            target_col: 目标列名
            feature_cols: 特征列名列表，如果为None则自动选择
            
        Returns:
            (X, y): 特征和目标变量
        """
        if feature_cols is None:
            feature_cols = [col for col in df.columns if col != target_col]
        
        X = df[feature_cols].values
        y = df[target_col].values
        
        # 处理缺失值
        X = np.nan_to_num(X, nan=0.0)
        
        return X, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray, model_type: str = 'random_forest', **kwargs) -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            X: 特征数据
            y: 目标变量
            model_type: 模型类型 ('random_forest', 'gradient_boosting', 'logistic')
            **kwargs: 模型参数
            
        Returns:
            包含模型和评估指标的字典
        """
        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 数据标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 选择模型
        if model_type == 'random_forest':
            model = RandomForestClassifier(**kwargs, random_state=42)
        elif model_type == 'gradient_boosting':
            model = GradientBoostingClassifier(**kwargs, random_state=42)
        elif model_type == 'logistic':
            model = LogisticRegression(**kwargs, random_state=42, max_iter=1000)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        # 训练模型
        model.fit(X_train_scaled, y_train)
        
        # 预测和评估
        y_pred = model.predict(X_test_scaled)
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        metrics = self.calculate_metrics(y_test, y_pred, y_pred_proba)
        
        # 交叉验证
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='f1')
        metrics['cv_mean_f1'] = cv_scores.mean()
        metrics['cv_std_f1'] = cv_scores.std()
        
        return {
            'model': model,
            'scaler': self.scaler,
            'metrics': metrics,
            'feature_importance': self.get_feature_importance(model)
        }
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_pred_proba: np.ndarray) -> Dict[str, float]:
        """计算评估指标"""
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_true, y_pred_proba)
        }
    
    def get_feature_importance(self, model: Any) -> Dict[str, float]:
        """获取特征重要性"""
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            return {
                f'feature_{i}': float(imp) 
                for i, imp in enumerate(importance)
            }
        return {}
    
    def save_model(self, model: Any, model_name: str, metrics: Dict[str, float], scaler: Any = None):
        """保存模型和指标"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(self.model_save_dir, f"{model_name}_{timestamp}")
        
        os.makedirs(save_path, exist_ok=True)
        
        # 保存模型
        joblib.dump(model, os.path.join(save_path, 'model.pkl'))
        
        # 保存scaler
        if scaler is not None:
            joblib.dump(scaler, os.path.join(save_path, 'scaler.pkl'))
        
        # 保存指标
        with open(os.path.join(save_path, 'metrics.json'), 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"模型已保存到: {save_path}")
        return save_path
    
    def load_model(self, model_path: str) -> Tuple[Any, Any, Dict[str, float]]:
        """加载模型"""
        model = joblib.load(os.path.join(model_path, 'model.pkl'))
        
        try:
            scaler = joblib.load(os.path.join(model_path, 'scaler.pkl'))
        except:
            scaler = None
        
        with open(os.path.join(model_path, 'metrics.json'), 'r') as f:
            metrics = json.load(f)
        
        return model, scaler, metrics