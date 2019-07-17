import uuid
import json
import time
import pandas as pd
import numpy as np
import copy
import sqlalchemy
import numbers
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, REAL, String, Boolean

class alertController:
	alert_cols = ['_uuid', 'title', 'msg', 'channel', 'tempo', '_updated_at', '_IsProcessed', '_processed_at']
	alert_template = {_: None for _ in alert_cols}

	def _get_session(self):
		Session = sessionmaker(bind=self.conn_engine)
		session = Session()
		return session
	# end def

	def __init__(self, conn_str):
		"""Initialize a alert controller object

		Args:
		  :conn_str (String): sqlalchemy connection string

		Returns:
		  :controller object
		"""

		self.conn_str = conn_str
		self.conn_engine = sqlalchemy.create_engine(self.conn_str, pool_pre_ping=True)
		self.db_name = self.conn_engine.url.database
		self.metadata = sqlalchemy.MetaData()

		self.tblname = None
		self.alerttable = None
		self._prepare_base()
	# end def

	def _prepare_base(self):
		self.metadata.reflect(bind=self.conn_engine)
		self.Base = automap_base(metadata=self.metadata)
		self.Base.prepare()
	# end def

	def set_alerttable(self, name):
		"""Set the current alert table

		Args:
		  :name (String): Name of the target alert table

		Returns:
		  :None
		"""
		self.tblname = name
		self.alerttable = name
	# end def

	def list_alerttables(self, prefix='alerts_', non_suffixes=['_subscription', '_tokens']):
		"""List all (alert) tables in the database

		Args:
		  :None

		Returns:
		  :List of Strings
		"""
		assert isinstance(prefix, str)

		table_names = self.conn_engine.table_names()
		output = []
		for name in table_names:
			if not(name.startswith(prefix)):
				continue
			# end if
			if np.any([name.endswith(suffix) for suffix in non_suffixes]):
				continue
			# end for
			output.append(name)
		# end for

		return output
	# end def

	def export_alerttable(self, name):
		"""Export task table to a DataFrame object

		Args:
		  :name (String): task table name

		Returns:
		  :DataFrame
		"""

		conn = self.conn_engine.connect()
		df = pd.read_sql_table(name, con=conn)
		conn.close()
		return df
	# end def

	#############################
	#### CRUD for alerttable ####
	#############################

	def init_alerttable(self, name, prefix="alerts_"):
		"""Initialize a alert table

		Args:
		  :name (String): Name of the alert table

		Returns:
		  :None
		"""
		# TODO: check engine name and alerttablename
		def is_acceptable_name(name):
			return str.isalnum(name.replace('-', '').replace('_', ''))
		# end def
		assert is_acceptable_name(name)  , 'alert table name must be alpha-numerical and (_, -) only'
		assert is_acceptable_name(prefix) or prefix=='', 'alert table prefix must be alpha-numerical and (_, -) only'

		table_name = prefix+name
		AlertTable = Table(table_name, self.metadata,
		  Column('_uuid', String(40),  primary_key=True),
		  Column('title',   Text),
		  Column('msg',  Text),
		  Column('channel', Text),
		  Column('tempo', String(12), nullable=False),
		  Column('_updated_at', REAL, nullable=False),
		  Column('_IsProcessed', Boolean,  nullable=False, default=False),
		  Column('_processed_at', REAL, nullable=False),
		) # end table
		self.metadata.create_all(self.conn_engine)

		self.tblname = None
		self._prepare_base()
		self.set_alerttable(prefix+name)
	# end def

	def delete_alerttable(self, name, backup_filepath, chunksize=1000):
		"""Delete a alert table

		Args:
		  :name (String): Name of the alert table
		  :backup_filepath (String): Backup filepath
		  :chunksize (Integer): chunk size of downloading process from database

		Returns:
		  :(None)
		"""
		# get engine name and alerttable name
		_uuid = ''.join(list(filter(str.isalnum, str(uuid.uuid4()))))[:8]
		print('type the following passphrase: %s' % (_uuid,))
		det = input('passphrase: ')
		if det != _uuid:
			raise ValueError('Wrong input passphrase. Will not proceed deletion of alert table.')
		# end if

		# BACKUP
		df = self.export_alerttable(name)
		if len(df) == 0:
			print('table is empty. not backing up.')
		else:
			df.to_excel(backup_filepath)
		# end if

		# Actually delete
		tbl = self.Base.classes[name]
		tbl.__table__.drop(self.conn_engine)
	# end def


	############################
	###### CRUD for alerts #####
	############################
	def add_alert(self, title, msg, channel, tempo, alert_uuid=None, is_processed=False, processed_at=None):
		"""Add a alert to the alert table

		Args:
		  :title (String): title of the message
		  :msg (String): content of the message
		  :channel (String): channel to publish the message
		  :alert_uuid (String): alert UUID
		  :is_proceesed (Bool): whether the message has been processed
		  :processed_at (Float): the timestamp of when the message has been processed

		Returns:
		  :(None)
		"""

		assert isinstance(processed_at, numbers.Real) or processed_at is None, 'processed_at must be numeric or None'
		assert self.tblname is not None, 'alert table not set'

		if alert_uuid is None:
			alert_uuid = str(uuid.uuid4())
		# end if
		if processed_at is None:
			processed_at = -1
		# end if

		curtime = int(time.time())
		_alert = copy.deepcopy(self.alert_template)
		_alert.update({
		  "title"    : title,
		  "msg"      : msg,
		  "channel"  : channel,
		  "tempo"    : tempo,
		  "_uuid"    : alert_uuid,
		  "_updated_at"  : curtime,
		  "_IsProcessed" : is_processed,
		  "_processed_at": processed_at,
		}) # end alert

		# insert operation for alert table
		table = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		insert_op = table.insert().values([_alert])
		self.conn_engine.execute(insert_op)
	# end def

	def list_alerts(self, table_name=None, offset=0, limit=0):
		"""List all alerts in the alert table

		Args:
		  :table_name (String): alert table name
		  :offset (Integer): offset n records
		  :limit (Integer): limit to n records

		Returns:
		  :DataFrame
		"""

		if table_name is None:
			assert self.tblname is not None, 'alert table not set'
			table_name = self.tblname
		# end if
		# load alert model
		alerttable = self.Base.classes[table_name]

		# build query statement
		session = self._get_session()
		query = session.query(alerttable)
		# - offset and limit
		if offset != 0:
			query = query.offset(offset)
		# end if
		if limit != 0:
			query = query.limit(limit)
		# end if

		# query and pipe to pd dataframe
		df = pd.read_sql_query(query.statement, query.session.bind)
		session.close()
		return df
	# end def

	def show_alert(self, alert_uuid):
		"""Show the parameters of a alert

		Args:
		  :alert_uuid (String): alert UUID

		Returns:
		  :Dict
		"""

		assert self.tblname is not None, 'alert table not set'
		# load alert model
		alerttable = self.Base.classes[self.tblname]

		# query
		session = self._get_session()
		query = session.query(alerttable)
		res = query.filter(alerttable._uuid == alert_uuid).first()
		session.close()

		# not found
		if res is None:
			return {}
		# end if

		# convert to dict
		swap = vars(res)
		swap = {key: val for key, val in swap.items() if not(key.startswith('_'))}
		res = swap
		return res
	# end def

	def update_alert(self, alert_uuid, params):
		"""update a alert

		Args:
		  :alert_uuid (String): UUID of the alert
		  :params (Dict): new set of values for alert

		Returns:
		  :(None)
		"""
		# validity check
		assert self.tblname is not None, 'alert table not set'
		assert isinstance(params, dict), 'params must be Dict type'
		assert '_uuid' not in params, 'alert uuid is immutable'

		updated_at = int(time.time())
		params['updated_at'] = updated_at

		# update operation
		alerttable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		update_op = alerttable.update().where(alerttable.c._uuid==alert_uuid).values(**params)

		# commit
		self.conn_engine.execute(update_op)
	# end def

	def delete_alert(self, alert_uuid):
		"""Delete a alert

		Args:
		  :alert_uuid (String): alert UUID

		Returns:
		  :Database response
		"""

		# delete operation
		alerttable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		delete_op = alerttable.delete().where(alerttable.c._uuid==alert_uuid)

		# commit
		res = self.conn_engine.execute(delete_op)

		return res
	# end def

# end class
