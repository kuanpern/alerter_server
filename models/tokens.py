import uuid
import json
import time
import pandas as pd
import copy
import sqlalchemy
import numbers
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, REAL, String, Boolean
from database import Base, engine
from database import db_session as session

class Tokens(Base):
    TABLE_NAME = 'tokens'
    
    __tablename__ = TABLE_NAME
    
    tables = engine.table_names()
    if TABLE_NAME not in tables:
        __table_args__ = {'extend_existing': True}

    # Schema definition
    _uuid = Column(String(40), primary_key=True)
    token = Column(Text)
    _created_at = Column(REAL, default=None)
    status = Column(String(20), default=None)