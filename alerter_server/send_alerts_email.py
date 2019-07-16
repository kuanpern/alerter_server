import os
import sys
import yaml
import time
import sqlalchemy
import pandas as pd
import uuid
import opends
import opends.easymail
import datetime
import logging
_handler = logging.StreamHandler(sys.stdout)
_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(_handler)

# TODO:
# support other email service provider
# if too big, upload to s3, send s3 link

def get_alert_tables(engine):
	logger.info('getting tables ...')
	table_names = engine.table_names()
	output = []
	for name in table_names:
		if not(name.startswith('alerts')):
			continue
		if name.endswith('_subscription'):
			continue
		if name.endswith('_tokens'):
			continue
		output.append(name)
	# end for
	return output
# end def

def handle_one_table(alert_table, tempo, conn, sender_email, sendgrid_token):
	logger.info('working on table "%s" ...' % alert_table)
	# find all unprocessed entries
	cmd = 'SELECT * FROM {alert_table} WHERE _isProcessed=0 AND tempo="{tempo}"'.format(
		alert_table = alert_table,
		tempo       = tempo,
	) # end cmd
	DF = pd.read_sql_query(cmd, con=conn)

	# formatting entries
	DF['timestamp'] = [pd.Timestamp.fromtimestamp(val).isoformat()+'Z' for val in DF['_updated_at']]
	DF = DF.sort_values(by='timestamp')

	# separate into different channels
	DF_channels = {}
	for channel in DF['channel'].unique():
		DF_channels[channel] = DF[DF['channel'] == channel]
	# end for
	for channel, _DF in DF_channels.items():
		logger.info('processing '+channel)
		handle_one_channel(alert_table, _DF, channel, tempo, conn, sender_email, sendgrid_token)
	# end for

# end def

def handle_one_channel(alert_table, DF, channel, tempo, conn, sender_email, sendgrid_token):
	logger.info('working on channel "%s" ...' % channel)

	# timestamp
	timestamp = time.time()
	timestamp_str = str(pd.Timestamp.fromtimestamp(timestamp)).split('.')[0]

	# separate title to dfiffent dataframe
	DFs = {}
	for title in DF['title'].unique():
		DFs[title] = DF[DF['title'] == title]
	# end for
	filename = '/tmp/'+str(uuid.uuid4())+'.xlsx'

	# write to excel file, multiple sheet
	writer = pd.ExcelWriter(filename, engine='xlsxwriter')
	for title in DFs.keys():
		df = DFs[title]
		df = df[['timestamp', 'title', 'msg']]
		df.to_excel(writer, sheet_name=title)
	# end for
	writer.save()

	# read subscriptions
	cmd = "SELECT * FROM alerts_backend_subscription WHERE channel='{channel}' AND status='active'"
	cmd = cmd.format(channel='generalalerts')
	DF_subscription = pd.read_sql_query(cmd, con=conn)
	targets = list(DF_subscription.transpose().to_dict().values())

	# send the emails
	responses = []
	for item in targets:

		# build email
		_email = item['email']
		username = item['username']
		subject = '[{tempo}-alerts] {channel} {timestamp}'.format(
			tempo   = tempo,
			channel = channel,
			timestamp = timestamp_str,
		) # end subject
		text = 'Hi {username}, please see attachment for alerts.'.format(username=username)

		# send email
		logger.info(' send email to %s' % username)
		res = opends.easymail.send_email(
			emailUser = sender_email,
			recipient = _email,
			api_key = sendgrid_token,
			subject = subject,
			text = text,
			attachmentFilePaths = [filename]
		) # end send email
		responses.append(res)
	# end for

	os.remove(filename)

	# mark channel entries as processed
	logger.info('updating alert entry status ...')
	cmd_template = 'UPDATE {tblname} SET _IsProcessed=TRUE, _processed_at={timestamp} WHERE _uuid="{UUID}"'
	_uuids = DF['_uuid'].values
	for _uuid in _uuids:
		cmd = cmd_template.format(
			tblname = alert_table,
			UUID    = _uuid,
			timestamp = timestamp,
		) # end cmd
		conn.execute(cmd)
	# end for
	return responses
# end def

def main(conn_str, sendgrid_token, sender_email, tempo):
	# initiate DB connection
	engine = sqlalchemy.create_engine(conn_str)
	conn = engine.connect()

	# get all alert tables
	alert_tables = get_alert_tables(engine)
	for alert_table in alert_tables:
		handle_one_table(alert_table, tempo, conn, sender_email, sendgrid_token)
	# end for
# end def

def cli():
	import argparse
	parser = argparse.ArgumentParser(description='Send alerts through emails')
	parser.add_argument('--config',  help='path to configuration file (.yaml)', required=True)
	parser.add_argument('--tempo',   help='tempo of the alert entries. Supports only "hourly" and "daily"', required=True)
	args = vars(parser.parse_args())

	config_file = args['config'] # os.environ['HOME']+'/.keys/scube_alerter.key.yaml'
	tempo       = args['tempo']
	assert tempo in ['hourly', 'daily']
	# read configuration
	with open(config_file, 'r') as fin:
		configs = yaml.load(fin, Loader=yaml.SafeLoader)
		conn_str       = configs['conn_str']
		sendgrid_token = configs['sendgrid_token']
		sender_email   = configs['sender_email']
	# end with

	# actually run
	main(
	  conn_str       = conn_str, 
	  sendgrid_token = sendgrid_token, 
	  sender_email   = sender_email,
	  tempo          = tempo
	) # end main
# end def

if __name__ == '__main__':
	cli()
# end if
