#!/usr/bin/env bash
# Destroys everything deploy.sh created.
# LoadBalancer Services are deleted FIRST: their ELBs are created by Kubernetes, not
# Terraform, and would otherwise block deleting the VPC (and keep costing money).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/3 deleting LoadBalancer services (removes the AWS ELBs)"
kubectl delete svc spendwise --ignore-not-found --wait=true || true
kubectl -n monitoring delete svc grafana --ignore-not-found --wait=true || true

echo "==> 2/3 waiting 60s for AWS to release the ELBs and their network interfaces"
sleep 60

echo "==> 3/3 terraform destroy"
# db_password is required by the config even for destroy; any value works here
export TF_VAR_db_password="${TF_VAR_db_password:-destroy-only-placeholder}"
terraform -chdir=terraform destroy

echo "Done. Double-check the AWS console (EC2 > Load Balancers, VPC > NAT gateways, RDS) in ap-south-1."
