import pymysql
import pandas as pd

conn = pymysql.connect(
    host='47.119.181.195',
    port=9030,
    user='taoshun_fk_zf',
    password='P5]xk!9,u$t[JIPf1~4)',
    database='dws'
)

sql = """
select province,
       store_name,
       date_format(complete_time, '%Y-%m') '竣工时间',
       count(*) '办单数',
       sum(case when step_num_repay_status = 2 then 1 else 0 end) '逾期数',
       round(sum(case when step_num_repay_status = 2 then 1 else 0 end) / count(*), 4) '逾期率',
       min(complete_time) '最早办单时间',
       max(complete_time) '最新办单时间',
       sum(case when old_new_customer = '新客户' then 1 else 0 end) '新客数',
       round(sum(case when old_new_customer = '新客户' then 1 else 0 end) / count(*), 4) '新客占比',
       round(sum(case when operator_real = 3 then 1 else 0 end) / count(*), 4) '本网占比'
from dws_credit_yzf_order_complete
where source_business_type = '淘顺实时授信'
  and store_name = '建资@益阳沅江中心营业厅'
group by province, store_name, 竣工时间
having 办单数 >= 5
order by 竣工时间 DESC;
"""

df = pd.read_sql_query(sql, conn)
conn.close()

print(df.to_string(index=False))
