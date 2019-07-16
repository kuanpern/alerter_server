import uuid
import time
import pandas as pd
import numbers
from sqlalchemy import Column, Integer, Text, REAL, String, Boolean
from sqlalchemy import and_
from database import Base, engine
from database import db_session as session
from utils import ins_to_dict

class Alert(Base):
    TABLE_NAME = 'alerts'
    
    __tablename__ = TABLE_NAME
    
    tables = engine.table_names()
    if TABLE_NAME not in tables:
        __table_args__ = {'extend_existing': True}

    # Schema definition
    _uuid = Column(String(40), primary_key=True)
    title = Column(Text)
    msg = Column(Text)
    channel = Column(Text)
    tempo =  Column(String(12))
    _updated_at = Column(REAL, nullable=False)
    _IsProcessed = Column(Boolean, nullable=False,  default=False)
    _processed_at = Column(REAL, nullable=False)

    ############################
    ###### CRUD for alerts #####
    ############################
    def __init__(self, title=None, msg=None, channel=None, tempo=None, alert_uuid=None, is_processed=None, processed_at=None):
        """Add a alert to the alert table

        Args:
          :title (String): title of the message
          :msg (String): content of the message
          :channel (String): channel to publish the message
          :tempo (String): daily or real-time alert
          :alert_uuid (String): alert UUID
          :is_proceesed (Bool): whether the message has been processed
          :processed_at (Float): the timestamp of when the message has been processed

        Returns:
          :(None)
        """
        curtime = int(time.time())
        
        self.title = title
        self.msg = msg
        self.channel = channel
        self.tempo = tempo
        self._uuid = alert_uuid
        self._updated_at = curtime
        self._IsProcessed = is_processed
        self._processed_at = processed_at
    # end def
    
    def add(self):
        # validity check
        self._validation()
        
        if self._uuid is None:
            self._uuid = str(uuid.uuid4())
        
        if self._IsProcessed is None:
            self._IsProcessed = False
        
        if self._processed_at is None:
            self._processed_at = -1
        
        session.add(self)
        session.commit()
        
    def update(self):
        # validity check
        self._validation(is_new=False)
        
        data = ins_to_dict(self)
        updates = {}
        keys = ['title', 'msg', 'channel', 'tempo', '_IsProcessed', '_processed_at']
        
        for key in keys:
            if data[key] is not None: updates[key] = data[key]

        Alert.query.filter(Alert._uuid == self._uuid).update(updates)
        session.commit()
    # end def

    def delete(self):
        # validity check
        self._validation(is_new=False)
        
        Alert.query.filter(Alert._uuid == self._uuid).delete()
        session.commit()
    # end def

    @classmethod
    def list_alerts(cls, offset=0, limit=0, tempo=None, is_processed=0):
        """List all alerts in the alert table

        Args:
          :offset (Integer): offset n records
          :limit (Integer): limit to n records
          :tempo (String)
          :_isProcessed (Boolean)

        Returns:
          :DataFrame
        """
        # end if

        # build query statement
        query = cls.query
        if tempo is not None:
            query = query.filter(and_(
                cls.tempo==tempo,
                cls._IsProcessed==is_processed
            ))
        
        # - offset and limit
        if offset != 0:
            query = query.offset(offset)
        # end if
        if limit != 0:
            query = query.limit(limit)
        # end if

        # query and pipe to pd dataframe
        df = pd.read_sql_query(query.statement, query.session.bind)
        return df
    # end def

    def show_alert(self):
        """Show the parameters of a alert

        Args: None

        Returns:
          :Dict
        """
        # validity check
        self._validation(is_new=False)
        
        # query
        res = Alert.query.filter(Alert._uuid == self._uuid).first()

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
    
    def _validation(self, is_new=True):
        data = ins_to_dict(self)
             
        if is_new:
            for attr in ['title', 'msg', 'channel', 'tempo']:
                assert data[attr] is not None, 'attr %s is required' % attr
            
            assert isinstance(self._processed_at, numbers.Real) or self._processed_at is None, 'processed_at must be numeric or None'
        else:
            assert self._uuid is not None, 'alert uuid is immutable'
        
    ############################
    ###### Table Operations ####
    ############################   
    @classmethod 
    def export_table(cls):
        """Export task table to a DataFrame object

        Args:
          : None

        Returns:
          :DataFrame
        """

        conn = engine.connect()
        df = pd.read_sql_table(cls.__table__.name, con=conn)
        conn.close()
        return df
    # end def
    
    @classmethod
    def delete_table(cls, backup_filepath, chunksize=1000):
        """Delete a alert table

        Args:
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
        df = cls.export_table()
        if len(df) == 0:
            print('table is empty. not backing up.')
        else:
            df.to_excel(backup_filepath)
        # end if

        # Actually delete
        cls.__table__.drop(engine)
    # end def