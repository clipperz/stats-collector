import tornado.web
import tornado.ioloop
import json
import os
import datetime
import base64
import requests		#   pip install requests

from tornado.options import define, options

define("port",  default=8888,			help="run on the given port", type=int)
define("users", default="./users.json", help="path to the file with enabled user credentials")

PROJECT_ID		= os.environ['PROJECT_ID']		if 'PROJECT_ID'		in os.environ else '__FAKE_PROJECT_ID__'
ACCESS_TOKEN	= os.environ['ACCESS_TOKEN']	if 'ACCESS_TOKEN'	in os.environ else '__FAKE_ACCESS_TOKEN__'

class Collector(tornado.web.RequestHandler):

	def initialize(self, enabledUsers):
		self.enabledUsers = enabledUsers


	def submitValuesToSplunkStorm(self, values, auth_key, ip):
		def appStats(label, data):
			status = data['status']
			result = "{label}Status={status}, {label}DownloadTime={downloadTime}, ".format(
				label = label,
				status = status,
				downloadTime = data['timing']
			)

			if status == 200:
				result += "{label}Signature={signature}, {label}Size={size}, ".format(
					label = label,
					signature = data['signature'],
					size = data['size']
				)
			return result

		def timingStats(data):
			if 'error' in data:
				result = "error=" + data['error']
			else:
				result = "knock={knock}, connect={connect}, credentialCheck={credentialCheck}, getUserDetails={getUserDetails}, totalTiming={totalTiming}, ".format(
					knock = data['knock'],
					connect = data['connect'],
					credentialCheck = data['credentialCheck'],
					getUserDetails = data['getUserDetails'],
					totalTiming = data['total']
				)
			return result

		log = "{timestamp}Z ip={ip}, user={user}, host={host}, authDescription=\"{authDescription}\", {app_info}{beta_info}{gamma_info}{delta_info}{timing}".format(
			timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat(),
			ip = ip,
			user = values['info']['user'],
			host = values['info']['host'],
			authDescription = self.enabledUsers[auth_key],
			app_info	= appStats('app', values['beta']),

			beta_info	= appStats('beta', values['beta']),
			gamma_info	= appStats('gamma', values['gamma']),
			delta_info	= appStats('delta', values['delta']),

			timing = timingStats(values['timing'])
		)
		print(log)

		params = { 'project':PROJECT_ID, 'host':auth_key, 'sourcetype':'collector', 'source':ip }
#		print("SENDING DATA: " + json.dumps(params, indent=4))
#		print("ACCESS_TOKEN: " + ACCESS_TOKEN)
		response = requests.post('https://api.splunkstorm.com/1/inputs/http', log, params=params, auth=('x', ACCESS_TOKEN), verify=False)
		if response.status_code != 200:
			raise Exception("problem saving data")


	def post(self):
		ip = self.request.headers.get('X-Forwarded-For') if 'X-Forwarded-For' in self.request.headers else self.request.headers.get('remote_addr')
		print("IP: " + ip)
		auth_hdr = self.request.headers.get('Authorization')
		if (auth_hdr == None) or (not auth_hdr.startswith('Basic ')):
			print("No authorization header found")
			return self.notAuthorized()

		auth_decoded = base64.decodestring(auth_hdr[6:])
		username, auth_key = auth_decoded.split(':', 2)
		print("Auth key: " + auth_key)
		if (username != 'x') or (not auth_key in self.enabledUsers):
			print("Auth key not found!")
			return self.notAuthorized()

		values = json.loads(self.request.body)
		self.submitValuesToSplunkStorm(values, auth_key, ip)
		self.write("Thanks")


	def notAuthorized(self):
		self.set_status(401)
		self.set_header('WWW-Authenticate','Basic realm="collector.stats.clipperz.is"')
		self.finish()

		return None


def main():
	tornado.options.parse_command_line()

	print("PROJECT ID: " + PROJECT_ID)
	print("ACCESS_TOKEN: " + ACCESS_TOKEN)

	application = tornado.web.Application([(r"/submit", Collector, dict(enabledUsers=json.load(open(options.users))))])
	application.listen(options.port)

	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()
