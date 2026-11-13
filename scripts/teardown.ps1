# PowerShell version of teardown.sh - delete LoadBalancer Services first, then terraform destroy.
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> 1/3 deleting LoadBalancer services (removes the AWS ELBs)"
kubectl delete svc spendwise --ignore-not-found --wait=true
kubectl -n monitoring delete svc grafana --ignore-not-found --wait=true

Write-Host "==> 2/3 waiting 60s for AWS to release the ELBs"
Start-Sleep -Seconds 60

Write-Host "==> 3/3 terraform destroy"
if (-not $env:TF_VAR_db_password) { $env:TF_VAR_db_password = "destroy-only-placeholder" }
terraform -chdir=terraform destroy
Write-Host "Done. Double-check EC2 > Load Balancers, VPC > NAT gateways and RDS in ap-south-1."
