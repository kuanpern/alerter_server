import datetime
import pendulum
from airflow import DAG
from airflow.operators.bash_operator import BashOperator

########################################################
############## DECLARE DAG AND PARAMETERS ##############
########################################################
project_dir = '/home/ubuntu/apps/alerter_server'
config_file = '/home/ubuntu/.keys/alerter_server.key.yaml'
tempo       = 'hourly'

local_tz = pendulum.timezone("Asia/Singapore")
cron_string = '0 * * * *'
DAG_name = 'hourly_alert_email_sender'
dag = DAG(
  DAG_name, 
  schedule_interval = cron_string,
  default_args={
  'owner': 'airflow',
  'depends_on_past': False,
  'start_date': datetime.datetime(2019, 1, 1, tzinfo=local_tz),
  'email': ['admin@example.com'],
  'email_on_failure': False,
  'email_on_retry'  : False,
  'retries': 1,
  'retry_delay': datetime.timedelta(minutes=1),
})
####################### END ###########################


###################################
############## TASKS ##############
###################################
cmd_template = '''
cd {project_dir}; 
venv/bin/python send_alerts_email.py \
  --config {config_file} \
  --tempo {tempo}
'''
cmd = cmd_template.format(
  project_dir=project_dir,
  config_file=config_file,
  tempo=tempo
) # end cmd

task_id='hourly_send_mail'
send_mail = BashOperator(task_id=task_id, dag=dag, bash_command=cmd)
############### END ###############
