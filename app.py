import yaml
import uuid
import sqlalchemy
import opends.easy_messaging
from multiprocessing import Process
from flask import Flask
from flask import abort
import utils
import logging

# initialize flask app
app = Flask(__name__)

# read configuration
config_file = os.environ['HOME']+'/.keys/scube_alerter.key.yaml'
with open(config_file, 'r') as fin:
	conn_str = yaml.load(fin, Loader=yaml.SafeLoader)
# end with

tokens = {}

cmd = 'SELECT token FROM alerts_backend_tokens WHERE status = "active"';


# initialize the controller
controller = utils.Controller(conn_str)


def put_db(inputs):
	tblname = inputs.pop('tblname')
	acceptables = ['title', 'msg', 'channel', 'alert_uuid', 'is_processed', 'processed_at']
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
	return opends.easy_messaging.send_slack_message(
		channel   = channel,
		text      = text, 
		token     = slack_token, 
		from_user = 'bot'
	) # end message
# end def

@app.route('/<tblname>', methods = ['POST'])
def recv(tblname):
	content = flask.request.get_json()

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
