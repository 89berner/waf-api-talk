#!/bin/bash

PROJECT_NAME=$1

if [ -z "$PROJECT_NAME" ]; then
	echo "You must pass as an argument a GCP project name";
	exit 1;
fi

echo "Starting setup at $(date)"
echo "==== Will clone the waf-api service.. ===="
git clone https://github.com/89berner/waf-api.git tmp/
mv tmp/* services/waf/

echo "==== Selecting project $PROJECT_NAME.. ===="
gcloud config set project $PROJECT_NAME

echo "==== Setting region to europe-west1.. ===="
gcloud config set compute/region europe-west1

echo "==== Setting zone to europe-west1-b.. ===="
gcloud config set compute/zone europe-west1-b

### SECRETS ###
echo "==== Adding logstashsub SA for logstash.. ===="
gcloud iam service-accounts create logstashsub --display-name "logstashsub"
if [ $? -eq 0 ]; then
	echo "==== Adding iam policy binding for logstashsub.. ===="
	gcloud projects add-iam-policy-binding $PROJECT_NAME --member serviceAccount:logstashsub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.subscriber
	echo "==== Storing credentials.. ===="
	gcloud iam service-accounts keys create credentials/logstashsub.json --iam-account=logstashsub@$PROJECT_NAME.iam.gserviceaccount.com
else
    echo "==== SA for logstashsub already existed ====";
fi

echo "==== Adding pubsubpublisher SA for Beam.. ===="
gcloud iam service-accounts create pubsubpublisher --display-name "pubsubpublisher"
if [ $? -eq 0 ]; then
	echo "==== Adding iam policy binding for pubsubpublisher.. ===="
	gcloud projects add-iam-policy-binding $PROJECT_NAME --member serviceAccount:pubsubpublisher@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.publisher
	echo "==== Storing credentials.. ===="
	gcloud iam service-accounts keys create credentials/pubsubpublisher.json --iam-account=pubsubpublisher@$PROJECT_NAME.iam.gserviceaccount.com
else
    echo "==== SA for pubsubpublisher already existed ====";
fi

echo "==== Adding alertersub SA for Beam.."
gcloud iam service-accounts create alertersub --display-name "alertersub"
if [ $? -eq 0 ]; then
	echo "==== Adding iam policy binding for alertersub.. ===="
	gcloud projects add-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/pubsub.subscriber
	gcloud projects add-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/bigquery.dataViewer
	gcloud projects add-iam-policy-binding $PROJECT_NAME --member serviceAccount:alertersub@$PROJECT_NAME.iam.gserviceaccount.com --role roles/bigquery.jobUser
	echo "==== Storing credentials.. ===="
	gcloud iam service-accounts keys create credentials/alertersub.json --iam-account=alertersub@$PROJECT_NAME.iam.gserviceaccount.com
else
    echo "==== SA for alertersub already existed ====";
fi

### REGIONAL IPS ###
echo "==== Setting regional ip address for redis service.. ===="
gcloud compute addresses create redis-ip --region europe-west1 --subnet default --addresses 10.132.0.5

echo "==== Setting regional ip address for waf service.. ===="
gcloud compute addresses create waf-ip --region europe-west1 --subnet default --addresses 10.132.0.14

echo "==== Initializing Terraform.. ===="
terraform init

echo "==== Applying Terraform Configuration.. ===="
terraform apply -auto-approve -var "project_name=$PROJECT_NAME"

### SERVICES ###
echo "==== Creating waf service from templates.. ===="
sed "s/PROJECT_NAME_TEMPLATE/$PROJECT_NAME/g" services/alerter/alerter.yaml.template   > services/alerter/alerter.yaml
sed "s/PROJECT_NAME_TEMPLATE/$PROJECT_NAME/g" services/demo-web/demo-web.yaml.template > services/demo-web/demo-web.yaml
sed "s/PROJECT_NAME_TEMPLATE/$PROJECT_NAME/g" services/logstash/logstash.yaml.template > services/logstash/logstash.yaml
sed "s/PROJECT_NAME_TEMPLATE/$PROJECT_NAME/g" services/scanner/scanner.yaml.template   > services/scanner/scanner.yaml
sed "s/PROJECT_NAME_TEMPLATE/$PROJECT_NAME/g" services/waf/waf.yaml.template           > services/waf/waf.yaml

echo "==== Building image for alerter.. ===="
docker build -t gcr.io/$PROJECT_NAME/alerter:latest services/alerter/
docker push     gcr.io/$PROJECT_NAME/alerter:latest

echo "==== Building image for demo-web.. ===="
docker build -t gcr.io/$PROJECT_NAME/demo-web:latest services/demo-web/
docker push     gcr.io/$PROJECT_NAME/demo-web:latest

echo "==== Building image for logstash.. ===="
docker build -t gcr.io/$PROJECT_NAME/logstash-waf:latest services/logstash/
docker push     gcr.io/$PROJECT_NAME/logstash-waf:latest

echo "==== Building image for scanner.. ===="
docker build -t gcr.io/$PROJECT_NAME/scanner:latest services/scanner/
docker push     gcr.io/$PROJECT_NAME/scanner:latest

echo "==== Building image for waf.. ===="
docker build -t gcr.io/$PROJECT_NAME/waf:latest services/waf/
docker push     gcr.io/$PROJECT_NAME/waf:latest

echo "==== Getting credentials from Kubernetes.. ===="
gcloud container clusters get-credentials cluster-waf-api-talk

echo "==== Uploading logstashsub credentials to kubernetes cluster.. ===="
kubectl create secret generic pubsub-key --from-file=credentials/logstashsub.json

echo "==== Uploading pubsubpublisher credentials to kubernetes cluster.. ===="
kubectl create secret generic pubsub-publisher-key --from-file=credentials/pubsubpublisher.json

echo "==== Uploading alertersub credentials to kubernetes cluster.. ===="
kubectl create secret generic alertersub-key --from-file=credentials/alertersub.json

### KUBERNETES ###

echo "==== Creating elasticsearch service.. ===="
kubectl apply -f services/elasticsearch/elasticsearch_service.yaml

echo "==== Creating elasticsearch storage.. ===="
kubectl apply -f services/elasticsearch/elasticsearch_storage.yaml

echo "==== Creating elasticsearch workflow.. ===="
kubectl apply -f services/elasticsearch/elasticsearch.yaml

echo "==== Creating kibana workflow.. ===="
kubectl apply -f services/kibana/kibana.yaml

echo "==== Creating kibana service.. ===="
kubectl apply -f services/kibana/kibana_service.yaml

echo "==== Creating logstash workflow.. ===="
kubectl apply -f services/logstash/logstash.yaml

echo "==== Creating waf workflow.. ===="
kubectl apply -f services/waf/waf.yaml

echo "==== Creating waf service.. ===="
kubectl apply -f services/waf/waf_service.yaml

echo "==== Creating demo-web workflow.. ===="
kubectl apply -f services/demo-web/demo-web.yaml

echo "==== Creating demo-web service.. ===="
kubectl apply -f services/demo-web/demo-web_service.yaml

echo "==== Creating redis workflow.. ===="
kubectl apply -f services/redis/redis.yaml

echo "==== Creating redis service.. ===="
kubectl apply -f services/redis/redis_service.yaml

echo "==== Creating scanner workflow.. ===="
kubectl apply -f services/scanner/scanner.yaml

echo "==== Creating alerter workflow.. ===="
kubectl apply -f services/alerter/alerter.yaml

echo "==== To open Kibana use the following command ===="
echo 'kubectl port-forward $(kubectl get pods|grep kibana|cut -d " " -f1|head -n1) 5601:5601'
echo "Finished setup at $(date)"

### DATAFLOW ###

echo "==== Waiting for resources to be created.. ===="
sleep 120;

echo "==== Starting dataflow job.. ===="
mvn compile exec:java -Dexec.mainClass=org.waf.pipeline.WafPipeline -Dexec.args="--defaultWorkerLogLevel=INFO --workerMachineType=n1-standard-1 --diskSizeGb=100 --maxNumWorkers=1 --projectName=$PROJECT_NAME --region=europe-west1 --zone=europe-west1-b --runner=DataflowRunner --jobName=$PROJECT_NAME-pipeline" -Pdataflow-runner -f flow_processor/pom.xml