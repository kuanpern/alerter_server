import os
import time
import yaml
import uuid
import sqlalchemy
import opends.easy_messaging
from multiprocessing import Process
import flask
from flask import Flask, abort
import utils
import logging
logger = logging.getLogger()

# initialize flask app
app = Flask(__name__)

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
	import argparse
	parser = argparse.ArgumentParser(description='Send alerts through emails')
	parser.add_argument('--config',  help='path to configuration file (.yaml)', required=True)
	args = vars(parser.parse_args())

	# read configuration
	config_file = args['config'] # os.environ['HOME']+'/.keys/scube_alerter.key.yaml'
	with open(config_file, 'r') as fin:
		configs = yaml.load(fin, Loader=yaml.SafeLoader)
		conn_str    = configs['conn_str']
		slack_token = configs['slack_token']
	# end with
	engine = sqlalchemy.create_engine(conn_str)

	# initialize the controller
	controller = utils.Controller(conn_str)

	# start the app
	app.run(host='0.0.0.0', port=8080, debug=True)
# end if
