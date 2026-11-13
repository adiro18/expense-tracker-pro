# Kubernetes secrets (created imperatively - never committed)

The app reads `SECRET_KEY`, `DB_USER` and `DB_PASSWORD` from the `spendwise-secrets` Secret.
It is created with `kubectl` so that no secret value ever lands in a YAML file in Git.

```bash
# DB_PASSWORD must be the same value you exported as TF_VAR_db_password for terraform apply
kubectl create secret generic spendwise-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DB_USER=spendwise_admin \
  --from-literal=DB_PASSWORD="$TF_VAR_db_password"
```

PowerShell:

```powershell
$secret = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
kubectl create secret generic spendwise-secrets `
  --from-literal=SECRET_KEY=$secret `
  --from-literal=DB_USER=spendwise_admin `
  --from-literal=DB_PASSWORD=$env:TF_VAR_db_password
```

Grafana admin password (used by `ansible/manifests/grafana.yaml`):

```bash
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=password="$(openssl rand -base64 18)"

# read it back later
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.password}' | base64 -d
```

To change a value: `kubectl delete secret spendwise-secrets`, re-create it, then
`kubectl rollout restart deployment/spendwise`.
