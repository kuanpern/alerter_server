## Alerter server
A really simple server to receive alert message and put to database, or send to slack.

### Installation
```
$ git clone https://kuanpern@bitbucket.org/kuanpern/alerter_server.git
$ cd alerter_server
$ virtualenv -ppython3 venv; venv/bin/pip install requirements.txt
```

### Running the applications
Start the webserver with
```
usage: app.py [-h] [--host HOST] [--port PORT] [--debug DEBUG] --config CONFIG

Send alerts through emails

optional arguments:
  -h, --help       show this help message and exit
  --host HOST      server host name
  --port PORT      port number
  --debug DEBUG    debug mode
  --config CONFIG  path to configuration file (.yaml)
```

Run this with external scheduler (e.g. airflow)
```
usage: send_alerts_email.py [-h] --config CONFIG --tempo TEMPO

Send alerts through emails

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  path to configuration file (.yaml)
  --tempo TEMPO    tempo of the alert entries. Supports only "hourly" and
                   "daily"
```

#### Configurations
config file should be a yaml file like
```
conn_str: "mysql://admin:password@hostname:3306/alerts"
slack_token: "xoxp-a7cc5df4-47de-43a0-98c8-5f93587ba9fd69c4eda8-1288-423b-9db9-5b616965e3dc"
sendgrid_token: "SG.78a01d49-525d-43a9-8563-eb1be1d7c21b.ded61ffb.247d"
sender_email: admin@example.com
```

### Example
See tests/ for example of adding alert through python library and RESTful API calls.


### Database and schema

* main alert table
```
CREATE TABLE `alerts_backend` (
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
CREATE TABLE `alerts_backend_subscription` (
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
CREATE TABLE `alerts_backend_tokens` (
  `_uuid` varchar(40) NOT NULL,
  `token` text,
  `_created_at` double DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
```

## To use this as a python package
- in requirements.txt, add "-e git+git@github.com:kuanpern/alerter_server.git@dev_qq#egg=alerter"
- install

	$ venv/bin/pip3 install -r requirements.txt
	
- go to venv/src/alerter
	
	$cp .env.example .env
	$vi .env
	$# replace configurations
	
- usage
	
	from alerter import Alerter

	token='sola'
	title='Test'
	msg='test'
	channel='general'
	tempo='real-time'
	alerter = Alerter(token=token, title=title, msg=msg, channel=channel, tempo=tempo)
	print(alerter.send())