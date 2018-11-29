import json
import logging
import time
import traceback
import os
import datetime
import redis
from IPy    import IP
from pprint import pprint

from google.cloud        import pubsub
from google.cloud.pubsub import types
from google.cloud        import bigquery

PROJECT_NAME      = os.environ['PROJECT_NAME']
SUB_NAME          = "waf-alerts-sub"
SUBSCRIPTION_NAME = 'projects/{project_id}/subscriptions/{sub}'.format(project_id=PROJECT_NAME,sub=SUB_NAME)
MAX_MESSAGES      = 10

subscriber = pubsub.SubscriberClient()
bqclient   = bigquery.Client(project=PROJECT_NAME)

def pubsub_callback(message):
    try:
        logging.info("Message received: %s" % message)

        message_data = json.loads(message.data)
        identifier_type  = message_data['key']
        identifier_value = message_data['value']

        logging.info("Received identifier_type: %s identifier_value:%s" % (identifier_type, identifier_value) )

        # validate ip address
        if (identifier_type == "ip"):
            # validate ip address
            valid_ip = IP(identifier_value)

            # fake sleeping
            time.sleep(1)

            r = redis.StrictRedis(host='redis', port=6379, db=0)

            score_needed = r.get("waf_trigger_score")
            if (score_needed is None):
                score_needed = 5
            else:
                score_needed = int(score_needed)
            
            try:
                QUERY = (
                    "select DATE(TIMESTAMP_SECONDS(CAST(epoch AS INT64))) as date, JSON_EXTRACT(raw_data, '$.url') as url, count(*) as amount "
                    "FROM `raw_dataset.raw_data` WHERE JSON_EXTRACT(raw_data, '$.ip')='" + '"' + identifier_value + '"' + "' GROUP BY date,url"
                    )
                query_job = bqclient.query(QUERY)  # API request
                logging.info("Running query: %s" % QUERY)
                rows = query_job.result()

                good_score = 0
                for row in rows:
                    logging.info("%s|%s|%s" % (row.date, row.url, row.amount))
                    if (row == '"http://demo-web/good_endpoint"'):
                        good_score += 1

                if (good_score > 1): # more than one day
                    logging.info("We could double the score needed due to good behaviour from IP in the past")
            except:
                logging.error("Error trying to query bigquery: %s" % traceback.format_exc())

            logging.info("Alert score %d was reached" % score_needed)
            added_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            r.set("waf_enabled#%s#%s" % (identifier_type.lower(), identifier_value.lower()), "%s#alerter_script" % added_time, ex=60*60*6)
        else:
            logging.error("Identifier type not supported: %s" % identifier_type)

        message.ack()
    except:
        logging.error("Error processing callback: %s" % traceback.format_exc())
        message.nack()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Starting alerter...")
    while(True):
        print("Will request a pubsub item")

        subscription_name = 'projects/{project_id}/subscriptions/{sub}'.format(
            project_id=PROJECT_NAME,sub=SUB_NAME)
        flow_control = types.FlowControl(max_messages=MAX_MESSAGES)

        future = subscriber.subscribe(SUBSCRIPTION_NAME,pubsub_callback, flow_control=flow_control)
        result = future.result()
        print("Worker finished processing pubsub")
        time.sleep(1)