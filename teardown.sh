#!/bin/bash

PROJECT_NAME=$1

if [ -z "$PROJECT_NAME" ]; then
	echo "You must pass a project name";
	exit 1;
fi

echo "Selecting project $PROJECT_NAME.."
gcloud config set project $PROJECT_NAME

echo "Deleting temporary files.."
rm -rf tmp/
rm credentials/*

echo "Cancelling Dataflow job"
gcloud dataflow jobs cancel $(gcloud dataflow jobs list|grep Running|cut -d ' ' -f1) --region=europe-west4

echo "Destroying Terraform Configuration"
terraform destroy -auto-approve -var "project_name=$PROJECT_NAME"

gcloud projects remove-iam-policy-binding $PROJECT_NAME --member serviceAccount:logstashsub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.subscriber
echo "Y"|gcloud iam service-accounts delete logstashsub@$PROJECT_NAME.iam.gserviceaccount.com

gcloud projects remove-iam-policy-binding $PROJECT_NAME --member serviceAccount:pubsubpublisher@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.publisher
echo "Y"|gcloud iam service-accounts delete pubsubpublisher@$PROJECT_NAME.iam.gserviceaccount.com

gcloud projects remove-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.subscriber
gcloud projects remove-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/bigquery.dataViewer
gcloud projects remove-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/bigquery.jobUser
echo "Y"|gcloud iam service-accounts delete alertersub@$PROJECT_NAME.iam.gserviceaccount.com

echo "Y"|gcloud compute addresses delete redis-ip
echo "Y"|gcloud compute addresses delete waf-ip  

echo "Deleting BigQuery dataset"
bq rm -r -f -d $PROJECT_NAME:raw_dataset 2>/dev/null

# echo "Deleting alerts pub/sub topic just in case terraform failed to do so"
# gcloud pubsub topics delete alerts 2>/dev/null
# gcloud pubsub subscriptions delete alerts-sub 2>/dev/null

# echo "Deleting enriched_events pub/sub topic just in case terraform failed to do so"
# gcloud pubsub topics delete enriched_events 2>/dev/null
# gcloud pubsub subscriptions delete logstash-sub 2>/dev/null

# echo "Deleting raw_events pub/sub topic just in case terraform failed to do so"
# gcloud pubsub topics delete raw_events 2>/dev/null
# gcloud pubsub subscriptions delete beam-sub 2>/dev/null

# echo "Deleting waf_alerts pub/sub topic just in case terraform failed to do so"
# gcloud pubsub topics delete waf_alerts 2>/dev/null
# gcloud pubsub subscriptions delete waf-alerts-sub 2>/dev/null
