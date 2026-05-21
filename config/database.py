"""
数据库连接配置
根据实际需求修改数据库连接参数
"""

import psycopg2
import sqlite3
import pandas as pd
from typing import Optional, Dict, Any

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'risk_db',
    'user': 'risk_user',
    'password': 'your_password',
    'table_prefix': 'risk_'
}

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def query_data(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    查询数据并返回DataFrame
    
    Args:
        sql: SQL查询语句
        params: 查询参数
        
    Returns:
        DataFrame: 查询结果
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    except Exception as e:
        print(f"数据查询失败: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_model_training_data(start_date: str, end_date: str, model_type: str) -> pd.DataFrame:
    """
    获取模型训练数据
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        model_type: 模型类型
        
    Returns:
        DataFrame: 模型训练数据
    """
    table_name = f"{DB_CONFIG['table_prefix']}training_data"
    sql = f"""
    SELECT * FROM {table_name}
    WHERE model_type = %s
    AND date BETWEEN %s AND %s
    ORDER BY date
    """
    
    params = [model_type, start_date, end_date]
    return query_data(sql, params)

def get_risk_indicators(date_range: str = '30d') -> pd.DataFrame:
    """
    获取风险指标数据
    
    Args:
        date_range: 时间范围 (如 '7d', '30d', '90d')
        
    Returns:
        DataFrame: 风险指标数据
    """
    table_name = f"{DB_CONFIG['table_prefix']}indicators"
    sql = f"""
    SELECT * FROM {table_name}
    WHERE date >= CURRENT_DATE - INTERVAL '{date_range}'
    ORDER BY date DESC
    """
    
    return query_data(sql)