#!/bin/bash

PROJECT_NAME=$1
mvn compile exec:java -Dexec.mainClass=org.waf.pipeline.WafPipeline -Dexec.args="--defaultWorkerLogLevel=INFO --workerMachineType=n1-standard-1 --diskSizeGb=100 --maxNumWorkers=1 --projectName=$PROJECT_NAME --region=europe-west1 --zone=europe-west1-b --runner=DataflowRunner --jobName=$PROJECT_NAME-pipeline" -Pdataflow-runner