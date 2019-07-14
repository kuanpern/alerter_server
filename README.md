## Alerter server
A really simple server to receive alert message and put to database, or send to slack.

### Installation
```
$ git clone https://kuanpern@bitbucket.org/kuanpern/alerter_server.git
$ cd alerter_server
$ virtualenv -ppython3 venv; venv/bin/pip install requirements.txt
```

### Running the application
Start the webserver with
```
usage: app.py [-h] --config CONFIG

Send alerts through emails

optional arguments:
  -h, --help       show this help message and exit
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
