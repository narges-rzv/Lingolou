# AKS Migration — Progress & Resume Guide

## Status: Paused — Waiting for ARM VM quota approval

### What's Done

1. **Kubernetes manifests created** — `k8s/` directory with 7 YAML files:
   - `namespace.yaml` — `lingolou` namespace
   - `service-account.yaml` — workload identity (needs `<IDENTITY_CLIENT_ID>` replaced after Step 2)
   - `cluster-issuer.yaml` — Let's Encrypt prod via cert-manager
   - `pvc.yaml` — PV + PVC for existing Azure Files `lingolou-data` share
   - `deployment.yaml` — app + Redis sidecar, probes, resource limits
   - `service.yaml` — ClusterIP on port 80 → 8000
   - `ingress.yaml` — nginx ingress with TLS for `www.lingolou.app`

2. **`entrypoint.sh` modified** — removed embedded Redis startup (now a sidecar)

3. **`.github/workflows/deploy.yml` updated** — replaced Container Apps deploy with AKS (`azure/aks-set-context@v4` + `kubectl set image`)

4. **`Makefile` updated** — added `aks-context`, `aks-deploy`, `aks-logs`, `aks-status`, `aks-restart` targets

5. **Azure provider registered** — `Microsoft.ContainerService` is registered

### What's Blocking

**ARM VM quota**: Your subscription has 0 cores for `standardBPSv2Family` (ARM B-series v2) in East US.

**To request quota increase:**
1. Go to Azure Portal → Subscriptions → Usage + quotas
2. Search for `standardBPSv2` or `Standard BPSv2 Family`
3. Request increase to **2 cores** for **East US**
4. Approval is usually within minutes for small requests

**Alternative**: Use `Standard_D2s_v4` (x86, ~$70/mo) which has quota available — no Docker build changes needed. You can resize to ARM later.

### Remaining Steps (after quota approval)

#### Step 1: Create AKS Cluster
```bash
# If using ARM (after quota approval):
az aks create -g Lingolou -n lingolou-aks \
  --node-count 1 --node-vm-size Standard_B2pls_v2 \
  --enable-oidc-issuer --enable-workload-identity \
  --tier free --generate-ssh-keys

# If using x86 (no quota needed):
az aks create -g Lingolou -n lingolou-aks \
  --node-count 1 --node-vm-size Standard_D2s_v4 \
  --enable-oidc-issuer --enable-workload-identity \
  --tier free --generate-ssh-keys

az aks get-credentials -g Lingolou -n lingolou-aks
```

#### Step 2: Install Helm Charts
```bash
# nginx-ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.replicaCount=1 \
  --set controller.resources.requests.cpu=100m \
  --set controller.resources.requests.memory=128Mi

# cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi
```

#### Step 3: Set Up Workload Identity
```bash
az identity create -g Lingolou -n lingolou-aks-identity

IDENTITY_CLIENT_ID=$(az identity show -g Lingolou -n lingolou-aks-identity --query clientId -o tsv)
AKS_OIDC_ISSUER=$(az aks show -g Lingolou -n lingolou-aks --query oidcIssuerProfile.issuerUrl -o tsv)

az identity federated-credential create \
  -g Lingolou --identity-name lingolou-aks-identity \
  --name lingolou-fed-cred \
  --issuer "$AKS_OIDC_ISSUER" \
  --subject system:serviceaccount:lingolou:lingolou-sa \
  --audiences api://AzureADTokenExchange

IDENTITY_PRINCIPAL=$(az identity show -g Lingolou -n lingolou-aks-identity --query principalId -o tsv)
STORAGE_ID=$(az storage account show -n lingoloudisk --query id -o tsv)
az role assignment create --assignee "$IDENTITY_PRINCIPAL" \
  --role "Storage Blob Data Contributor" --scope "$STORAGE_ID"

# Update k8s/service-account.yaml with the actual IDENTITY_CLIENT_ID
```

#### Step 4: Create Kubernetes Secrets
```bash
kubectl create secret docker-registry acr-secret -n lingolou \
  --docker-server=lingolou.azurecr.io \
  --docker-username=lingolou \
  --docker-password="<ACR_PASSWORD>"

kubectl create secret generic azure-files-secret -n lingolou \
  --from-literal=azurestorageaccountname=lingoloudisk \
  --from-literal=azurestorageaccountkey="<STORAGE_KEY>"

kubectl create secret generic lingolou-secrets -n lingolou \
  --from-literal=SESSION_SECRET_KEY="<value>" \
  --from-literal=OPENAI_API_KEY="<value>" \
  --from-literal=ELEVENLABS_API_KEY="<value>" \
  --from-literal=GOOGLE_CLIENT_ID="<value>" \
  --from-literal=GOOGLE_CLIENT_SECRET="<value>" \
  --from-literal=CORS_ORIGINS="https://www.lingolou.app"
```

#### Step 5: Deploy
```bash
kubectl apply -f k8s/
```

#### Step 6: Update Docker Build (ARM only)
If using ARM node, update `.github/workflows/deploy.yml` to build `linux/arm64` instead of `linux/amd64`.

#### Step 7: DNS Cutover
```bash
# Get ingress external IP
kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Update DNS A record for www.lingolou.app → new IP
# Verify cert-manager provisioned the TLS certificate:
kubectl get certificate -n lingolou
```

#### Step 8: Verify
```bash
kubectl get nodes
kubectl get pods -n lingolou
curl https://www.lingolou.app/health
```

#### Step 9: Decommission Container Apps (after verification)
```bash
az containerapp delete -n lingolou -g Lingolou
az containerapp env delete -n lingolou-env -g Lingolou
```

### VM Choice Impact on Docker Build

| VM | Architecture | Docker `--platform` | Dockerfile changes |
|----|-------------|--------------------|--------------------|
| Standard_B2pls_v2 | ARM64 | `linux/arm64` | None (Python/Node work on ARM) |
| Standard_D2s_v4 | x86_64 | `linux/amd64` (current) | None |
