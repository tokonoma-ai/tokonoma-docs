# Platform: GKE

Verify persistent storage for GKE. Google Cloud Storage (GCS), telemetry ingestion, and self-monitoring are optional.

Run commands on a workstation with `kubectl`, Helm 3.14+, gcloud and access to the intended cluster and Google Cloud project. Save values in your [installation working directory](../install.md), outside this repository. Replace `REPLACE_WITH_*` inputs; agents must ask for unresolved choices.

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_PROJECT` | Google Cloud project ID from the cluster owner; required only for the optional GCS recipe. |
| `REPLACE_WITH_REGION` | Bucket location selected with the cloud administrator; required only for the optional GCS recipe. |
| `REPLACE_WITH_CUSTOMER` | Optional full-stack organization slug: at most 42 lowercase letters, digits, or hyphens, starting with a letter. |

## Persistent volumes

Check the intended cluster's storage:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass
```

Continue when a StorageClass includes `(default)` and the cluster owner confirms volume provisioning works. Otherwise, PersistentVolumeClaims stay `Pending` and installation times out.

Return to [prepare your installation files](../install.md#2-prepare-your-files). Continue below only if you chose Tokonoma's full telemetry stack with GCS-backed attachments.

## Optional: telemetry, GCS attachments, and self-monitoring

This recipe enables all three features. Telemetry uses `gs://` storage; attachments use `mcp.storage.backend: gcs`. Both use Workload Identity without long-lived keys.

The cluster needs [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity): the `REPLACE_WITH_PROJECT.svc.id.goog` workload pool and GKE metadata server on the node pool. Autopilot enables it by default. Without it, IAM bindings can succeed but pod bucket access fails.

Enable the IAM Service Account Credentials API in the same project:

```sh
gcloud services enable iamcredentials.googleapis.com --project REPLACE_WITH_PROJECT
```

Continue when the command completes successfully.

### 1. Prepare buckets and access

Create telemetry and attachment buckets and a Google Cloud service account. If a name is taken, use a unique name throughout the commands and overlay.

```sh
gcloud storage buckets create gs://REPLACE_WITH_CUSTOMER-tokonoma-indexes gs://REPLACE_WITH_CUSTOMER-tokonoma-attachments \
  --location REPLACE_WITH_REGION --project REPLACE_WITH_PROJECT
gcloud iam service-accounts create tokonoma-sa --project REPLACE_WITH_PROJECT
```

New service accounts can take 60 seconds or more to become available. Check:

```sh
gcloud iam service-accounts describe tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --project REPLACE_WITH_PROJECT --format="value(email)"
```

Continue when the expected account email appears. If not found, wait and retry.

Grant access to both buckets and bind the cloud account to the Kubernetes ServiceAccount:

```sh
gcloud storage buckets add-iam-policy-binding gs://REPLACE_WITH_CUSTOMER-tokonoma-indexes \
  --member serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --role roles/storage.objectAdmin
gcloud storage buckets add-iam-policy-binding gs://REPLACE_WITH_CUSTOMER-tokonoma-attachments \
  --member serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --role roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:REPLACE_WITH_PROJECT.svc.id.goog[tokonoma/tokonoma-sa]" \
  --project REPLACE_WITH_PROJECT
```

Each command must succeed. Bucket policies must show the account under `roles/storage.objectAdmin`; the service-account command reports `Updated IAM policy`. If the account is not found, wait and retry. The chart creates the annotated `tokonoma-sa` Kubernetes ServiceAccount.

### 2. Save the overlay

Save as `tokonoma-full.yaml` in your customer working directory. Use the same bucket names and location as above:

```yaml
customer: REPLACE_WITH_CUSTOMER
region: REPLACE_WITH_REGION
telemetryPlatform: true
objectStorage:
  indexesScheme: gs
  indexesBucket: REPLACE_WITH_CUSTOMER-tokonoma-indexes
  attachmentsBucket: REPLACE_WITH_CUSTOMER-tokonoma-attachments
  serviceAccountName: tokonoma-sa
  serviceAccountCreate: true
  serviceAccountAnnotations:
    iam.gke.io/gcp-service-account: tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com
mcp:
  image:
    tag: "0.68.0"
  storage:
    backend: gcs
otelCollector: { enabled: true }
prometheus:    { enabled: true }
grafana:       { enabled: true }
```

The customer slug determines telemetry index names. Do not set `objectStorage.endpoint`, `flavor`, or `credentialsSecret` for native GCS.

For a first [installation](../install.md#3-install), include this overlay after `tokonoma-values.yaml`. Keep MCP private for verification. The MCP pod serves attachment URLs; set `mcp.domain` for remote clients and configure [OAuth](../guides/oauth.md) before shared or public access.

For an existing installation, follow [upgrade preparation](../guides/upgrading.md), then apply the overlay with existing values and Secret references preserved:

```sh
helm upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context REPLACE_WITH_KUBE_CONTEXT --version 0.37.0 -n tokonoma \
  --reset-then-reuse-values -f tokonoma-values.yaml -f tokonoma-full.yaml \
  --wait --timeout 15m
```

Include other changed overlays. Expect `STATUS: deployed`. Local attachments remain on `toko-mcp-attachments`; this does not migrate them to GCS.

### 3. Verify the optional services

Before startup, MCP checks attachment-bucket write, read, and delete access. If Workload Identity or bucket IAM is not ready, Helm times out after 15 minutes; Kubernetes keeps retrying. Inspect the check:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-mcp -c check-bucket-storage
```

After installation, check the telemetry bucket with the same Workload Identity:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma exec deploy/toko-mcp -c mcp -- \
  env GCS_BUCKET=REPLACE_WITH_CUSTOMER-tokonoma-indexes /app/.venv/bin/toko-mcp-check-attachment-storage
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc
```

Exit status zero confirms bucket write, read, and delete access. Confirm workloads are ready and claims are `Bound`. Complete the [MCP health and memory checks](../install.md#4-verify).

In a separate terminal, leave this running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-grafana 3000:80
```

Once it reports `Forwarding from`, check from another terminal:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/login
```

Expect `200`. If port 3000 is busy, change the mapping’s left side and URL. Open <http://127.0.0.1:3000> as `admin`; retrieve the password privately:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get secret toko-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d
```

Ship OpenTelemetry Protocol (OTLP) data from inside the cluster to `toko-indexer:7281` with headers `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs` and `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces`. See [endpoints](../reference/endpoints.md).

For the `gce` IngressClass and ManagedCertificate flow, see [public MCP](../guides/public-mcp-ingress.md).
