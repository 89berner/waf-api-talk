from google.cloud        import pubsub
from google.cloud.pubsub import types
from google.cloud        import bigquery
import os

PROJECT_NAME      = os.environ['PROJECT_NAME']
SUB_NAME          = "waf-alerts-sub"
SUBSCRIPTION_NAME = 'projects/{project_id}/subscriptions/{sub}'.format(project_id=PROJECT_NAME,sub=SUB_NAME)
MAX_MESSAGES      = 10

subscriber = pubsub.SubscriberClient()

def pubsub_callback(message):
	print(message)

subscription_name = 'projects/{project_id}/subscriptions/{sub}'.format(
            project_id=PROJECT_NAME,sub=SUB_NAME)
flow_control = types.FlowControl(max_messages=MAX_MESSAGES)

print(SUBSCRIPTION_NAME)
future = subscriber.subscribe(SUBSCRIPTION_NAME,pubsub_callback, flow_control=flow_control)
result = future.result()
