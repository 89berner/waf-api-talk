#!/usr/bin/python2

import redis
import argparse
import time
import datetime
import operator
from prettytable import PrettyTable

def _print_help_commands():
	print("Example commands:")
	print("python manage.py --add-virtual-patching-endpoint=ping")
	print("python manage.py --configure-request-stage=1 --mode=identifier # enable request stage only for created identifiers")
	print("python manage.py --configure-response-stage=1 --mode=identifier # disable response stage")
	print("python manage.py --add-identifier=1 --identifier=ip  --identifier-value=10.60.1.72")
	print("python manage.py --add-block-rule=1 --identifier=user-agent --identifier-value=NotSequelMap")
	print("python manage.py --delete-block-rule=1 --identifier=ip --identifier-value=127.0.0.2")

def _build_parser():
	parser = argparse.ArgumentParser()
	# Enable / disable waf stages and modes
	parser.add_argument('--configure-request-stage',  type=int, help='Enable WAF checks on Request stage. Needs to specify either --identifier option or --full option')
	parser.add_argument('--configure-response-stage', type=int, help='Enable WAF checks on Response stage. Needs to specify either --identifier option or --full option')
	parser.add_argument('--mode',                  type=str, help='Selects WAF mode. Options are full | identifier | disabled')
	# Add identifiers for identifier mode
	parser.add_argument('--add-identifier',         type=str, help='Add identifier for identifier mode. Needs --identifier and --identifier_value options set')
	parser.add_argument('--delete-identifier',      type=str, help='Delete identifier. Needs --identifier and --identifier_value options set')
	parser.add_argument('--delete-all-identifiers', type=str, help='Delete all identifiers')
	parser.add_argument('--identifier',             type=str, help='Enable WAF for a particular identifier type. Needs the --value option to be set')
	parser.add_argument('--identifier-value',       type=str, help='Value that will go through the WAF. Needs an --identifier option to be set')
	parser.add_argument('--ttl',                    type=int, help='TTL for the identifier. Defaults to 1 day.' , default=60*60*24)
	# Create block rules
	parser.add_argument('--add-block-rule',    type=str, help='Add a block rule. Needs --identifier and --identifier_value to be set')
	parser.add_argument('--delete-block-rule', type=str, help='Delete a block rule. Needs --identifier and --identifier_value to be set')
	# Virtual Patching
	parser.add_argument('--add-virtual-patching-endpoint', type=str, help='Name of the endpoint to apply virtual patching')
	parser.add_argument('--remove-virtual-patching-endpoint', type=str, help='Name of the endpoint to remove from virtual patching')
	# Proxy Routing
	parser.add_argument('--enable-proxy-routing',  type=str, help='Enable proxy routing')
	parser.add_argument('--disable-proxy-routing', type=str, help='Disable proxy routing')
	# Manage scoring
	parser.add_argument('--set-score', type=int, help='Set score for triggering blocking')
	# Manage alerts
	parser.add_argument('--delete-alert-locks', type=int, help='Delete all locks for alerting')
	# Helpers
	parser.add_argument('--show-config', type=str, help='Show the configuration status')
	parser.add_argument('--show-keys', type=str, help='Show the configuration status')
	parser.add_argument('--show-help',   type=str, help='Show help commands')
	args = parser.parse_args()

	return args

def _configure_stage(stage, mode):
	print("Selected %s stage" % stage)
	if (args.mode == "full"):
		print("Configured full mode for stage %s" % stage)
		r.set("waf_enabled_stage_%s" % stage, "full")
	elif (args.mode == "identifier"):
		print("Configured identifier mode for stage %s" % stage)
		r.set("waf_enabled_stage_%s" % stage, "identifier")
	elif (args.mode == "disabled"):
		print("Will disable the %s stage" % stage)
		r.set("waf_enabled_stage_%s" % stage, "disabled")
	else:
		print("You must select a mode: full | identifier | disabled")

args = _build_parser()
r = redis.StrictRedis(host='redis', port=6379, db=0)

formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if args.configure_request_stage:
	_configure_stage("request", args.mode)
elif args.configure_response_stage:
	_configure_stage("response", args.mode)
# Identifiers
elif args.add_identifier:
	if args.identifier is None or args.identifier_value is None:
		print("Identifier and value must be set")
	else:
		r.set("waf_enabled#%s#%s" % (args.identifier.lower(), args.identifier_value.lower()), "%s#manage_script" % formatted_time, ex=args.ttl)
		print("Identifier %s has been set for value %s" % (args.identifier.lower(), args.identifier_value.lower()))
elif args.delete_identifier:
	if args.identifier is None or args.identifier_value is None:
		print("Identifier and value must be set")
	else:
		r.delete("waf_enabled#%s#%s" % (args.identifier, args.identifier_value))
		print("Identifier %s has been deleted for value %s" % (args.identifier, args.identifier_value))
elif args.delete_all_identifiers:
	for key in r.scan_iter("waf_enabled#*"):
		r.delete(key)
		print("Removing key %s" % key)
# Blockrule
elif args.add_block_rule:
	if args.identifier is None or args.identifier_value is None:
		print("Identifier and value must be set")
	else:
		r.set("waf_block_rule#%s#%s" % (args.identifier.lower(), args.identifier_value.lower()), "%s#manage_script" % formatted_time, ex=args.ttl)
		print("Block Rule: Identifier %s has been set for value %s" % (args.identifier, args.identifier_value))
elif args.delete_block_rule:
	if args.identifier is None or args.identifier_value is None:
		print("Identifier and value must be set")
	else:
		r.delete("waf_block_rule#%s#%s" % (args.identifier, args.identifier_value))
		print("Block Rule: Identifier %s has been deleted for value %s" % (args.identifier, args.identifier_value))
# Virtual patching
elif args.add_virtual_patching_endpoint:
	print("Virtual patching: Adding endpoint %s" % args.add_virtual_patching_endpoint)
	r.set("waf_virtual_patching_enabled#%s" % args.add_virtual_patching_endpoint, formatted_time)
elif args.remove_virtual_patching_endpoint:
	print("Virtual patching: Removing endpoint %s" % args.remove_virtual_patching_endpoint)
	r.delete("waf_virtual_patching_enabled#%s" % args.remove_virtual_patching_endpoint)
# Proxy Routing
elif args.enable_proxy_routing:
	print("Enabling proxy routing")
	r.set("waf_proxy_rounting_enabled", formatted_time)
elif args.disable_proxy_routing:
	print("Disabling proxy routing")
	r.delete("waf_proxy_rounting_enabled")
# Set scoring
elif args.set_score:
	print("Setting score to %d" % args.set_score)
	r.set("waf_trigger_score", args.set_score)
# Delete alert locks
elif args.delete_alert_locks:
	print("Deleting alert locks..")
	for key in r.scan_iter("waf_alert_sent*"):
		r.delete(key)
		print("Deleted key %s" % key)
# Helpers
elif args.show_config:
	print("=" * 75)
	print("WAF Configuration")
	# Request
	t = PrettyTable(['Config', 'Status'])
	request_stage = r.get("waf_enabled_stage_request")
	if (request_stage is None):
		request_stage = "disabled"
	#print ("Request stage: %s" % request_stage)
	t.add_row(['Request Stage', request_stage])
	# Response
	response_stage = r.get("waf_enabled_stage_response")
	if (response_stage is None):
		response_stage = "disabled"
	#print ("Response stage: %s" % response_stage)
	t.add_row(['Response Stage', response_stage])

	waf_proxy_rounting_enabled = r.get("waf_proxy_rounting_enabled")
	if (waf_proxy_rounting_enabled is None):
		response_stage = "disabled"
	else:
		waf_proxy_rounting_enabled = "enabled"
	t.add_row(['Waf Proxy Routing', response_stage])

	score = r.get("waf_trigger_score")
	if (score is None):
		score = 5
	t.add_row(['Scoring threshold', score])
	print(t)

	# Identifiers configured
	print("=" * 75)
	print("WAF Identifier based routing:")
	#print("=" * 50)
	t = PrettyTable(['Identifier', 'Value', 'Added at', 'Created by'])
	has_identifiers = False
	for key in r.scan_iter("waf_enabled#*"):
		has_identifiers = True
		# parse identifier
		identifier       = key.split("#")[1]
		identifier_value = key.split("#")[2]
		data             = r.get(key).split("#")
		formatted_time   = data[0]
		created_by       = data[1]

		t.add_row([identifier, identifier_value, formatted_time, created_by])

	if (has_identifiers is True):
		print(t.get_string(sortby="Added at"))
	else:
		print("No identifier has been configured.")

	# Virtual Patching
	print("=" * 75)
	print("Virtual patching routing:")
	t = PrettyTable(['Endpoint', 'Added at'])
	has_endpoints = False
	for key in r.scan_iter("waf_virtual_patching_enabled*"):
		has_endpoints = True
		endpoint = key.split("#")[1]
		added_at = r.get(key)
		t.add_row([endpoint, added_at])

	if (has_endpoints is True):
		print(t.get_string(sortby="Added at"))
	else:
		print("No endpoints has been configured for virtual patching.")

	# Block Rules
	print("=" * 75)
	print("Block Rules Configured:")
	#print("=" * 50)
	t = PrettyTable(['Identifier', 'Value', 'Added at', 'Created by'])
	has_blockrule = False
	for key in r.scan_iter("waf_block_rule#*"):
		has_blockrule = True
		# parse block rule
		identifier       = key.split("#")[1]
		identifier_value = key.split("#")[2]
		data             = r.get(key).split("#")
		formatted_time   = data[0]
		created_by       = data[1]

		t.add_row([identifier, identifier_value, formatted_time, created_by])

	if (has_blockrule is True):
		print(t.get_string(sortby="Added at"))
	else:
		print("No BlockRule has been configured.")

	# Rate limit
	print("=" * 75)
	print("Rate limit counters:")
	#print("=" * 50)
	t = PrettyTable(['Time Bucket', 'Identifier', 'Value', 'Counter', 'TTL'])
	for key in r.scan_iter("waf_rate_limiter#*"):
		# parse block rule
		identifier       = key.split("#")[1]
		identifier_value = key.split("#")[2]
		epoch            = key.split("#")[3]
		ttl              = r.ttl(key)
		counter          = r.get(key)
		date             = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(epoch)))
		#print("[%s] %s(%s) => %s" % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(epoch))), identifier_value, identifier, r.get(key) ) )
		t.add_row([date, identifier, identifier_value, counter, ttl])
	print(t.get_string(sort_key=operator.itemgetter(1, 0), sortby="Identifier"))

		#print("%s => %s" % (key, r.get(key)))
elif args.show_keys:
	print("Showing status of the waf configuration:\n")
	for key in r.scan_iter("*"):
		print("%s => %s" % (key, r.get(key)))

elif args.show_help:
	_print_help_commands()
else:
	print("You need to provide an option, use ./manage.py -h for more information")
