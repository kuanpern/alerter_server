import os
import sys
import yaml
import time
import sqlalchemy
from sqlalchemy.orm import sessionmaker
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

def handle_one_table(alert_table, tempo, conn, email_provider, sender_email, email_api_key ):
	logger.info('working on table "%s" ...' % alert_table)
	# find all unprocessed entries
	
	# TODO: to improve query pattern
	DF = pd.read_sql_table(alert_table, con=conn)
	DF = DF[DF['_IsProcessed'] == False]
	DF = DF[DF['tempo']        == tempo]

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
		handle_one_channel(alert_table, _DF, channel, tempo, conn, email_provider, sender_email, email_api_key )
	# end for

# end def

def handle_one_channel(alert_table, DF, channel, tempo, conn, email_provider, sender_email, email_api_key ):
	logger.info('working on channel "%s" ...' % channel)
	
	meta = sqlalchemy.MetaData()
	meta.reflect(bind=conn)
	table = sqlalchemy.Table(alert_table, meta, autoload=True, autoload_with=conn.engine)

	if len(DF) == 0:
		logger.info(' - no alerts')
		return
	# end if

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
	# TODO: to improve query pattern
	tblname = alert_table+'_subscription'
	DF_subscription = pd.read_sql_table(tblname, con=conn)
	DF_subscription = DF_subscription[DF_subscription['channel'] == channel]
	DF_subscription = DF_subscription[DF_subscription['status' ] == 'active']
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
			provider  = email_provider,
			emailUser = sender_email,
			recipient = _email,
			api_key = email_api_key ,
			subject = subject,
			text = text,
			attachmentFilePaths = [filename]
		) # end send email
		responses.append(res)
	# end for

	os.remove(filename)

	# mark channel entries as processed
	logger.info('updating alert entry status ...')
	Session = sessionmaker(bind=conn)
	session = Session()

	_uuids = DF['_uuid'].values
	for _uuid in _uuids:
		stmt = table.update() \
		  .where(table.c._uuid == _uuid) \
		  .values({'_IsProcessed': True, '_processed_at': timestamp})
		session.execute(stmt)
	# end for
	session.commit()
	session.close()
	
# end def

def main(conn_str, email_api_key , email_provider, sender_email, tempo):
	# initiate DB connection
	engine = sqlalchemy.create_engine(conn_str)
	conn = engine.connect()

	# get all alert tables
	alert_tables = get_alert_tables(engine)
	for alert_table in alert_tables:
		handle_one_table(alert_table, tempo, conn, email_provider, sender_email, email_api_key )
	# end for
	conn.close()
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
		email_api_key  = configs['email_api_key']
		sender_email   = configs['sender_email']
		email_provider = configs['email_provider']
	# end with

	# actually run
	main(
	  conn_str       = conn_str, 
	  email_api_key  = email_api_key , 
	  email_provider = email_provider,
	  sender_email   = sender_email,
	  tempo          = tempo
	) # end main
# end def

if __name__ == '__main__':
	cli()
# end if
