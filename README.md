# waf-api-talk

This project is meant to be an example of how to setup a WAF service. This is not to be expected to run on a production environment.

To build the project run: /bin/bash setup.sh

Once that is set, you will need to setup port forwarding to access Kibana:
kubectl port-forward $(kubectl get pods|grep kibana|cut -d ' ' -f1|head -n1) 5601:5601