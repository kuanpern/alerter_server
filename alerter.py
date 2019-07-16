import time
import uuid
import json
import os
from utils import ins_to_dict
import opends.easy_messaging
from multiprocessing import Process
from models.alert import Alert
from models.tokens import Tokens
# logging
import logging
logger = logging.getLogger()
# load env
from dotenv import load_dotenv
load_dotenv()

class Alerter:
    def __init__(self, token):
        self.token = token
        
        # validation
        self._validate()
    
    def send(self, title, msg, channel, tempo='daily'):
        self.title = title
        self.msg = msg
        self.channel = channel
        self.tempo = tempo
        
        _uuid = str(uuid.uuid4())
        self.alert_uuid = _uuid
        self.tblname = Alert.__table__.name
        content = ins_to_dict(self)
        
        if self.tempo == 'real-time':
            p = Process(target=send_msg, args=(content,))
        else:
            p = Process(target=put_db  , args=(content,))
        # end if
        p.start()
    
        return json.dumps({'uuid': _uuid})
        
    def _validate(self):
        # validate token
        exist = Tokens.query.filter(Tokens.token == self.token, Tokens.status == 'active').count() > 0
        assert exist, 'Authentication failed'
        # end if
  
def put_db(inputs):
    acceptables = ['title', 'msg', 'channel', 'tempo', 'alert_uuid', 'is_processed', 'processed_at']
    pops = set(inputs.keys()) - set(acceptables)
    for key in pops:
        inputs.pop(key)
    # end for
    alert = Alert(**inputs)
    alert.add()
# end def

def send_msg(inputs):
    tblname = inputs['tblname']
    title   = inputs['title']
    msg     = inputs['msg']
    channel = inputs['channel']        # ds, general, random

    text = '[{tblname}] | [{title}]\n{msg}'.format(tblname=tblname, title=title, msg=msg)
    response = opends.easy_messaging.send_slack_message(
        channel   = channel,
        text      = text, 
        token     = os.getenv('SLACK_TOKEN'), 
        from_user = 'bot'
    ) # end message

    # still register to DB
    inputs['is_processed'] = True
    inputs['processed_at'] = time.time()
    put_db(inputs)
# end def

if __name__ == '__main__':
    token='sola'
    title='Test'
    msg='test'
    channel='general'
    tempo='real-time' # daily, hourly
    alerter = Alerter(token=token)
    print(alerter.send(title=title, msg=msg, channel=channel, tempo=tempo))