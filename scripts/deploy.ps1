# PowerShell version of deploy.sh. Usage:
#   $env:TF_VAR_db_password = 'a-strong-password'
#   .\scripts\deploy.ps1
# Ansible does not run natively on Windows: step 6 calls it through WSL with kubectl.exe.
# ⚠️ Creates billable AWS resources - run .\scripts\teardown.ps1 afterwards.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not $env:TF_VAR_db_password) { throw "Set `$env:TF_VAR_db_password first" }
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }

function Invoke-Native { & $args[0] $args[1..($args.Count - 1)]; if ($LASTEXITCODE -ne 0) { throw "$($args -join ' ') failed" } }
function New-RandomHex { -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) }) }

Write-Host "==> 1/7 terraform apply"
Invoke-Native terraform -chdir=terraform init -input=false
Invoke-Native terraform -chdir=terraform apply
$Cluster = terraform -chdir=terraform output -raw cluster_name
$RdsHost = terraform -chdir=terraform output -raw rds_endpoint

Write-Host "==> 2/7 kubeconfig"
Invoke-Native aws eks update-kubeconfig --region $Region --name $Cluster
kubectl get nodes

Write-Host "==> 3/7 secrets"
kubectl get secret spendwise-secrets 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Invoke-Native kubectl create secret generic spendwise-secrets `
    "--from-literal=SECRET_KEY=$(New-RandomHex)" `
    --from-literal=DB_USER=spendwise_admin `
    "--from-literal=DB_PASSWORD=$env:TF_VAR_db_password"
}
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring get secret grafana-admin 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Invoke-Native kubectl -n monitoring create secret generic grafana-admin "--from-literal=password=$((New-RandomHex).Substring(0, 24))"
}

Write-Host "==> 4/7 configmap with DB_HOST=$RdsHost"
(Get-Content k8s/configmap.yaml -Raw).Replace("REPLACE_WITH_RDS_ENDPOINT", $RdsHost) | kubectl apply -f -

Write-Host "==> 5/7 deploy the app"
Invoke-Native kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
Invoke-Native kubectl rollout status deployment/spendwise --timeout=300s

Write-Host "==> 6/7 monitoring (Ansible via WSL, calling Windows kubectl.exe)"
$WinManifests = (Resolve-Path ansible/manifests).Path -replace '\\', '/'
$WslPlaybookDir = (wsl wslpath -a ((Resolve-Path ansible).Path -replace '\\', '/')).Trim()
wsl ansible-playbook -i "$WslPlaybookDir/inventory.ini" "$WslPlaybookDir/playbook.yml" `
  -e kubectl=kubectl.exe -e "manifests_dir=$WinManifests"

Write-Host "==> 7/7 load balancer URLs"
for ($i = 0; $i -lt 30; $i++) {
  $App = kubectl get svc spendwise -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
  $Grafana = kubectl -n monitoring get svc grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
  if ($App -and $Grafana) { break }
  Start-Sleep -Seconds 10
}
Write-Host "Spendwise : http://$App"
Write-Host "Grafana   : http://$Grafana  (user: admin)"
Write-Host "Seed demo data: kubectl exec deploy/spendwise -c spendwise -- flask seed"
