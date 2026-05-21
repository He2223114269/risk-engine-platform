"""
邮件服务模块
用于处理业务取数需求和数据发送
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

class EmailService:
    """邮件服务"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = None
        self.sender_password = None
        
    def configure(self, sender_email: str, sender_password: str):
        """
        配置发件人信息
        
        Args:
            sender_email: 发件人邮箱
            sender_password: 邮箱密码或应用密码
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def send_data_report(
        self, 
        recipient: str, 
        subject: str, 
        data: pd.DataFrame, 
        message: str = None,
        csv_filename: str = None,
        cc: List[str] = None
    ) -> bool:
        """
        发送数据报告邮件
        
        Args:
            recipient: 收件人邮箱
            subject: 邮件主题
            data: 要发送的数据
            message: 正文内容
            csv_filename: CSV附件文件名
            cc: 抄送列表
            
        Returns:
            是否发送成功
        """
        if not self.sender_email or not self.sender_password:
            print("请先配置发件人信息")
            return False
        
        if message is None:
            message = f"""
您好,

附件是您请求的数据报告，包含 {len(data)} 条记录。

如有任何问题，请随时联系。

此致
风险建模分析助手
            """
        
        if csv_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"data_report_{timestamp}.csv"
        
        # 创建临时CSV文件
        temp_path = f"/tmp/{csv_filename}"
        data.to_csv(temp_path, index=False, encoding='utf-8-sig')
        
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # 添加正文
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # 添加附件
            with open(temp_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=csv_filename)
                part['Content-Disposition'] = f'attachment; filename="{csv_filename}"'
                msg.attach(part)
            
            # 发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            all_recipients = [recipient]
            if cc:
                all_recipients.extend(cc)
            
            server.sendmail(self.sender_email, all_recipients, msg.as_string())
            server.quit()
            
            print(f"邮件已成功发送给 {recipient}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def send_monitoring_alert(
        self, 
        recipient: str, 
        anomaly_count: int, 
        anomaly_types: List[str], 
        details: str = None
    ) -> bool:
        """
        发送监控告警邮件
        
        Args:
            recipient: 收件人邮箱
            anomaly_count: 异常数量
            anomaly_types: 异常类型列表
            details: 详细信息
            
        Returns:
            是否发送成功
        """
        subject = f"⚠️ 数据监控告警 - 发现 {anomaly_count} 个异常"
        
        message = f"""
您好,

数据监控检测到异常，详情如下:

异常数量: {anomaly_count}
异常类型: {', '.join(anomaly_types)}
检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        if details:
            message += f"\n详细信息:\n{details}\n"
        
        message += f"""
请及时查看并处理。

此致
风险建模分析助手
        """
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()
            
            print(f"告警邮件已发送给 {recipient}")
            return True
            
        except Exception as e:
            print(f"告警邮件发送失败: {e}")
            return False
    
    def send_model_performance_report(
        self, 
        recipient: str, 
        model_name: str, 
        metrics: Dict[str, float],
        message: str = None
    ) -> bool:
        """
        发送模型性能报告
        
        Args:
            recipient: 收件人邮箱
            model_name: 模型名称
            metrics: 性能指标
            message: 自定义消息
            
        Returns:
            是否发送成功
        """
        subject = f"📊 模型性能报告 - {model_name}"
        
        metrics_text = "\n".join([f"  {k}: {v:.4f}" for k, v in metrics.items()])
        
        if message is None:
            message = f"""
您好,

模型 {model_name} 的性能指标如下:

{metrics_text}

训练时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

如有问题，请查看详细日志。

此致
风险建模分析助手
            """
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient, msg.as_string())
            server.quit()
            
            print(f"模型性能报告已发送给 {recipient}")
            return True
            
        except Exception as e:
            print(f"模型性能报告发送失败: {e}")
            return False

# 业务取数需求模板
class DataRequestTemplate:
    """数据取数模板"""
    
    @staticmethod
    def create_basic_report(data: pd.DataFrame, request_info: Dict[str, Any]) -> str:
        """
        创建基础数据报告
        
        Args:
            data: 数据
            request_info: 请求信息
            
        Returns:
            格式化的报告文本
        """
        report = f"""
数据取数报告
{'='*50}

请求信息:
  请求人: {request_info.get('requester', '未知')}
  部门: {request_info.get('department', '未知')}
  请求时间: {request_info.get('request_time', '未知')}
  需求描述: {request_info.get('description', '未知')}

数据概况:
  记录数: {len(data)}
  字段数: {len(data.columns)}
  时间范围: {request_info.get('date_range', '未知')}
  
数据字段:
  {', '.join(data.columns.tolist())}

数据预览:
{data.head(10).to_string()}

{'='*50}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return report
    
    @staticmethod
    def create_summary_report(data: pd.DataFrame, request_info: Dict[str, Any]) -> str:
        """
        创建汇总数据报告
        
        Args:
            data: 汇总数据
            request_info: 请求信息
            
        Returns:
            格式化的汇总报告
        """
        report = f"""
数据汇总报告
{'='*50}

请求信息:
  请求人: {request_info.get('requester', '未知')}
  部门: {request_info.get('department', '未知')}
  统计周期: {request_info.get('period', '未知')}

汇总统计:
{data.to_string(index=True)}

{'='*50}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return report