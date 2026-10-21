# AWS (EKS)

Prepare persistent storage for Amazon Elastic Kubernetes Service (EKS). Telemetry ingestion with S3 storage and self-monitoring are optional.

Run commands on a workstation with `kubectl`, Helm 3.14+, AWS CLI and access to the intended cluster and AWS account. Save values in your [installation working directory](../install.md), outside this repository. Replace `REPLACE_WITH_*` inputs; agents must ask for unresolved choices.

Before running Helm, resolve `REPLACE_WITH_INSTALLED_CHART_VERSION` using [configuration checks](../upgrading.md#before-changing-configuration). This keeps the installed chart version while changing its settings.

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_CLUSTER`, `REPLACE_WITH_REGION` | EKS cluster name and AWS region from the cluster owner; required for the storage checks. |
| `REPLACE_WITH_ADDON_VERSION` | EBS CSI add-on version selected by the cluster owner; required only when configuring that add-on. |
| `REPLACE_WITH_CUSTOMER` | Optional full-stack organization slug: at most 42 lowercase letters, digits, or hyphens, starting with a letter. |
| `REPLACE_WITH_IRSA_ROLE_ARN` | Role created for optional S3 access below; required only for that overlay. |

## Persistent volumes

This procedure targets standard EKS on EC2 nodes. EKS Auto Mode manages its own storage controller, and EBS-backed volumes cannot run on Fargate-only nodes. Follow the [AWS EBS CSI guidance](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) for your cluster mode.

Manage the EBS CSI driver and its AWS IAM access with the cluster. The Tokonoma chart does not install or remove them.

First check that volume provisioning works and a default StorageClass exists. If both checks pass, [prepare your installation files](../install.md#2-prepare-your-files). Otherwise, configure the missing storage infrastructure below.

In the Terraform that owns the EKS cluster:

1. Create the EBS CSI IAM role and attach `AmazonEBSCSIDriverPolicyV2`. Use the trust policy in the AWS guide above.
2. Create an `aws_eks_addon` for `aws-ebs-csi-driver` and set its `service_account_role_arn` to that role.
3. Check the selected add-on version’s supported settings:

```sh
aws eks describe-addon-configuration --addon-name aws-ebs-csi-driver \
  --addon-version REPLACE_WITH_ADDON_VERSION --region REPLACE_WITH_REGION
```

If the returned schema supports `defaultStorageClass.enabled`, set `configuration_values = jsonencode({ defaultStorageClass = { enabled = true } })`. Otherwise create a suitable default StorageClass through your cluster-management workflow.

Apply the Terraform through that workflow, then check the add-on and storage:

```sh
aws eks describe-addon --cluster-name REPLACE_WITH_CLUSTER \
  --addon-name aws-ebs-csi-driver --region REPLACE_WITH_REGION \
  --query 'addon.status' --output text
kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass
```

Continue when the add-on reports `ACTIVE` and a StorageClass includes `(default)`. Without volume provisioning, PersistentVolumeClaims stay `Pending` and installation times out.

Return to [prepare your installation files](../install.md#2-prepare-your-files). Continue below only if you chose Tokonoma's telemetry stack with S3 storage.

## Optional: telemetry and self-monitoring

This recipe adds telemetry with S3 storage and self-monitoring. Grafana requires **amd64 nodes** because the pinned Quickwit datasource plugin has no linux-arm64 build. On Graviton-only groups, Grafana crash-loops; see [troubleshooting](../troubleshooting.md).

### 1. Prepare S3 and IAM access

In the Terraform that owns the customer environment, create:

1. The cluster IAM OpenID Connect (OIDC) provider used by IAM roles for service accounts (IRSA).
2. An S3 bucket named `REPLACE_WITH_CUSTOMER-tokonoma-indexes` in `REPLACE_WITH_REGION`.
3. An object-storage IAM policy with bucket-level `ListBucket` and `GetBucketLocation`, plus object-level read, write, delete, and multipart-upload access to the bucket.
4. An IRSA role trusted by `system:serviceaccount:tokonoma:tokonoma-sa`, with that policy attached.

Apply Terraform and save the role ARN. The chart creates the annotated ServiceAccount. If a bucket name is taken, choose a unique name and set `objectStorage.indexesBucket` in the overlay.

### 2. Save the overlay

Save as `tokonoma-full.yaml` in your customer working directory. Use the same region as the bucket:

```yaml
customer: REPLACE_WITH_CUSTOMER
region: REPLACE_WITH_REGION
telemetryPlatform: true
objectStorage:
  serviceAccountName: tokonoma-sa
  serviceAccountCreate: true
  serviceAccountAnnotations:
    eks.amazonaws.com/role-arn: REPLACE_WITH_IRSA_ROLE_ARN
otelCollector: { enabled: true }
prometheus:    { enabled: true }
grafana:       { enabled: true }
```

The customer slug determines index and default bucket names. Telemetry uses `tokonoma-sa` for S3 access.

For a first [installation](../install.md#3-install), include this overlay after `tokonoma-values.yaml`. Keep MCP private during verification; configure [OAuth](../oauth.md) before shared or public access.

For an existing installation, follow [upgrade preparation](../upgrading.md), then apply the overlay with existing values and Secret references preserved:

```sh
helm upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --kube-context REPLACE_WITH_KUBE_CONTEXT --version REPLACE_WITH_INSTALLED_CHART_VERSION -n tokonoma \
  --reset-then-reuse-values -f tokonoma-values.yaml -f tokonoma-full.yaml \
  --wait --timeout 15m
```

Include other changed overlays. Expect `STATUS: deployed`.

### 3. Verify the optional services

Check workloads, persistent storage, and index creation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc,jobs
```

Confirm workloads are ready and claims are `Bound`. Helm removes the index-creation Job after success; investigate it if it remains and has failed. If telemetry workloads fail, check the S3 bucket and IAM access. Complete the [MCP health and memory checks](../install.md#4-verify), then the required [runner setup and verification](../install.md#6-configure-and-verify-the-runner).

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

Ship OpenTelemetry Protocol (OTLP) data from inside the cluster to `toko-indexer:7281` with headers `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs` and `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces`. See [endpoints](../endpoints.md). Choose CPU, memory, storage, and retention settings for your workload. Verify capacity with a representative ingestion test.

For the `alb` IngressClass and ACM certificate flow, see [public MCP](../public-mcp-ingress.md).
