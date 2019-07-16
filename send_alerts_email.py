import os
import sys
import time
import pandas as pd
import uuid
import opends
import opends.easymail
import logging
from models.alert import Alert
from models.subscription import Subscription
from dotenv import load_dotenv
load_dotenv()
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

# timestamp
timestamp = time.time()
timestamp_str = str(pd.Timestamp.fromtimestamp(timestamp)).split('.')[0]

def main(tempo, sender_email, sendgrid_token):
	logger.info('working on table "%s" ...' % Alert.__table__.name)
	
	DF = Alert.list_alerts(tempo=tempo)

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
		handle_one_channel(_DF, channel, tempo, sender_email, sendgrid_token)
	# end for
# end def

def handle_one_channel(DF, channel, tempo, sender_email, sendgrid_token):
	logger.info('working on channel "%s" ...' % channel)
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
	DF_subscription = Subscription.list_subs(channel='general')
	targets = list(DF_subscription.transpose().to_dict().values())

	# send the emails
	responses = []
	for item in targets:

		# build email
		_email = item['email']
		username = item['user_name']
		subject = '[{tempo}-alerts] {channel} {timestamp}'.format(
			tempo   = tempo,
			channel = channel,
			timestamp = timestamp_str,
		) # end subject
		text = 'Hi {username}, please see attachment for alerts.'.format(username=username)

		# send email
		logger.info(' send email to %s' % username)
		print(sendgrid_token)
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
	
	_uuids = DF['_uuid'].values
	for _uuid in _uuids:
		data = {'alert_uuid': _uuid, 'is_processed': True, 'processed_at': timestamp}
		alert = Alert(**data)
		alert.update()
	# end for
	return responses
# end def

def cli():
	import argparse
	parser = argparse.ArgumentParser(description='Send alerts through emails')
	parser.add_argument('--tempo',   help='tempo of the alert entries. Supports only "hourly" and "daily"', required=True)
	args = vars(parser.parse_args())

	tempo = args['tempo']
	assert tempo in ['hourly', 'daily']

	# actually run
	main(
		tempo          = tempo,
		sender_email   = os.getenv('SENDER_EMAIL'),
	 	sendgrid_token = os.getenv('SENDGRID_TOKEN') 
	) # end main
# end def

if __name__ == '__main__':
	cli()
# end if
