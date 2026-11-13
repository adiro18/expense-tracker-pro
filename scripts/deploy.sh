#!/usr/bin/env bash
# Full AWS deployment:
#   terraform apply -> kubeconfig -> secrets -> configmap (RDS host) -> app -> monitoring -> URLs
#
#   export TF_VAR_db_password='a-strong-password'
#   ./scripts/deploy.sh
#
# ⚠️ Creates billable AWS resources (EKS, NAT gateway, RDS, load balancers).
#    Run ./scripts/teardown.sh when the demo is over.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${TF_VAR_db_password:?export TF_VAR_db_password first (same value is used for the K8s secret)}"
REGION="${AWS_REGION:-ap-south-1}"

echo "==> 1/7 terraform apply (review the plan, then type 'yes')"
terraform -chdir=terraform init -input=false
terraform -chdir=terraform apply

CLUSTER=$(terraform -chdir=terraform output -raw cluster_name)
RDS_HOST=$(terraform -chdir=terraform output -raw rds_endpoint)

echo "==> 2/7 kubeconfig for $CLUSTER"
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER"
kubectl get nodes

echo "==> 3/7 secrets (created only if missing, values never written to disk)"
if ! kubectl get secret spendwise-secrets >/dev/null 2>&1; then
  kubectl create secret generic spendwise-secrets \
    --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=DB_USER=spendwise_admin \
    --from-literal=DB_PASSWORD="$TF_VAR_db_password"
fi
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1; then
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=password="$(openssl rand -base64 18)"
fi

echo "==> 4/7 configmap with DB_HOST=$RDS_HOST"
sed "s|REPLACE_WITH_RDS_ENDPOINT|$RDS_HOST|" k8s/configmap.yaml | kubectl apply -f -

echo "==> 5/7 deploy the app"
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
kubectl rollout status deployment/spendwise --timeout=300s

echo "==> 6/7 monitoring (Ansible)"
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml

echo "==> 7/7 waiting for load balancer hostnames"
lb() { kubectl get svc "$@" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'; }
for _ in $(seq 1 30); do
  APP=$(lb spendwise); GRAFANA=$(lb -n monitoring grafana)
  [[ -n "$APP" && -n "$GRAFANA" ]] && break
  sleep 10
done
echo
echo "Spendwise : http://${APP:-<pending - kubectl get svc spendwise>}"
echo "Grafana   : http://${GRAFANA:-<pending - kubectl -n monitoring get svc grafana>}  (user: admin)"
echo "Grafana password: kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.password}' | base64 -d"
echo "Seed demo data  : kubectl exec deploy/spendwise -c spendwise -- flask seed"
echo "(New ELB DNS names can take 2-3 minutes to resolve.)"
