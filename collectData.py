#!/usr/bin/python

import sys
import hashlib
import time
import json
import os
import binascii
import datetime
import requests		#   pip install requests

from requests import Request, Session

AUTH_KEY = os.environ['AUTH_KEY']
USERNAME = os.environ['USERNAME']
PASSPHRASE = os.environ['PASSPHRASE']
URL = os.environ['URL']

def md5(content):
	hash = hashlib.md5()
	hash.update(content)
	result = bytearray(hash.digest())

	return result

def sha256(content):
	hash = hashlib.sha256()
	hash.update(content)
	result = bytearray(hash.digest())

	return result

def shaD256(content):
	return sha256(sha256(content))

def hash(content):
	return shaD256(content)

def stringHash(value):
	return binascii.hexlify(hash(value))


def dataToInt(data):
	return int(binascii.hexlify(data), 16)

def intToHex(value):
	return hex(value).rstrip("L").lstrip("0x")

def downloadApp(session, label, url):
	sys.stdout.write('Downloading application version {}'.format(label))
	request = Request('GET', url)
	preparedRequest = session.prepare_request(request)
	preparedRequest.headers['Accept'] = 'text/html'
	preparedRequest.headers['Accept-Encoding'] = 'gzip,deflate,sdch'

	# SNI will never be supported in Python 2 series: http://stackoverflow.com/questions/18578439/using-requests-with-tls-doesnt-give-sni-support#comment30104870_18579484
	start = time.time()
	response = session.send(preparedRequest, verify=False)
	loadTime = time.time() - start

	result = {
		'url':			url,
		'status':		response.status_code,
		'etag':			response.headers['etag'],
		'lastModified':	response.headers['last-modified'],
		'timing':		loadTime,
	}

	if response.status_code == 200:
#		result['content'] =	response.headers['content-encoding'],
		result['size'] = len(response.content)
		result['signature'] = binascii.hexlify(md5(response.content))
		print(' -> signature: {} - size: {}'.format(result['signature'], str(result['size'])))
	else:
		print(" error: " + response.status_code)

	return result


def payToll(toll):

	def prefixMatchingBits(value, target):
		result = 0
		c = min(len(value), len(target))
		i = 0
		while (i < c) and (value[i] == target[i]):
			result += 8
			i += 1

		if (i < c):
			xorValue = value[i] ^ target[i]
			if xorValue >= 64:
				result += 1
			elif xorValue >= 32:
				result += 2
			elif xorValue >= 16:
				result += 3
			elif xorValue >= 8:
				result += 4
			elif xorValue >= 4:
				result += 5
			elif xorValue >= 2:
				result += 6
			elif xorValue >= 1:
				result += 7

		return result

	def increment(value):
		i = len(value) - 1
		done = False

		while (i >= 0) and (done == False):
			currentValue = value[i]

			if currentValue == 0xff:
				value[i] = 0x00
				if i >= 0:
					i -= 1
				else:
					done = True
			else:
				value[i] = currentValue + 1
				done = True

		return value

	cost = toll['cost']
	target = bytearray(toll['targetValue'].decode("hex"))

	payment = bytearray(os.urandom(32))

	while True:
		if prefixMatchingBits(sha256(payment), target) > cost:
			break
		else:
			payment = increment(payment)

	result = binascii.hexlify(payment)
	return result

def postPayload(session, url, payload):
	start = time.time()
	request = Request('POST', url, data=payload)
	preparedRequest = session.prepare_request(request)
	response = session.send(preparedRequest, verify=False)
	timing = time.time() - start
	result = response.json()

	return timing, result


def knock(session, url):
	payload = {
		'method': 'knock',
		'version': 'fake-app-version',
		'parameters': json.dumps({
			'requestType': 'CONNECT'
		})
	}
	timing, result = postPayload(session, url, payload)
	toll = result['toll']

	return timing, toll


def handshake_connect(session, url, C, A, toll, payment):
	payload = {
		'method': 'handshake',
		'version': 'fake-app-version',
		'parameters': json.dumps({
			"parameters": {
				"message": "connect",
				"version": "0.2",
				"parameters": {
					"C": C,
					"A": A
				}
			},
			"toll": {
				"targetValue": toll['targetValue'],
				"toll": payment
			}
		})
	}

	timing, result = postPayload(session, url, payload)
	toll = result['toll']
	challenge = result['result']

	return timing, challenge, toll


def handshake_credentialCheck(session, url, M1, toll, payment):
	payload = {
		'method': 'handshake',
		'version': 'fake-app-version',
		'parameters': json.dumps({
			"parameters": {
				"message": "credentialCheck",
				"version": "0.2",
				"parameters": {
					"M1": M1
				}
			},
			"toll": {
				"targetValue": toll['targetValue'],
				"toll": payment
			}
		})
	}

	timing, result = postPayload(session, url, payload)
	toll = result['toll']
	info = result['result']

	return timing, info, toll


def message_getUserDetails(session, url, sharedSecret, toll, payment):
	payload = {
		'method': 'message',
		'version': 'fake-app-version',
		'parameters': json.dumps({
			"parameters": {
				"message": "getUserDetails",
				"srpSharedSecret": sharedSecret,
				"parameters": {}
			},
			"toll": {
				"targetValue": toll['targetValue'],
				"toll": payment
			}
		})
	}

	timing, result = postPayload(session, url, payload)
	toll = result['toll']
	details = result['result']

	return timing, details, toll


def doLogin(session, url, username, passphrase):
	sys.stdout.write("Doing login ...")
	try:
		start = time.time()
		g = 2
		n = int('115b8b692e0e045692cf280b436735c77a5a9e8a9e7ed56c965f87db5b2a2ece3', 16)

		knockTiming, toll = knock(session, url)

		C = stringHash(username + passphrase)
		p = stringHash(passphrase + username)
		a = dataToInt(bytearray(os.urandom(32)))
		A = pow(g, a, n)
		connectTiming, challenge, toll = handshake_connect(session, url, C, intToHex(A), toll, payToll(toll))

		B = int(challenge['B'], 16)
		s = challenge['s']
		u = dataToInt(hash(str(B)))
		x = dataToInt(hash(('0000000000000000000000000000000000000000000000000000000000000000' + s)[-64:] + p))
		S = pow((B - pow(g, x, n)), (a + u * x), n)
		K = stringHash(str(S))
		M1 = stringHash(str(A) + str(B) + K)
		credentialCheckTiming, info, toll = handshake_credentialCheck(session, url, M1, toll, payToll(toll))

		sharedSecret = K
		getUserDetailsTiming, details, toll = message_getUserDetails(session, url, sharedSecret, toll, payToll(toll))

		result = {
			'knock':			knockTiming,
			'connect':			connectTiming,
			'credentialCheck':	credentialCheckTiming,
			'getUserDetails':	getUserDetailsTiming,
			'total':			time.time() - start
		}
	except Exception as exception:
		result = {
			'error': str(exception)
		}
	print(" done")
	return result, C


#def collectCurrentLocationInfo():
#	return {
#		'timestamp': datetime.datetime.utcnow().isoformat(),
#		'ip': requests.get('http://ifconfig.me/ip').text.rstrip().encode("ascii")
#	}

def main (baseUrl, username, passphrase):
	session = Session()

	betaInfo =	downloadApp(session, 'beta',  baseUrl + '/beta')
	gammaInfo =	downloadApp(session, 'gamma', baseUrl + '/gamma')
	deltaInfo =	downloadApp(session, 'delta', baseUrl + '/delta')

	connectInfo, C = doLogin(session, baseUrl + '/json', username, passphrase)

#	currentLocationInfo = collectCurrentLocationInfo()

	result = {
		'info': {
			'user': C
		},

		'beta':  betaInfo,
		'gamma': gammaInfo,
		'delta': deltaInfo,

		'timing': connectInfo
#		'info': currentLocationInfo
	}

	data = json.dumps(result)
	print("Collected data:\n" + json.dumps(result, indent=4))

#!	response = requests.post('http://collector.stats.clipperz.is/submit', data, auth=('x', AUTH_KEY))
#	response = requests.post('http://localhost:8888/submit/0.1', data, auth=('x', AUTH_KEY))
#	if response.status_code != 200:
#		raise Exception("failed to submit data")


if __name__ == "__main__":
	main(URL, USERNAME, PASSPHRASE)

