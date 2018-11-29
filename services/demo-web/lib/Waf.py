import requests
import time
import json
import logging
import redis
import traceback

WAF_ENDPOINT = "waf"

def waf_request_review(host, event, data, response_content):
    block = False
    waf_response = {}

    try:
        data = {
            "method":  event['method'], 
            "path":    event['full_path'], 
            "headers": event['headers'],
            "data":    data,
            "event":   event,
        }
        if (response_content != ""):
            data['content'] = response_content

        json_data = json.dumps(data)
        response = requests.post("http://%s:8080/process_request" % WAF_ENDPOINT, data = json_data).content
        logging.debug("WAF Response: %s" % response)
        try:
            waf_response = json.loads(response)
        except:
            logging.error("Error while trying to load response: %s" % response)
            logging.error(traceback.format_exc())
            return (block, {})

        if (waf_response['status'] == "Attack"):
            block = True
    except:
        logging.error("Error performing request to WAF: %s" % traceback.format_exc())

    return (block, waf_response)

def _check_waf_enabled(event, stage):
    r = redis.StrictRedis(host='redis', port=6379, db=0)

    total_key_name = "waf_enabled_stage_%s" % stage.lower()
    enabled_mode   = r.get(total_key_name)
    logging.info("Checking if key %s exists" % total_key_name)

    if (enabled_mode == "full"):
        return (True, enabled_mode)
    elif (enabled_mode == "identifier"):
        # check for partially enabled for the ip address
        for identifier in ("login_id", "ip", "user-agent"):
            if identifier in event:
                key_name = "waf_enabled#%s#%s" % (identifier.lower(), event[identifier].lower())
                logging.info("Checking if key %s exists" % key_name)
                exists = r.get(key_name)
                if (exists != None):
                    return (True, enabled_mode)

    logging.info("Checking virtual patching for an endpoint")
    vp_key = "waf_virtual_patching_enabled#%s" % event["endpoint"]
    endpoint_virtually_patched = r.get(vp_key)
    if (endpoint_virtually_patched != None):
        logging.info("Virtual patch enabled for endpoint: %s" % event["endpoint"])
        return (True, "virtual_patching")

    logging.info("Checking for Proxy routing")
    proxy_routing_key = "waf_proxy_rounting_enabled"
    proxy_routing_enabled = r.get(proxy_routing_key)

    if (proxy_routing_enabled != None and event['geo.src'] == "A1"):
        logging.info("Proxy routing enabled")
        return (True, "proxy_routing")

    logging.info("No need for WAF at stage %s according to redis" % stage)
    return (False, None)
    # this should check against redis if the waf appears as enabled for some different identifiers
    # endpoint, IP address, user, IP range, user agent

def perform_waf_check(event, stage, request_data, response = ""):

    if (stage not in ['REQUEST', 'RESPONSE']):
        raise("Unknown WAF stage: %s" % stage)

    (waf_enabled, mode) = _check_waf_enabled(event, stage)
    logging.info("[perform_waf_check] waf_enabled for stage %s is %s" % (stage, waf_enabled))
    if (waf_enabled is True):
        # waf content inspection if it was not blocked previously

        start_waf = time.time()
        (block, waf_response) = waf_request_review("localhost", event, request_data, response)
        event["waf_%s_answer" % stage.lower()] = waf_response
        event['waf_status'] = waf_response["status"]
        end_waf   = time.time()
        logging.debug("Time elapsed on %s review: %f" % (stage, (end_waf - start_waf) ) )
        event["waf_%s_time_spent" % stage.lower()] = end_waf - start_waf

        event['waf_mode'] = mode
        event['performed_waf_review'] = stage;
        if (block is True):
            event['waf_block'] = stage
            if (response != ""):
                event['request_blocked_response'] = response
            return "BLOCKED"

    return None