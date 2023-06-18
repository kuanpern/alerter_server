## Alerter server
A really simple server to register alert message; send hourly/daily email to user, or send real-time message to slack.

Note (2023-06-18): This repository is not maintained anymore. One should use better supported system (e.g. [Sentry](https://develop.sentry.dev/self-hosted/)) for this use case.


### Installation (Server side)
```
$ sudo apt-get install virtualenv python-mysqldb python3-dev libmysqlclient-dev gcc
$ git clone https://github.com/kuanpern/alerter_server.git
$ cd alerter_server
$ virtualenv -ppython3 venv; venv/bin/pip install .
```

### Running the applications
set config file location (see configs/example_configs.yaml for an example)
```
$ export ALERTER_CONFIG_FILE=/home/ubuntu/.keys/alerter_configs.yaml
```
then start the webserver
```
$ venv/bin/python alerter_server/webserver/alerter_webserver.py
```
see alerter_server/webserver/alerter_webserver.service (and relevant config file) for deployment with gunicorn and daemonization with systemd.

#### Configurations
config file should be a yaml file like
```
db_conn_str : "mysql://admin:password@hostname:3306/alerts"
slack_token : "xoxp-a7cc5df4-47de-43a0-98c8-5f93587ba9fd69c4eda8-1288-423b-9db9-5b616965e3dc"
timezone    : Asia/Singapore
email_provider : sendgrid
email_api_key  : "SG.78a01d49-525d-43a9-8563-eb1be1d7c21b.ded61ffb.247d3b7af0c75d34"
sender_email   : admin@example.com
```

### Setup an alert center

```
from alerter_server.utils import alertController, tokenController, subscriptionController

# assume a SQL database endpoint has been setup
conn_str = 'mysql://admin:password@hostname:3306/alerts'

# setup an alert table
alert_controller = alertController(conn_str)
alert_controller.init_alerttable(name='test', prefix='alerts_')

# setup a token table
token_controller = tokenController(conn_str)
token_controller.init_tokentable(name='test', suffix='_tokens', prefix='alerts_')

# setup a subscription table
subs_controller = subscriptionController(conn_str)
subs_controller.init_subscriptiontable(name='test', prefix='alerts_', suffix='_subscription')


# issue a new token
token_controller.set_tokentable('alerts_test_tokens')
token = token_controller.issue_new_token()
print(token) # <- send this to subscriber(s)

# register a new subscriber
subs_controller.set_subscriptiontable('alerts_test_subscription')
subs_controller.add_subscription(
    username = 'kuanpern',
    email    = 'kptan86@gmail.com',
    channel  = 'generalalerts',
) # end alert
```


### Quick start and example (Client side)
To use the package as a library, install with
```
pip install -e git+https://github.com/kuanpern/alerter_server.git#egg=alerter_server
```

To register an alert to the webserver, simply do
```
from alerter_server.utils import Alerter

alerter = Alerter(
    endpoint='http://localhost:8080/alerts_test', 
    token   ='b76326d5-b3ed-4350-b531-9c26308c6487'
) # end alerter

r = alerter.register(
    msg     = 'This is a test message from usage testing', 
    tempo   = 'hourly', 
    channel = 'datascience', 
    title   = 'algo01'
) # end alerter
```


See tests/ for more examples of adding alerts through python libraries and RESTful API calls.


### Database and schema

* main alert table
```
CREATE TABLE `alerts_test` (
  `_uuid` varchar(40) NOT NULL,
  `title` text,
  `msg` text,
  `channel` text,
  `_updated_at` double NOT NULL,
  `_IsProcessed` tinyint(1) NOT NULL,
  `_processed_at` double NOT NULL,
  `tempo` varchar(12) DEFAULT NULL,
  PRIMARY KEY (`_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
```

* subscription table
```
CREATE TABLE `alerts_test_subscription` (
  `_uuid` varchar(40) NOT NULL,
  `username` text,
  `_created_at` double DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `email` varchar(320) DEFAULT NULL,
  `channel` text,
  PRIMARY KEY (`_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
```

* tokens table
```
CREATE TABLE `alerts_test_tokens` (
  `_uuid` varchar(40) NOT NULL,
  `token` text,
  `_created_at` double DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
```


### ROADMAP
* use sqlalchemy rather than plain sql
* fix naming convention and autostart project
