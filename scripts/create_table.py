import yaml
import argparse
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, REAL, String, Boolean

def create_alert_table(conn_str, table_name):
	engine = create_engine(conn_str)
	meta = MetaData()

	# define table
	AlertTable = Table(table_name, meta,
	  Column('_uuid', String(40),  primary_key=True),
	  Column('title',   Text),
	  Column('msg',  Text),
	  Column('channel', Text),
	  Column('_updated_at', REAL, nullable=False),
	  Column('_IsProcessed', Boolean,  nullable=False, default=False),
	  Column('_processed_at', REAL, nullable=False),
	) # end table

	# create table
	print('creating table ...')
	meta.create_all(engine)
	print('done')
# end def

def cli():
	# parse inputs
	parser = argparse.ArgumentParser(description='Create alert table')
	parser.add_argument('--key',    help="config file with database conn_str (.yaml)", type=str, required=True)
	parser.add_argument('--table_name',   help="table name",   type=str, required=True)

	pars = vars(parser.parse_args())
	keyfile      = pars['key']
	table_name   = pars['table_name']

	with open(keyfile, 'r') as fin:
		conn_str = yaml.load(fin, Loader=yaml.SafeLoader)['conn_str']
	# end with
	create_alert_table(conn_str, table_name=table_name)

# end def

if __name__ == '__main__':
	cli()
# end if
