import uuid
import json
import time
import pandas as pd
import copy
import numbers
from sqlalchemy import and_
from sqlalchemy import Column, Integer, Text, REAL, String, Boolean
from database import Base, engine
from database import db_session as session
from os.path import stat

class Subscription(Base):
    TABLE_NAME = 'subscription'
    
    __tablename__ = TABLE_NAME
    
    tables = engine.table_names()
    if TABLE_NAME not in tables:
        __table_args__ = {'extend_existing': True}

    # Schema definition
    _uuid = Column(String(40), primary_key=True)
    user_name = Column(Text)
    _created_at = Column(REAL, default=None)
    status = Column(String(20), default=None)
    email = Column(String(320), default=None)
    channel = Column(Text)
    
    def __init__(self, user_name, email, channel, sub_uuid=None, status='active'):
        self._uuid = sub_uuid
        self.user_name = user_name
        self.email = email
        self.channel = channel
        self.status = status
        self._created_at = int(time.time())
    # end def
    
    def add(self):
        # validity check
        self._validation()
        
        if self._uuid is None:
            self._uuid = str(uuid.uuid4())
        
        session.add(self)
        session.commit()
    # end def   
        
    def _validation():
        pass
    # end def
    
    @classmethod
    def list_subs(cls, channel=None, status='active'):
        """List all subs in the subscription table

        Args:
          :channel (String)
          :status (String)

        Returns:
          :DataFrame
        """
        # end if

        # build query statement
        query = cls.query
        if channel is not None:
            query = query.filter(and_(
                cls.channel==channel,
                cls.status==status
            ))

        # query and pipe to pd dataframe
        df = pd.read_sql_query(query.statement, query.session.bind)
        return df
    # end def