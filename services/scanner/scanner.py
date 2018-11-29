#!/usr/bin/python

import requests
import time
import traceback
import random
import subprocess

sleep_factor = int(random.random()*10) + 1
while(True):
	try:
		print("Performing a typical sql injection request..")
		# set our header
		headers = {'user-agent': 'scanner-1/0.0.1'}
		r = requests.get('http://demo-web:80/?param1=SELECT * FROM INFORMATION_SCHEMA', headers=headers)
		print(r.content)
		print("Performing content request...")
		headers = {'user-agent': 'scanner-2/0.0.1'}
		r = requests.get('http://demo-web:80/vulnerable_content', headers=headers)
		print(r.content)
		print("Running Sqlmap")
		subprocess.call('timeout 3600 sqlmap --level=5 --risk=3 -u http://demo-web/?id=1 --batch --user-agent=NotSequelMap --delay=2', shell=True)
		print("Finished running Sqlmap")
		# print("Running Nikto")
		# subprocess.call('timeout 3600 nikto -host "http://demo-web/ -Pause 2"', shell=True)
		# print("Finished running Nikto")
		# print("Running Skipfish")
		# subprocess.call('echo "A" | skipfish -e -o /tmp/results "http://demo-web/" -l 1', shell=True)
		# print("Finished running Skipfish")
	except:
		print("Error trying to run scanner: %s" % traceback.format_exc())
	time.sleep(60*10*sleep_factor)