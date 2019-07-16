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

class subscriptionController:
	subscription_cols = ['_uuid', 'username', '_created_at', 'status', 'email', 'channel']
	subscription_template = {_: None for _ in subscription_cols}

	def _get_session(self):
		Session = sessionmaker(bind=self.conn_engine)
		session = Session()
		return session
	# end def

	def __init__(self, conn_str):
		"""Initialize a subscription controller object

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
		self.subscriptiontable = None
		self._prepare_base()
	# end def

	def _prepare_base(self):
		self.metadata.reflect(bind=self.conn_engine)
		self.Base = automap_base(metadata=self.metadata)
		self.Base.prepare()
	# end def

	def set_subscriptiontable(self, name):
		"""Set the current subscription table

		Args:
		  :name (String): Name of the target subscription table

		Returns:
		  :None
		"""
		self.tblname = name
		self.subscriptiontable = name
	# end def

	def list_subscriptiontables(self, prefix='alerts_', suffix='_subscription'):
		"""List all (subscription) tables in the database

		Args:
		  :None

		Returns:
		  :List of Strings
		"""
		assert isinstance(suffix, str)

		table_names = self.conn_engine.table_names()
		output = []
		for name in table_names:
			if name.endswith(suffix):
				output.append(name)
			# end if
		# end for

		return output
	# end def

	def export_subscriptiontable(self, name):
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

	####################################
	#### CRUD for subscriptiontable ####
	####################################

	def init_subscriptiontable(self, name, suffix="_subscription", prefix="alerts_"):
		"""Initialize a subscription table

		Args:
		  :name (String): Name of the subscription table

		Returns:
		  :None
		"""
		# TODO: check engine name and subscriptiontablename
		def is_acceptable_name(name):
			return str.isalnum(name.replace('-', '').replace('_', ''))
		# end def
		assert is_acceptable_name(name)  , 'subscription table name must be alpha-numerical and (_, -) only'
		assert is_acceptable_name(prefix) or prefix=='', 'subscription table prefix must be alpha-numerical and (_, -) only'

		table_name = prefix+name+suffix
		subscriptionTable = Table(table_name, self.metadata,
		  Column('_uuid',       String(40),  primary_key=True),
		  Column('username',    Text,        nullable=False),
		  Column('_created_at', REAL,        nullable=False),
		  Column('status',      String(20),  nullable=False),
		  Column('email',       String(320), nullable=False),
		  Column('channel',     Text,        nullable=False),
		) # end table
		self.metadata.create_all(self.conn_engine)

		self.tblname = None
		self._prepare_base()
		self.set_subscriptiontable(prefix+name)
	# end def

	def delete_subscriptiontable(self, name, backup_filepath, chunksize=1000):
		"""Delete a subscription table

		Args:
		  :name (String): Name of the subscription table
		  :backup_filepath (String): Backup filepath
		  :chunksize (Integer): chunk size of downloading process from database

		Returns:
		  :(None)
		"""
		# get engine name and subscriptiontable name
		_uuid = ''.join(list(filter(str.isalnum, str(uuid.uuid4()))))[:8]
		print('type the following passphrase: %s' % (_uuid,))
		det = input('passphrase: ')
		if det != _uuid:
			raise ValueError('Wrong input passphrase. Will not proceed deletion of subscription table.')
		# end if

		# BACKUP
		df = self.export_subscriptiontable(name)
		if len(df) == 0:
			print('table is empty. not backing up.')
		else:
			df.to_excel(backup_filepath)
		# end if

		# Actually delete
		tbl = self.Base.classes[name]
		tbl.__table__.drop(self.conn_engine)
	# end def


	###################################
	###### CRUD for subscriptions #####
	###################################
	def add_subscription(self, username, email, channel):
		"""Add a subscription to the subscription table

		Args:
		  :username (String): user name
		  :email (String): user email
		  :channel (String): channel to subscribe to

		Returns:
		  :(None)
		"""

		assert self.tblname is not None, 'subscription table not set'

		curtime = int(time.time())
		_subscription = copy.deepcopy(self.subscription_template)
		_subscription.update({
		  "_uuid"      : str(uuid.uuid4()),
		  "username"   : username,
		  "_created_at": curtime,
		  "status"     : "active",
		  "email"      : email,
		  "channel"    : channel,
		}) # end subscription

		# insert operation for subscription table
		table = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		insert_op = table.insert().values([_subscription])
		self.conn_engine.execute(insert_op)
	# end def

	def list_subscriptions(self, table_name=None, offset=0, limit=0):
		"""List all subscriptions in the subscription table

		Args:
		  :table_name (String): subscription table name
		  :offset (Integer): offset n records
		  :limit (Integer): limit to n records

		Returns:
		  :DataFrame
		"""

		if table_name is None:
			assert self.tblname is not None, 'subscription table not set'
			table_name = self.tblname
		# end if
		# load subscription model
		subscriptiontable = self.Base.classes[table_name]

		# build query statement
		session = self._get_session()
		query = session.query(subscriptiontable)
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

	def show_subscription(self, subscription_uuid):
		"""Show the parameters of a subscription

		Args:
		  :subscription_uuid (String): subscription UUID

		Returns:
		  :Dict
		"""

		assert self.tblname is not None, 'subscription table not set'
		# load subscription model
		subscriptiontable = self.Base.classes[self.tblname]

		# query
		session = self._get_session()
		query = session.query(subscriptiontable)
		res = query.filter(subscriptiontable._uuid == subscription_uuid).first()
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

	def update_subscription(self, subscription_uuid, params):
		"""update a subscription

		Args:
		  :subscription_uuid (String): UUID of the subscription
		  :params (Dict): new set of values for subscription

		Returns:
		  :(None)
		"""
		# validity check
		assert self.tblname is not None, 'subscription table not set'
		assert isinstance(params, dict), 'params must be Dict type'
		assert '_uuid' not in params, 'subscription uuid is immutable'

		updated_at = int(time.time())

		# update operation
		subscriptiontable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		update_op = subscriptiontable.update().where(subscriptiontable.c._uuid==subscription_uuid).values(**params)

		# commit
		self.conn_engine.execute(update_op)
	# end def

	def delete_subscription(self, subscription_uuid):
		"""Delete a subscription

		Args:
		  :subscription_uuid (String): subscription UUID

		Returns:
		  :Database response
		"""

		# delete operation
		subscriptiontable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		delete_op = subscriptiontable.delete().where(subscriptiontable.c._uuid==subscription_uuid)

		# commit
		res = self.conn_engine.execute(delete_op)
	# end def

# end class
