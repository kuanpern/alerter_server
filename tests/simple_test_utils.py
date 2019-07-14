import utils
import uuid

conn_str = 'mysql://admin:password@hostname:3306/alerts'

controller = utils.Controller(conn_str)

controller.list_alerttables()

controller.init_alerttable(name='backend', prefix='alerts_')

controller.list_alerttables()

print(controller.alerttable)

controller.add_alert(
    title = 'test',
    msg = 'this is a test',
    channel = 'generalalerts',
    alert_uuid = str(uuid.uuid4()),
) # end alert

controller.list_alerts()



