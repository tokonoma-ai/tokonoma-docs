# Troubleshooting

Run checks from the installation workstation. Use its verified `REPLACE_WITH_KUBE_CONTEXT`, release, namespace, and saved configuration. Examples use `tokonoma` for release and namespace. Fill any other placeholder from the affected resource or selected guide, not from a guess. Start with read-only checks and retain the actual error.

## Public ECR reports an expired token

The chart is public and does not require an AWS account or registry login. A saved Helm or Docker credential can still be selected for a public pull; AWS documents this [expired-credential behavior](https://docs.aws.amazon.com/AmazonECR/latest/public/docker-pull-ecr-image.html). On macOS, an empty temporary config can also allow Helm to discover the native Keychain helper.

If you no longer need the saved public-registry login, remove that registry's stored Helm credential:

```sh
helm registry logout public.ecr.aws
```

This changes the workstation's saved login for `public.ecr.aws`; an authenticated workflow will need to log in again. An agent must confirm that this change is within the requested scope before removing an existing login. If Docker also stores a login for this registry, AWS documents this direct removal command:

```sh
docker logout public.ecr.aws
```

Use the Docker command only if that client is installed and its stored credential is involved. A message that no login exists is not a successful diagnosis. If you must retain the login, have its owner refresh it through the normal registry workflow instead.

Retry the pinned public download from the customer working directory:

```sh
helm pull oci://public.ecr.aws/tokonoma/charts/tokonoma --version 0.37.0
```

Expect `tokonoma-0.37.0.tgz` and manifest digest `sha256:e719008a626bb929e16f974104de4f99199df1ed9f49cabcbae37e4ebc114fc2`. If the same error remains, preserve it and contact Tokonoma before changing more credentials. Do not disable TLS verification.

The downloaded archive can replace the OCI URL in subsequent commands. For example:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT install tokonoma ./tokonoma-0.37.0.tgz \
  --namespace tokonoma --create-namespace \
  --values tokonoma-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

Include any selected configuration overlays and other credential inputs from your installation plan. For an existing release, use the [upgrade guide](upgrading.md) with the archive path instead of running `install` again. See [Helm registry logout](https://helm.sh/docs/helm/helm_registry_logout/) for the credential-removal command.

## Install / upgrade

**Helm times out on `--wait`.** Check pod status: `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods`. Common causes: missing StorageClass, image pull failures (egress to ECR/Docker Hub/`registry.ollama.ai`; add-ons also use `quay.io`/`registry.k8s.io`), or insufficient node resources for the telemetry platform. For Pending PVCs, run `kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass` and confirm one row includes `(default)`, then run `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe pvc REPLACE_WITH_PVC_NAME`. On EKS, follow the [persistent-volume setup](../platform/eks.md#persistent-volumes) to configure the EBS CSI add-on, its IAM role, and a default StorageClass.

**Grafana crash-loops on arm64 nodes.** The pinned Quickwit datasource plugin has no linux-arm64 build and a failed plugin install is fatal to Grafana. Schedule Grafana on an amd64 node, use a newer plugin version, or clear `grafana.env.GF_INSTALL_PLUGINS`.

**`mcp.ingress.enabled=true` fails template render.** Set top-level `domain`, `mcp.domain`, or `mcp.ingress.host`. If `tls.enabled=true`, set `mcp.ingress.tls.secretName`.

**OAuth configuration fails template render.** Enabled OAuth requires
`mcp.auth.baseUrl`, `mcp.domain`, or top-level `domain`, plus at least one
credential provider or SAML login method. Cognito also requires
`mcp.auth.cognito.userPoolId`; Google requires the configured API key Secret.
In `preregistered_only`, declare at least one active client. Client errors name
the invalid grant, redirect, scope, authentication method, or Secret reference;
the accepted combinations are documented in the [OAuth guide](oauth.md#choose-oauth-client-admission).

## Object storage

**MCP pod is stuck in init with bucket storage.** With `mcp.storage.backend=s3` or `gcs`, the pod runs the MCP application's write, read, and delete preflight against the attachments bucket before MCP starts. Read the error with `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-mcp -c check-bucket-storage`, then verify the bucket name, workload identity or static credentials, and object permissions.

**GCS auth failures on GKE.** GKE uses native GCS with Workload Identity (`indexesScheme: gs` and `mcp.storage.backend=gcs`). Check that the `tokonoma-sa` KSA carries the `iam.gke.io/gcp-service-account` annotation, the GSA has the `roles/iam.workloadIdentityUser` binding for it, and the cluster/node pool has Workload Identity enabled. See [Platform: GKE](../platform/gke.md).

**Attachment uploads return 503 or telemetry index writes return 403 on GKE.** Confirm that the GCP service account has `roles/storage.objectAdmin` on both buckets. Run this command once with `REPLACE_WITH_BUCKET` set to `REPLACE_WITH_CUSTOMER-tokonoma-indexes` and once with it set to `REPLACE_WITH_CUSTOMER-tokonoma-attachments`:

```sh
gcloud storage buckets get-iam-policy gs://REPLACE_WITH_BUCKET \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/storage.objectAdmin AND bindings.members:serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com" \
  --format="value(bindings.members)"
```

Each bucket should print `serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com`. If either result is empty, rerun the failed binding command in step 1 of the [GKE guide](../platform/gke.md). For the underlying error, check `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-mcp` and the telemetry search pod logs.

**Telemetry search pods never appear (not even Pending).** The search backend runs as ServiceAccount `tokonoma-sa` by default; Kubernetes will not create pods that reference a missing SA. Check `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe rs -l app.kubernetes.io/part-of=tokonoma | grep -A2 Events` for `serviceaccount "tokonoma-sa" not found`. In the recommended platform values, set `objectStorage.serviceAccountCreate: true`, supply the EKS or GKE identity annotation, and upgrade again. If your cluster manages the ServiceAccount externally, confirm that it exists instead.

**Telemetry search pods crash on install.** Confirm top-level `customer` (or `objectStorage.indexesBucket`) points at an existing bucket and workload identity is wired: IRSA on EKS or Workload Identity on GKE.

## Telemetry ingest

**OTLP rejected / "no shards available" after an old upgrade.** Preserve the error and component logs and contact Tokonoma before changing database state. The current [upgrade guide](upgrading.md#older-installations) does not include a generic shard-deletion repair; the correct recovery depends on the source version and current storage state.

**Indexes not created.** Confirm top-level `customer` is set (or `telemetryIndexes` explicitly) and the index-creation Job completed: `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get jobs`.

## MCP

**`/health` is not reachable.** This endpoint is a process response and does not probe PostgreSQL or bucket storage. Check the MCP pod status, Service or port-forward, and logs: `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-mcp`. PostgreSQL and bucket access are separate startup gates reported by their init containers.

**Attachments fail on S3.** Verify the AWS bucket policy and `objectStorage.serviceAccountName` for IRSA on EKS, or `objectStorage.credentialsSecret` when using static AWS credentials. If the backend is `local`, keep `mcp.replicaCount` at 1.

## Ingress

**Certificate not issued (nginx/Traefik).** Confirm the cert-manager `ClusterIssuer` exists and DNS points at the Ingress controller.

**ALB not reachable.** Check `certificate-arn`, security groups, and that `target-type: ip` matches your CNI setup.

**GKE ManagedCertificate stuck.** DNS must point at the Ingress IP before the cert provisions. Check `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe managedcertificate toko-mcp-cert`.
