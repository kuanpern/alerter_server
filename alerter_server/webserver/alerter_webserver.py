import os
import time
import yaml
import uuid
import sqlalchemy
import opends.easy_messaging
from multiprocessing import Process
import flask
from flask import Flask, abort
import logging
logger = logging.getLogger()
import alerter_server
from alerter_server.utils import alertController
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# initialize flask app
app = Flask(__name__)

# read configs
config_file = os.environ['ALERTER_CONFIG_FILE']
with open(config_file, 'r') as fin:
	configs = yaml.load(fin, Loader=yaml.SafeLoader)
# end with
db_conn_str = configs['conn_str']
slack_token = configs['slack_token']
timezone    = configs['timezone']
sendgrid_token = configs['sendgrid_token']
sender_email   = configs['sender_email']

def send_hourly_emails():
	return alerter_server.send_alerts_email.main(
	  conn_str       = db_conn_str,
	  sendgrid_token = sendgrid_token,
	  sender_email   = sender_email,
	  tempo          = 'hourly'
	) # end send mail
# end def

def send_daily_emails():
	return alerter_server.send_alerts_email.main(
	  conn_str       = db_conn_str,
	  sendgrid_token = sendgrid_token,
	  sender_email   = sender_email,
	  tempo          = 'daily'
	) # end send mail
# end def

# init a scheduler
scheduler = BackgroundScheduler({'apscheduler.timezone': timezone})
scheduler.start()
# - add hourly job
scheduler.add_job(send_hourly_emails, CronTrigger.from_crontab('0 * * * *'))
# - add daily job
scheduler.add_job(send_daily_emails,  CronTrigger.from_crontab('0 18 * * *')) # TODO: make configurable


# init engine
engine = sqlalchemy.create_engine(db_conn_str)
controller = alertController(db_conn_str)


def put_db(inputs):
	tblname = inputs.pop('tblname')
	acceptables = ['title', 'msg', 'channel', 'alert_uuid', 'is_processed', 'processed_at', 'tempo']
	pops = set(inputs.keys()) - set(acceptables)
	for key in pops:
		inputs.pop(key)
	# end for

	controller.set_alerttable(tblname)
	controller.add_alert(**inputs)
# end def

def send_msg(inputs):
	tblname = inputs['tblname']
	title   = inputs['title']
	msg     = inputs['msg']
	channel = inputs['channel']

	text = '[{tblname}] | [{title}]\n{msg}'.format(tblname=tblname, title=title, msg=msg)
	response = opends.easy_messaging.send_slack_message(
		channel   = channel,
		text      = text, 
		token     = slack_token, 
		from_user = 'bot'
	) # end message

	# still register to DB
	inputs['is_processed'] = True
	inputs['processed_at'] = time.time()
	put_db(inputs)
# end def

@app.route('/', methods = ['GET'])
def index():
	return 'Hi this is alerter server speaking.'
# end def


@app.route('/<tblname>', methods = ['POST'])
def recv(tblname):
	content = flask.request.get_json()

	# ensure table is there
	if tblname not in engine.table_names():
		return 'Unregistered endpoint "{tblname}"'.format(tblname=tblname), 400
	# end if

	# get tokens
	cmd = 'SELECT token FROM {tblname}_tokens WHERE status = "active"'.format(tblname=tblname)
	conn = engine.connect()
	res = conn.execute(cmd)
	conn.close()
	tokens = [_[0] for _ in res]

	# authentication
	token = content.get('token', None)
	if token not in tokens:
		return 'Authentication failed', 400
	# end if

	# input check
	requireds = ['msg', 'title', 'tempo', 'channel']
	if len(set(requireds) - set(content.keys())) > 0:
		return 'Bad request', 400
	# end if

	_uuid = str(uuid.uuid4())
	content['alert_uuid'] = _uuid
	content['tblname']    = tblname
	tempo = content.get('tempo', 'daily')
	if tempo == 'real-time':
		p = Process(target=send_msg, args=(content,))
	else:
		p = Process(target=put_db  , args=(content,))
	# end if
	p.start()

	return flask.jsonify({'uuid': _uuid})
# end def

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080, debug=True)
# end if
