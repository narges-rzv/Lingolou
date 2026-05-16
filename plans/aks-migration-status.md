# AKS Migration — Session Log & Lessons

> Focus: what we tried, what failed, why, and what finally worked.
> Final state: https://www.lingolou.app live, TLS issued, audio working.
> Pending: Container Apps env deletion in progress (`ScheduledForDelete`), merge `feature/aks-migration` to main.

---

## Pitfalls — Quick Reference

Everything that bit us, in one place. Details in the session log below.

1. **ARM quota is zero by default in East US.** `Standard_B2pls_v2` (ARM) provisioned the cluster but left the node pool in `Failed`. Always confirm quota for the exact VM family before creating. x86 (`Standard_D2s_v4`) had quota.

2. **Azure Files and Azure Blob are separate RBAC planes.** `Storage File Data SMB Share Contributor` grants nothing on Blob. If your app uses both (e.g. SQLite on Files + audio on Blob), assign both roles to the workload identity upfront: `Storage File Data SMB Share Contributor` + `Storage Blob Data Contributor`.

3. **User-delegation SAS tokens require a Blob Data role — not just Blob access.** The app calls `get_user_delegation_key()` which is an Azure AD operation. The identity needs `Storage Blob Data Contributor` (or Reader) even if you only need read-only SAS URLs.

4. **The k8s namespace must exist before `kubectl create secret`.** Obvious in hindsight — apply `namespace.yaml` and `service-account.yaml` before creating any secrets in that namespace.

5. **`imagePullSecrets` is separate from workload identity.** Workload identity handles Azure SDK calls inside the pod, but pulling images from ACR still requires a docker-registry secret explicitly referenced in `imagePullSecrets` on the deployment. The pod gets `ErrImagePull 401` without it.

6. **Build and push a fresh image from the branch you're deploying.** The `latest` tag in ACR was from `main`, which still had an embedded Redis in `entrypoint.sh`. The AKS branch removed that. Deploying a stale image caused a port 6379 bind conflict between the embedded Redis and the sidecar.

7. **The Azure LB HTTP health probe requires exactly HTTP 200 — redirects count as failure.** Nginx redirects port 80 → HTTPS with 308. The LB marked the backend unhealthy and silently dropped all port 80 traffic. NSG rules, LB rules, and the pod itself were all fine — the probe was the only problem. Diagnose with `az network lb probe list`.

8. **`kubectl annotate` on a Helm-managed resource causes a field manager conflict on the next `helm upgrade`.** Helm uses server-side apply and disputes ownership. Remove the manual annotation first (trailing `-` syntax: `kubectl annotate svc foo key-`) before running `helm upgrade`.

9. **The AKS CCM doesn't always reconcile all service annotations to the LB.** In our cluster version, the probe path and protocol annotations were picked up, but the probe port annotation was silently ignored. When annotations don't take effect after a few minutes, patch the Azure LB directly with `az network lb probe update`.

10. **The direct `az network lb probe update` patch may revert after AKS cluster upgrades.** The CCM reconciles LB state during node pool upgrades and cluster version bumps. If port 80 goes unreachable again after an upgrade, re-run the probe patch (see session 2). Check with `az network lb probe list -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes -o table` — if the port column is back to a nodePort (30000+ range) instead of 10254, the CCM overwrote it.

11. **The 443 probe also changed to `/healthz` as a side effect of the Helm annotations.** The `azure-load-balancer-health-probe-request-path` annotation applies to all probes on the service, not just port 80. The 443 probe went from `Https /` to `Https /healthz`. This is fine — nginx serves `/healthz` on port 10254 regardless of TLS — but be aware if you're debugging the 443 probe separately.

12. **cert-manager does not auto-retry from `invalid` Order state.** Once an ACME order goes invalid (e.g. because port 80 was unreachable), you must manually delete the CertificateRequest (`kubectl delete certificaterequest --all -n <ns>`). The Order is garbage-collected automatically. Then annotate the Certificate to trigger re-issuance.

13. **DNS: GoDaddy won't let you change a CNAME to an A record in-place.** Delete the CNAME first, then add the A record. Verify immediately against the authoritative nameserver (`dig @ns35.domaincontrol.com`) to bypass local TTL cache.

14. **RBAC propagation takes ~1 minute after `az role assignment create`.** Don't restart the pod and immediately test — wait for propagation first. Poll with a `until` loop rather than a blind sleep.

---

## Session 1

### ARM quota — cluster node pool stuck in Failed

**Symptom:** `az aks create` succeeded but node pool stayed in `Failed` with no nodes.

**Diagnosis:** The VM size `Standard_B2pls_v2` is ARM (Ampere). East US had 0 ARM core quota.
```bash
az vm list-usage --location eastus --query "[?contains(name.value,'standardBPLSv2')]" -o table
# CurrentValue=0, Limit=0
```

**Fix:** Delete the failed cluster, recreate with x86 (`Standard_D2s_v4` — available quota confirmed first):
```bash
az aks delete -g Lingolou -n lingolou-aks --yes --no-wait
# poll until gone before recreating
az aks create -g Lingolou -n lingolou-aks --node-count 1 --node-vm-size Standard_D2s_v4 \
  --enable-oidc-issuer --enable-workload-identity --tier free --generate-ssh-keys
az aks get-credentials -g Lingolou -n lingolou-aks --overwrite-existing
```

**Lesson:** Always confirm quota for the exact VM family before creating a cluster. ARM and x86 use separate quota pools.

---

### Helm repos and cluster tooling

Helm wasn't installed locally — `brew install helm`. Then:
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

---

### Workload identity setup

Needed for: (1) mounting Azure Files over SMB without a storage account key in the pod, (2) generating Azure Blob SAS tokens without a storage key.

```bash
az identity create -g Lingolou -n lingolou-aks-identity

IDENTITY_CLIENT_ID=$(az identity show -g Lingolou -n lingolou-aks-identity --query clientId -o tsv)
IDENTITY_PRINCIPAL=$(az identity show -g Lingolou -n lingolou-aks-identity --query principalId -o tsv)
AKS_OIDC_ISSUER=$(az aks show -g Lingolou -n lingolou-aks --query oidcIssuerProfile.issuerUrl -o tsv)
STORAGE_ID=$(az storage account show -n lingoloudisk --query id -o tsv)

# Federated credential: lets the k8s SA exchange its OIDC token for an Azure AD token
az identity federated-credential create -g Lingolou --identity-name lingolou-aks-identity \
  --name lingolou-fed-cred --issuer "$AKS_OIDC_ISSUER" \
  --subject system:serviceaccount:lingolou:lingolou-sa \
  --audiences api://AzureADTokenExchange

# Role for Azure Files (SMB mount)
az role assignment create --assignee "$IDENTITY_PRINCIPAL" \
  --role "Storage File Data SMB Share Contributor" --scope "$STORAGE_ID"

# Role for Azure Blob SAS token generation — MUST be added separately (see session 2)
az role assignment create --assignee "$IDENTITY_PRINCIPAL" \
  --role "Storage Blob Data Contributor" --scope "$STORAGE_ID"
```

**Lesson:** Azure Files (SMB) and Azure Blob are separate RBAC planes. `Storage File Data SMB Share Contributor` grants zero Blob permissions. We missed the Blob role in session 1 and only caught it in session 2 when audio stopped working.

---

### Secrets — namespace must exist first

```bash
# Wrong order: namespace doesn't exist yet
kubectl create secret generic lingolou-secrets -n lingolou ...
# → namespaces "lingolou" not found

# Fix: apply namespace and SA manifests before creating secrets
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/service-account.yaml
# now create secrets
```

All secret values passed as CLI args — never written to disk:
```bash
kubectl create secret docker-registry acr-secret -n lingolou \
  --docker-server=lingolou.azurecr.io --docker-username=lingolou \
  --docker-password="$(az acr credential show -n lingolou --query passwords[0].value -o tsv)"

kubectl create secret generic azure-files-secret -n lingolou \
  --from-literal=azurestorageaccountname=lingoloudisk \
  --from-literal=azurestorageaccountkey="$(az storage account keys list -n lingoloudisk -g Lingolou --query '[0].value' -o tsv)"

kubectl create secret generic lingolou-secrets -n lingolou \
  --from-literal=SESSION_SECRET_KEY="$SESSION_SECRET_KEY" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  ...
```

---

### Redis CrashLoopBackOff

**Symptom:** Redis sidecar container: `bind: Address in use` on port 6379.

**Root cause:** The `latest` image in ACR was built from `main` before the AKS branch was merged. The old `entrypoint.sh` started an embedded Redis inside the app container — so two Redis processes (embedded + sidecar) both tried to bind 6379.

**Fix:** Rebuild and push from the AKS branch (which removed the embedded Redis from entrypoint.sh), then restart:
```bash
az acr login -n lingolou
docker buildx build --platform linux/amd64 \
  -t lingolou.azurecr.io/lingolou-app:aks-v1 \
  -t lingolou.azurecr.io/lingolou-app:latest --push .
kubectl rollout restart deployment/lingolou -n lingolou
```

**Lesson:** Always push a fresh image from the exact branch you're deploying before applying manifests.

---

### ErrImagePull — missing imagePullSecrets

**Symptom:** `401 Unauthorized` pulling from `lingolou.azurecr.io`.

**Fix:** `k8s/deployment.yaml` was missing `imagePullSecrets`. Added:
```yaml
imagePullSecrets:
  - name: acr-secret
```

**Lesson:** Workload identity handles Azure SDK auth inside the pod, but image pull from ACR still needs a separate docker-registry secret referenced in `imagePullSecrets`.

---

### DNS cutover

The existing `www` DNS record was a CNAME pointing to the Container Apps FQDN, not an A record. GoDaddy doesn't let you change a CNAME to an A record in-place — delete and recreate:

1. Delete the CNAME for `www`
2. Add A record: `www` → `57.151.44.179` (TTL 3600)

Verify against the authoritative nameserver (bypasses local cache TTL):
```bash
dig www.lingolou.app A +short @ns35.domaincontrol.com
# → 57.151.44.179  (should be immediate)
```

---

### cert-manager ACME HTTP-01 challenge failing — port 80 unreachable

**Symptom:**
```
Fetching http://www.lingolou.app/.well-known/acme-challenge/...: Timeout during connect (likely firewall problem)
curl --max-time 10 http://57.151.44.179/  # times out from external
```

**Systematic diagnosis — what was ruled out:**
```bash
# NSG — not the problem
az network nsg rule list -g MC_Lingolou_lingolou-aks_eastus \
  --nsg-name aks-agentpool-21866258-nsg -o table
# → allows TCP 80, 443 from Internet ✓

# LB rules — not the problem
az network lb rule list -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes -o table
# → port 80 → nodePort 31962, port 443 → nodePort 31340 ✓

# nginx pod itself — not the problem (works internally)
kubectl run test-curl --image=curlimages/curl --rm -it -- \
  curl http://$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
    -o jsonpath='{.spec.clusterIP}')
# → HTTP 308 ✓ (nginx is alive and responding)

# LB health probe — THIS is the problem
az network lb probe list -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes -o table
# → Protocol=Http, Port=31962, Path="/"
```

**Root cause:** The Azure LB health probe was HTTP, hitting nginx nodePort 31962 at path `/`. Nginx redirects `/` to HTTPS with HTTP 308. Azure HTTP probes require exactly HTTP 200 — a 308 marks the backend **unhealthy**, so the LB silently drops all port 80 traffic even though the LB rules and NSG are correct.

Left as a blocker at end of session 1.

---

## Session 2

### Fixing the LB health probe (three attempts)

**Attempt 1 — TCP protocol annotation (did not work):**
```bash
kubectl annotate svc ingress-nginx-controller -n ingress-nginx \
  "service.beta.kubernetes.io/azure-load-balancer-health-probe-protocol=tcp"
```
The AKS cloud-controller-manager (CCM) is supposed to reconcile service annotations into Azure LB config. It didn't — probe stayed `Http` after 5+ minutes.

**Attempt 2 — Helm upgrade for `/healthz` (partial, then hit annotation conflict):**

The `kubectl annotate` from attempt 1 caused a field manager conflict — Helm uses server-side apply and disputes ownership of fields set by `kubectl`. Remove the annotation first (trailing dash = delete):
```bash
kubectl annotate svc ingress-nginx-controller -n ingress-nginx \
  "service.beta.kubernetes.io/azure-load-balancer-health-probe-protocol-"
```
Then Helm upgrade:
```bash
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --reuse-values \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path=/healthz" \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-port=10254" \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-protocol=http"
```
The CCM updated the probe **path** to `/healthz` but never changed the **port** from 31962 → 10254. Nginx only serves `/healthz` on port 10254 (its own health/metrics port), not on port 80. So probing nodePort 31962 at `/healthz` returned 404 — still unhealthy.

**Attempt 3 — Direct az CLI patch (worked immediately):**
```bash
PROBE_NAME=$(az network lb probe list \
  -g MC_Lingolou_lingolou-aks_eastus --lb-name kubernetes -o json \
  | python3 -c "import sys,json; p=json.load(sys.stdin); \
    print([x['name'] for x in p if '80' in x['name'] and '443' not in x['name']][0])")

az network lb probe update \
  -g MC_Lingolou_lingolou-aks_eastus \
  --lb-name kubernetes --name "$PROBE_NAME" \
  --protocol Http --port 10254 --path "/healthz"
```

nginx-ingress binds port 10254 as a `hostPort` on the node. The Azure LB probes the node IP directly on that port. `/healthz` returns HTTP 200. Port 80 became reachable instantly.

**Lesson — why the CCM annotation for `port` didn't work:** The CCM in this AKS version reliably reconciled path and protocol annotations but silently ignored the probe port annotation. The direct `az` patch bypasses the CCM. The Helm annotations remain on the service, so future CCM reconciliations *should* converge to the right values — but if an AKS upgrade resets the probe, re-run the `az network lb probe update` command.

**Lesson — annotation vs kubectl conflict:** If you manually `kubectl annotate` a field on a resource that Helm manages, Helm's next `upgrade` will fail with a field manager conflict. Always use `helm upgrade --set` for annotations on Helm-managed resources, or remove the manual annotation first (trailing `-` syntax).

---

### Forcing cert-manager to retry after port 80 fix

Once the LB was fixed, the existing ACME Order was in `invalid` state. cert-manager does not auto-retry from `invalid` — you must delete the failed objects:

```bash
kubectl delete certificaterequest -n lingolou --all
# Order is owned by the CR and gets garbage-collected automatically

# Nudge cert-manager to notice the Certificate needs reissuing
kubectl annotate certificate lingolou-tls -n lingolou \
  cert-manager.io/issuer-kind=ClusterIssuer --overwrite
```

cert-manager created a new Order within seconds. The HTTP-01 challenge completed, and the certificate went `READY: True`.

**Lesson:** `kubectl delete certificaterequest --all -n <namespace>` is the standard way to force a cert-manager retry. Deleting only the Order isn't enough because the CR immediately recreates it. Deleting the CR triggers the full issuance flow from scratch.

---

### Audio files not loading — missing Blob RBAC role

**Symptom:** Story pages loaded but no audio. App logs:
```
azure.core.exceptions.HttpResponseError: AuthorizationPermissionMismatch
```
on `get_user_delegation_key()` call.

**Root cause:** The app generates Blob audio URLs as user-delegation SAS tokens — this requires the caller (the workload identity) to have a Blob Data role on the storage account. The workload identity only had `Storage File Data SMB Share Contributor`, which is an Azure Files role and grants zero Blob permissions.

Azure Files and Azure Blob are entirely separate RBAC planes on the same storage account. A role on one has no effect on the other.

**Fix:**
```bash
IDENTITY_PRINCIPAL=$(az identity show -g Lingolou -n lingolou-aks-identity --query principalId -o tsv)
STORAGE_ID=$(az storage account show -n lingoloudisk --query id -o tsv)
az role assignment create \
  --assignee "$IDENTITY_PRINCIPAL" \
  --role "Storage Blob Data Contributor" \
  --scope "$STORAGE_ID"
kubectl rollout restart deployment/lingolou -n lingolou
```

Wait ~1 minute for RBAC to propagate, then verify:
```bash
kubectl exec -n lingolou deployment/lingolou -- python3 -c "
import sys; sys.path.insert(0, '/app')
from webapp.services.storage import get_storage
print(get_storage().get_url('17/ch1.mp3'))
"
# → https://lingoloudisk.blob.core.windows.net/audio/17/ch1.mp3?sv=...
```
Then curl the URL to confirm it returns HTTP 200 with content.

**Lesson:** When setting up workload identity for a storage account that serves both SMB (for SQLite/database) and Blob (for audio/files), assign **both** roles upfront:
- `Storage File Data SMB Share Contributor` — for Azure Files
- `Storage Blob Data Contributor` — for Azure Blob SAS token generation and upload

---

## Current state

- `kubectl get pods -n lingolou` → `2/2 Running`
- `kubectl get certificate -n lingolou` → `READY: True`
- `curl https://www.lingolou.app/health` → `{"status":"healthy","redis":"connected",...}`
- Old Container App still running — decommission once smoke-testing is complete:
  ```bash
  az containerapp delete -n lingolou -g Lingolou
  az containerapp env delete -n lingolou-env -g Lingolou
  ```
