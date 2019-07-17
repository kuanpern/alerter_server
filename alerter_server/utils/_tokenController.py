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

class tokenController:
	token_cols = ['_uuid', 'token', '_created_at', 'status']
	token_template = {_: None for _ in token_cols}

	def _get_session(self):
		Session = sessionmaker(bind=self.conn_engine)
		session = Session()
		return session
	# end def

	def __init__(self, conn_str):
		"""Initialize a token controller object

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
		self.tokentable = None
		self._prepare_base()
	# end def

	def _prepare_base(self):
		self.metadata.reflect(bind=self.conn_engine)
		self.Base = automap_base(metadata=self.metadata)
		self.Base.prepare()
	# end def

	def set_tokentable(self, name):
		"""Set the current token table

		Args:
		  :name (String): Name of the target token table

		Returns:
		  :None
		"""
		self.tblname = name
		self.tokentable = name
	# end def

	def list_tokentables(self, suffix='_tokens'):
		"""List all (token) tables in the database

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

	def export_tokentable(self, name):
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
	#### CRUD for tokentable ####
	#############################

	def init_tokentable(self, name, suffix="_tokens", prefix="alerts_"):
		"""Initialize a token table

		Args:
		  :name (String): Name of the token table

		Returns:
		  :None
		"""
		# TODO: check engine name and tokentablename
		def is_acceptable_name(name):
			return str.isalnum(name.replace('-', '').replace('_', ''))
		# end def
		assert is_acceptable_name(name)  , 'token table name must be alpha-numerical and (_, -) only'
		assert is_acceptable_name(suffix) or suffix=='', 'token table suffix must be alpha-numerical and (_, -) only'
		assert is_acceptable_name(prefix) or prefix=='', 'token table suffix must be alpha-numerical and (_, -) only'

		table_name = prefix+name+suffix
		tokenTable = Table(table_name, self.metadata,
		  Column('_uuid',       String(40), primary_key=True),
		  Column('token',       Text,       nullable=False),
		  Column('_created_at', REAL,       nullable=False),
		  Column('status',      String(20), nullable=False),
		) # end table
		self.metadata.create_all(self.conn_engine)

		self.tblname = None
		self._prepare_base()
		self.set_tokentable(name+suffix)
	# end def

	def delete_tokentable(self, name, backup_filepath, chunksize=1000):
		"""Delete a token table

		Args:
		  :name (String): Name of the token table
		  :backup_filepath (String): Backup filepath
		  :chunksize (Integer): chunk size of downloading process from database

		Returns:
		  :(None)
		"""
		# get engine name and tokentable name
		_uuid = ''.join(list(filter(str.isalnum, str(uuid.uuid4()))))[:8]
		print('type the following passphrase: %s' % (_uuid,))
		det = input('passphrase: ')
		if det != _uuid:
			raise ValueError('Wrong input passphrase. Will not proceed deletion of token table.')
		# end if

		# BACKUP
		df = self.export_tokentable(name)
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
	###### CRUD for tokens #####
	############################
	def issue_new_token(self, table_name=None):
		"""Add a token to the token table

		Returns:
		  :String
		"""

		if table_name is None:
			assert self.tblname is not None, 'token table not set'
			table_name = self.tblname
		# end if

		new_token = str(uuid.uuid4())
		curtime = int(time.time())
		_token = copy.deepcopy(self.token_template)
		_token.update({
		  "_uuid"        : str(uuid.uuid4()),
		  "token"        : new_token,
		  "_created_at"  : curtime,
		  "status"       : 'active',
		}) # end token

		# insert operation for token table
		table = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		insert_op = table.insert().values([_token])
		self.conn_engine.execute(insert_op)

		return new_token
	# end def

	def list_tokens(self, table_name=None):
		"""List all tokens in the token table

		Args:
		  :table_name (String): token table name

		Returns:
		  :DataFrame
		"""

		if table_name is None:
			assert self.tblname is not None, 'token table not set'
			table_name = self.tblname
		# end if
		# load token model
		tokentable = self.Base.classes[table_name]

		# build query statement
		session = self._get_session()
		query = session.query(tokentable)
		# query and pipe to pd dataframe
		df = pd.read_sql_query(query.statement, query.session.bind)
		session.close()
		return df
	# end def

	def revoke_token(self, token_uuid):
		"""deactivate a token

		Args:
		  :token_uuid (String): UUID of the token
		  :params (Dict): new set of values for token

		Returns:
		  :(None)
		"""
		# validity check
		assert self.tblname is not None, 'token table not set'

		params = {'status': 'deactivated'}
		# update operation
		tokentable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		update_op = tokentable.update().where(tokentable.c._uuid==token_uuid).values(**params)

		# commit
		self.conn_engine.execute(update_op)
	# end def

	def delete_token(self, token_uuid):
		"""Delete a token

		Args:
		  :token_uuid (String): token UUID

		Returns:
		  :Database response
		"""

		# delete operation
		tokentable = sqlalchemy.Table(self.tblname, self.metadata, autoload=True, autoload_with=self.conn_engine)
		delete_op = tokentable.delete().where(tokentable.c._uuid==token_uuid)

		# commit
		res = self.conn_engine.execute(delete_op)
	# end def

# end class
