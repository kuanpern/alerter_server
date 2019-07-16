from flask import Flask
from database import init_db
import logging
logger = logging.getLogger()

# initialize flask app
app = Flask(__name__)

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description='Send alerts through emails')
	parser.add_argument('--host',   help='server host name', type=str, required=False, default='0.0.0.0')
	parser.add_argument('--port',   help='port number', type=int, required=False, default=8088)
	parser.add_argument('--debug',  help='debug mode', type=bool, required=False, default=True)
	args = vars(parser.parse_args())

	# read configuration
	host = args['host']
	port = args['port']
	debug_mode = args['debug']
	
	# init database
	init_db()
	
	# start the app
	app.run(host=host, port=port, debug=debug_mode)
# end if
