# Google Cloud (GKE)

Verify persistent storage for Google Kubernetes Engine (GKE). Telemetry ingestion with Google Cloud Storage (GCS) and self-monitoring are optional.

Run commands on a workstation with `kubectl`, Helm 3.14+, gcloud and access to the intended cluster and Google Cloud project. Keep `values.yaml` in your [installation working directory](../install.md), outside this repository. Replace `REPLACE_WITH_*` inputs; agents must ask for unresolved choices.

For an existing release, resolve `REPLACE_WITH_INSTALLED_CHART_VERSION` using [configuration checks](../upgrading.md#before-changing-configuration). This keeps the installed chart version while changing its settings.

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

Return to [prepare your installation files](../install.md#2-prepare-your-files). Continue below only if you chose Tokonoma's telemetry stack with GCS storage.

## Optional: telemetry and self-monitoring

This recipe adds telemetry with `gs://` storage and self-monitoring. Telemetry uses Workload Identity without long-lived keys.

The cluster needs [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity), with the `REPLACE_WITH_PROJECT.svc.id.goog` workload pool and GKE metadata server on the node pool. Autopilot enables it by default. Without it, IAM bindings can succeed but pod bucket access fails.

Enable the IAM Service Account Credentials API in the same project:

```sh
gcloud services enable iamcredentials.googleapis.com --project REPLACE_WITH_PROJECT
```

Continue when the command completes successfully.

### 1. Prepare the bucket and access

Create a telemetry bucket and a Google Cloud service account. If a name is taken, use a unique name throughout the commands and `values.yaml`.

```sh
gcloud storage buckets create gs://REPLACE_WITH_CUSTOMER-tokonoma-indexes \
  --location REPLACE_WITH_REGION --project REPLACE_WITH_PROJECT
gcloud iam service-accounts create tokonoma-sa --project REPLACE_WITH_PROJECT
```

New service accounts can take 60 seconds or more to become available. Check:

```sh
gcloud iam service-accounts describe tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --project REPLACE_WITH_PROJECT --format="value(email)"
```

Continue when the expected account email appears. If the account is not found, wait and retry.

Grant access to the bucket and bind the cloud account to the Kubernetes ServiceAccount:

```sh
gcloud storage buckets add-iam-policy-binding gs://REPLACE_WITH_CUSTOMER-tokonoma-indexes \
  --member serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --role roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:REPLACE_WITH_PROJECT.svc.id.goog[tokonoma/tokonoma-sa]" \
  --project REPLACE_WITH_PROJECT
```

Check that each command succeeds. The bucket policy must show the account under `roles/storage.objectAdmin`; the service-account command reports `Updated IAM policy`. If the account is not found, wait and retry. The chart creates the annotated `tokonoma-sa` Kubernetes ServiceAccount.

### 2. Update the values

Merge these settings into `values.yaml`, preserving the required services and other configuration. Use the same bucket name and location as above:

```yaml
# Used in telemetry index names and the default bucket name.
customer: REPLACE_WITH_CUSTOMER
region: REPLACE_WITH_REGION  # Use the bucket location.
telemetryPlatform: true  # Optional telemetry backend; disabled by default.
objectStorage:
  # Native GCS uses Workload Identity; omit endpoint, flavor and credentialsSecret.
  indexesScheme: gs
  indexesBucket: REPLACE_WITH_CUSTOMER-tokonoma-indexes
  serviceAccountName: tokonoma-sa  # Must match the cloud identity binding.
  serviceAccountCreate: true  # Create the annotated Kubernetes account; default is false.
  serviceAccountAnnotations:
    iam.gke.io/gcp-service-account: tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com
# Optional self-monitoring components; all are disabled by default.
otelCollector: { enabled: true }
prometheus:    { enabled: true }
grafana:       { enabled: true }
```

For a first installation, finish preparing `values.yaml` and credentials, then [install Tokonoma](../install.md#3-install) with that file. Keep MCP private for verification and configure [OAuth](../oauth.md) before shared or public access.

For an existing installation, follow [upgrade preparation](../upgrading.md), then apply the updated `values.yaml` with existing settings and Secret references preserved:

```sh
helm upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context REPLACE_WITH_KUBE_CONTEXT --version REPLACE_WITH_INSTALLED_CHART_VERSION -n tokonoma \
  --reset-then-reuse-values --values values.yaml \
  --wait --timeout 15m
```

Include any changed credential inputs. Expect `STATUS: deployed`.

### 3. Verify the optional services

Check workloads, persistent storage, and index creation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc,jobs
```

Confirm workloads are ready and claims are `Bound`. Helm removes the index-creation Job after success; investigate it if it remains and has failed. If telemetry workloads fail, check Workload Identity and bucket access. Complete the [installation health checks](../install.md#4-verify). [Monitoring and integration checks](../install.md#check-monitoring-and-integrations) are optional follow-ups.

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

Ship OpenTelemetry Protocol (OTLP) data from inside the cluster to `toko-indexer:7281` with headers `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs` and `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces`. See [endpoints](../endpoints.md).

For the `gce` IngressClass and ManagedCertificate flow, see [public MCP](../public-mcp-ingress.md).
