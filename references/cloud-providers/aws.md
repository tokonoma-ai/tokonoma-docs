# AWS (EKS)

Prepare persistent storage for Amazon Elastic Kubernetes Service (EKS). Telemetry ingestion with S3 storage and self-monitoring are optional.

Use `kubectl`, Helm 3.14+, and AWS CLI on a workstation with access to the intended cluster and AWS account. Run commands from your [installation working directory](../install.md), following [input conventions](../install.md#inputs-and-placeholders).

| Input | Source and when required |
|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts`; required for cluster commands. |
| `REPLACE_WITH_CLUSTER`, `REPLACE_WITH_REGION` | EKS cluster name and AWS region from the cluster owner; required for the storage checks. The cloud cluster name may differ from its kubeconfig context. |
| `REPLACE_WITH_ADDON_VERSION` | EBS CSI add-on version selected by the cluster owner; required only when configuring that add-on. |
| `REPLACE_WITH_CUSTOMER` | Telemetry organization slug: at most 42 lowercase letters, digits, or hyphens, starting with a letter. |
| `REPLACE_WITH_IRSA_ROLE_ARN` | Role created for optional S3 access below; required only for that configuration. |

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

Apply Terraform and save the role ARN. The chart creates the annotated ServiceAccount. If a bucket name is taken, choose a unique name and set `objectStorage.indexesBucket` in `values.yaml`.

### 2. Update the values

Merge these settings into `values.yaml`, preserving existing configuration. Use the same region as the bucket:

```yaml
# Used in telemetry index names and the default bucket name.
customer: REPLACE_WITH_CUSTOMER
region: REPLACE_WITH_REGION  # Use the bucket location.
telemetryPlatform: true  # Optional telemetry backend; disabled by default.
objectStorage:
  # Set indexesBucket here if you changed the bucket name in step 1.
  serviceAccountName: tokonoma-sa  # Must match the cloud identity binding.
  serviceAccountCreate: true  # Create the annotated Kubernetes account; default is false.
  serviceAccountAnnotations:
    eks.amazonaws.com/role-arn: REPLACE_WITH_IRSA_ROLE_ARN
# Optional self-monitoring components; all are disabled by default.
otelCollector: { enabled: true }
prometheus:    { enabled: true }
grafana:       { enabled: true }
```

For a first installation, finish preparing `values.yaml` and credentials, then [install Tokonoma](../install.md#3-install) with that file. Keep MCP private during verification; configure [OAuth](../oauth.md) before shared or public access.

For an existing release, [apply the configuration change](../upgrading.md#before-changing-configuration), preserving existing settings and Secret references.

### 3. Verify the optional services

Check workloads, persistent storage, and index creation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc,jobs
```

Confirm workloads are ready and claims are `Bound`. Helm removes the index-creation Job after success; investigate it if it remains and has failed. If telemetry workloads fail, check the S3 bucket and IAM access. Complete the [installation health checks](../install.md#4-verify) and [monitoring and integration checks](../install.md#check-monitoring-and-integrations) for enabled features before phase 1 is complete.

For dashboards, [open the self-monitoring Grafana UI](../endpoints.md#self-monitoring-grafana-ui).

Send OpenTelemetry Protocol (OTLP) data using the [ingest endpoint and headers](../endpoints.md#otlp-ingest). Choose CPU, memory, storage, and retention settings for your workload. Verify capacity with a representative ingestion test.

For the `alb` IngressClass and ACM certificate flow, see [public MCP](../public-mcp-ingress.md).
