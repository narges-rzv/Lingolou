# AKS Migration — Full Status as of 2026-05-16

## Overall Status: Cluster running, DNS propagating, port 80 unreachable (blocking TLS)

---

## What's Fully Done

1. **AKS cluster** — `lingolou-aks`, East US, `Standard_D2s_v4`, k8s 1.34.7, `Succeeded`
2. **Helm installs** — `ingress-nginx` + `cert-manager` (v1.20.2) in their own namespaces
3. **Workload identity** — managed identity `lingolou-aks-identity`, client ID `466d6d0d-0a96-4763-b51e-709314087c8a`, federated credential bound to `system:serviceaccount:lingolou:lingolou-sa`
4. **k8s secrets** — `acr-secret`, `azure-files-secret`, `lingolou-secrets` all created in `lingolou` namespace via `kubectl create secret` (nothing on disk)
5. **Manifests applied** — `kubectl apply -f k8s/` deployed namespace, SA, cluster-issuer, PVC, deployment, service, ingress
6. **Pod running** — `2/2 Running` (app + redis sidecar)
7. **Database intact** — same Azure Files share mounted, 24 users / 22 stories / 64 chapters, alembic at `9274db3a1fbc`
8. **Audio files intact** — using same `azure_blob` storage account `lingoloudisk`, no migration needed
9. **DNS updated** — GoDaddy A record for `www.lingolou.app` → `57.151.44.179` set (authoritative nameserver confirmed). Old record was a CNAME to Container Apps. TTL 3600.
10. **Code fixes committed and pushed** to `feature/aks-migration`:
    - Removed stale `az containerapp update` step from `deploy.yml`
    - Added `imagePullSecrets: acr-secret` to `k8s/deployment.yaml`
    - Filled in workload identity client ID in `k8s/service-account.yaml`
    - Updated `README.md` and `CLAUDE.md` to reflect AKS pattern

---

## What's Blocked: Port 80 Not Reachable Externally

### Symptom
cert-manager ACME HTTP-01 challenge failed:
```
400 urn:ietf:params:acme:error:connection: 57.151.44.179:
Fetching http://www.lingolou.app/.well-known/acme-challenge/...: Timeout during connect (likely firewall problem)
```
Manual `curl http://57.151.44.179:80` also times out from external. Port 80 is simply not reachable from the internet.

### What Was Ruled Out
- **NSG** — has rule allowing TCP 80 and 443 from Internet ✓
- **LB rules** — Azure LB has rules for port 80 → nodePort 31962, and 443 → nodePort 31340 ✓
- **Nginx ingress pod** — running, responds on port 80 internally (tested with curl pod from inside cluster, got HTTP 308) ✓
- **LB backend pool config** — looks correct ✓

### Root Cause Hypothesis
The Azure LB health probe for port 80 is configured as **HTTP** to nodePort 31962, checking path `/`. Nginx returns **HTTP 308** (redirect to HTTPS). Azure HTTP probes require exactly **HTTP 200** — a 308 causes the backend to be marked **unhealthy**, so the LB stops forwarding port 80 traffic entirely.

### Fix to Apply Next Session

**Option A (simplest):** Patch nginx-ingress service to use TCP health probe instead of HTTP:
```bash
kubectl annotate svc ingress-nginx-controller -n ingress-nginx \
  "service.beta.kubernetes.io/azure-load-balancer-health-probe-protocol=tcp"
```
Then verify the LB probe changes from HTTP to TCP. TCP probes only check TCP handshake success, not HTTP response.

**Option B:** Configure nginx ingress to use its own `/healthz` endpoint on port 10254:
```bash
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-port"="10254"
```

After fixing, the LB will forward port 80, cert-manager will complete the ACME challenge, and TLS will be issued automatically.

### After TLS is Issued
- Verify: `kubectl get certificate -n lingolou` shows `READY: True`
- Test: `curl https://www.lingolou.app/health`
- Decommission old Container App (Step 9):
  ```bash
  az containerapp delete -n lingolou -g Lingolou
  az containerapp env delete -n lingolou-env -g Lingolou
  ```

---

## Session Log — What Worked / What Didn't

### ARM VM quota (failed → switched to x86)
- **Tried:**
  ```bash
  az aks create -g Lingolou -n lingolou-aks --node-count 1 --node-vm-size Standard_B2pls_v2 \
    --enable-oidc-issuer --enable-workload-identity --tier free --generate-ssh-keys
  ```
- **Result:** Cluster provisioned but node pool stuck in `Failed` — 0 ARM cores in East US
- **Confirmed quota:**
  ```bash
  az vm list-usage --location eastus --query "[?contains(name.value,'standardDSv4')]..." -o table
  # Standard DSv4 Family: current=0, limit=10
  ```
- **Fix:**
  ```bash
  az aks delete -g Lingolou -n lingolou-aks --yes --no-wait
  # waited with polling loop until cluster gone, then:
  az aks create -g Lingolou -n lingolou-aks --node-count 1 --node-vm-size Standard_D2s_v4 \
    --enable-oidc-issuer --enable-workload-identity --tier free --generate-ssh-keys
  az aks get-credentials -g Lingolou -n lingolou-aks --overwrite-existing
  kubectl get nodes   # confirmed Ready
  ```

### Helm not installed
- **Fix:** `brew install helm`

### Helm repos and installs (worked first try)
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.replicaCount=1 \
  --set controller.resources.requests.cpu=100m \
  --set controller.resources.requests.memory=128Mi

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi
```

### Workload identity setup (worked)
```bash
az identity create -g Lingolou -n lingolou-aks-identity

IDENTITY_CLIENT_ID=$(az identity show -g Lingolou -n lingolou-aks-identity --query clientId -o tsv)
AKS_OIDC_ISSUER=$(az aks show -g Lingolou -n lingolou-aks --query oidcIssuerProfile.issuerUrl -o tsv)
IDENTITY_PRINCIPAL=$(az identity show -g Lingolou -n lingolou-aks-identity --query principalId -o tsv)
STORAGE_ID=$(az storage account show -n lingoloudisk --query id -o tsv)

az identity federated-credential create -g Lingolou --identity-name lingolou-aks-identity \
  --name lingolou-fed-cred --issuer "$AKS_OIDC_ISSUER" \
  --subject system:serviceaccount:lingolou:lingolou-sa \
  --audiences api://AzureADTokenExchange

az role assignment create --assignee "$IDENTITY_PRINCIPAL" \
  --role "Storage File Data SMB Share Contributor" --scope "$STORAGE_ID"
```

### Namespace missing when creating secrets
- **Tried:** `kubectl create secret ... -n lingolou` before applying manifests → `namespaces "lingolou" not found`
- **Fix:** Apply namespace and SA first:
  ```bash
  kubectl apply -f k8s/namespace.yaml && kubectl apply -f k8s/service-account.yaml
  ```

### Secrets creation (worked — all values passed as CLI args, never written to files)
```bash
# ACR password retrieved via: az acr credential show -n lingolou
# Storage key retrieved via: az storage account keys list -n lingoloudisk -g Lingolou --query "[0].value"
# App secrets read from .env (SESSION_SECRET_KEY retrieved from Azure Container Apps UI)

kubectl create secret docker-registry acr-secret -n lingolou \
  --docker-server=lingolou.azurecr.io --docker-username=lingolou --docker-password="<from az acr>"

kubectl create secret generic azure-files-secret -n lingolou \
  --from-literal=azurestorageaccountname=lingoloudisk \
  --from-literal=azurestorageaccountkey="<from az storage>"

kubectl create secret generic lingolou-secrets -n lingolou \
  --from-literal=SESSION_SECRET_KEY="$SESSION_SECRET_KEY" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  --from-literal=GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  --from-literal=GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  --from-literal=CORS_ORIGINS="https://www.lingolou.app"
```

### Apply all manifests
```bash
kubectl apply -f k8s/
# Output: namespace unchanged, SA unchanged, clusterissuer created, deployment created,
#         ingress created, pv created, pvc created, service created
```

### Redis CrashLoopBackOff (failed → fixed)
- **Symptom:** `bind: Address in use` on port 6379 in redis sidecar
- **Root cause:** `lingolou-app:latest` in ACR was built from `main` before AKS branch merged — old `entrypoint.sh` started embedded Redis, conflicting with the sidecar
- **Fix:**
  ```bash
  az acr login -n lingolou
  docker buildx build --platform linux/amd64 \
    -t lingolou.azurecr.io/lingolou-app:aks-v1 \
    -t lingolou.azurecr.io/lingolou-app:latest --push .
  kubectl rollout restart deployment/lingolou -n lingolou
  kubectl rollout status deployment/lingolou -n lingolou --timeout=180s
  # → "successfully rolled out"
  ```

### Missing `imagePullSecrets` (failed → fixed)
- **Symptom:** `ErrImagePull 401 Unauthorized` on `lingolou.azurecr.io`
- **Fix:** Added to `k8s/deployment.yaml`:
  ```yaml
  imagePullSecrets:
    - name: acr-secret
  ```
  Then `kubectl apply -f k8s/deployment.yaml`

### DNS cutover
- **Found:** `www` was a CNAME (not A record) → `lingolou.yellowdune-2e117bec.eastus.azurecontainerapps.io`
- **Fix in GoDaddy:** Deleted CNAME, added A record `www` → `57.151.44.179` (TTL 3600)
- **Verified authoritative nameserver immediately:**
  ```bash
  dig www.lingolou.app A +short @ns35.domaincontrol.com
  # → 57.151.44.179 ✓
  ```

### cert-manager ACME HTTP-01 challenge (failed — current blocker)
- **Symptom:** Order in `invalid` state, Let's Encrypt timeout on port 80
- **Investigated:**
  ```bash
  kubectl describe challenge -n lingolou   # → "Timeout during connect (likely firewall problem)"
  curl --max-time 10 http://57.151.44.179/...  # → times out externally
  kubectl run test-curl --image=curlimages/curl --rm -i -- curl http://ingress-nginx-controller...
  # → HTTP 308 ✓ (works internally)
  az network nsg rule list -g MC_Lingolou_lingolou-aks_eastus --nsg-name aks-agentpool-21866258-nsg
  # → allows TCP 80,443 from Internet ✓
  az network lb rule list -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes
  # → LB has 80→31962, 443→31340 ✓
  az network lb probe list -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes
  # → HTTP probe to port 31962, path "/" — this is the likely culprit ✗
  ```
- **Root cause hypothesis:** Azure HTTP health probe gets HTTP 308 from nginx; Azure requires 200 → backend marked unhealthy → LB drops all port 80 traffic
- **Not yet tried:** Fix health probe (see "Fix to Apply Next Session" above)

---

## Key Resource IDs

| Resource | Value |
|----------|-------|
| AKS cluster | `lingolou-aks` in RG `Lingolou` |
| Ingress IP | `57.151.44.179` |
| ACR | `lingolou.azurecr.io` |
| Storage account | `lingoloudisk` |
| Azure Files share | `lingolou-data` |
| Workload identity client ID | `466d6d0d-0a96-4763-b51e-709314087c8a` |
| NSG | `aks-agentpool-21866258-nsg` in RG `MC_Lingolou_lingolou-aks_eastus` |
| LB | `kubernetes` in RG `MC_Lingolou_lingolou-aks_eastus` |

---

## Branch State

Branch: `feature/aks-migration` — pushed, up to date with origin.
Last commit: `b1bad34` — docs update.
NOT yet merged to main (waiting for migration to be fully verified).
