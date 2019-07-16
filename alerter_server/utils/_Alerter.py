import requests

class Alerter:
	def __init__(self, endpoint, token):
		self.endpoint = endpoint
		self._token   = token
	# end def

	def register(self, channel, title, msg, tempo='hourly'):
		inputs = {
			'token'  : self._token,
			'title'  : title,
			'msg'    : msg,
			'channel': channel,
			'tempo'  : tempo,
		}
		res = requests.post(self.endpoint, json=inputs)
		return res
	# end def
# end class
