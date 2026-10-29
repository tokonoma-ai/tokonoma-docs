# Troubleshooting

Run checks from the installation workstation with its verified context and saved configuration. Examples use `tokonoma` for the release and namespace; replace them if yours differ. Replace other placeholders from the affected resource or setup guide. Start with read-only checks and save the error.

## Public ECR reports an expired token

The chart is public and requires no registry login. Helm or Docker can still use an expired saved credential for a public pull; see [AWS's explanation](https://docs.aws.amazon.com/AmazonECR/latest/public/docker-pull-ecr-image.html).

If you no longer need the saved public-registry login, remove that registry's stored Helm credential:

```sh
helm registry logout public.ecr.aws
```

This removes the workstation's saved login for `public.ecr.aws`; authenticated workflows will need to log in again. Confirm that removing it is within scope. If Docker also stores a login for this registry:

```sh
docker logout public.ecr.aws
```

Use the Docker command only if its stored credential is involved. If the login is still needed, have its owner refresh it instead. If no login exists, investigate another cause.

Retry the public download from the customer working directory:

```sh
helm pull oci://public.ecr.aws/tokonoma/charts/tokonoma
```

Record the chart version and digest Helm prints, and use the archive saved in this directory. If the error remains, contact Tokonoma before changing more credentials. Do not disable TLS verification.

In your complete [installation command](install.md#3-install), replace the OCI URL with the downloaded archive's actual path. Keep `values.yaml` and all selected credential inputs. For an existing release, make the same replacement in the [upgrade command](upgrading.md) instead of running `install` again. See [Helm registry logout](https://helm.sh/docs/helm/helm_registry_logout/) for the credential-removal command.

## Install / upgrade

**Helm times out on `--wait`.** Check pod status: `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods`. Common causes: missing StorageClass, image pull failures (egress to ECR/Docker Hub/`registry.ollama.ai`; add-ons also use `quay.io`/`registry.k8s.io`), or insufficient node resources for the telemetry platform. For Pending PVCs, run `kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass` and confirm one row includes `(default)`, then run `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe pvc REPLACE_WITH_PVC_NAME`. On EKS, follow the [persistent-volume setup](cloud-providers/aws.md#persistent-volumes) to configure the EBS CSI add-on, its IAM role, and a default StorageClass.

**Grafana crash-loops on arm64 nodes.** The pinned Quickwit datasource plugin has no linux-arm64 build and a failed plugin install is fatal to Grafana. Schedule Grafana on an amd64 node, use a newer plugin version, or clear `grafana.env.GF_INSTALL_PLUGINS`.

**`mcp.ingress.enabled=true` fails template render.** Set top-level `domain`, `mcp.domain`, or `mcp.ingress.host`. If `tls.enabled=true`, set `mcp.ingress.tls.secretName`.

**OAuth configuration fails template render.** Enabled OAuth requires
`mcp.auth.baseUrl`, `mcp.domain`, or top-level `domain`, plus at least one
active native machine client, credential provider, or SAML login method. The
standard authenticated local runner provisions its machine client automatically.
This requires the [native-auth releases](upgrading.md#native-machine-authentication-release-prerequisite).
Cognito also requires
`mcp.auth.cognito.userPoolId`; Google requires the configured API key Secret.
In `preregistered_only`, declare at least one active client. Client errors name
the invalid grant, redirect, scope, authentication method, or Secret reference;
the accepted combinations are documented in the [OAuth guide](oauth.md#choose-oauth-client-admission).

## Object storage

**GCS auth failures on GKE.** GKE uses native GCS with Workload Identity (`indexesScheme: gs`). Check that the `tokonoma-sa` Kubernetes service account carries the `iam.gke.io/gcp-service-account` annotation. The Google Cloud service account needs the `roles/iam.workloadIdentityUser` binding for it, and the cluster/node pool must have Workload Identity enabled. See [Google Cloud (GKE)](cloud-providers/google-cloud.md).

**Telemetry index writes return 403 on GKE.** Confirm that the Google Cloud service account has `roles/storage.objectAdmin` on the telemetry bucket. Replace `REPLACE_WITH_BUCKET` with the bucket name from your saved values, normally `REPLACE_WITH_CUSTOMER-tokonoma-indexes`:

```sh
gcloud storage buckets get-iam-policy gs://REPLACE_WITH_BUCKET \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/storage.objectAdmin AND bindings.members:serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com" \
  --format="value(bindings.members)"
```

Expect `serviceAccount:tokonoma-sa@REPLACE_WITH_PROJECT.iam.gserviceaccount.com`. If the result is empty, rerun the bucket binding command in step 1 of the [GKE guide](cloud-providers/google-cloud.md). Check the telemetry search pod logs for the underlying error.

**Telemetry search pods never appear (not even Pending).** The search backend runs as ServiceAccount `tokonoma-sa` by default; Kubernetes will not create pods that reference a missing ServiceAccount. Check `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe rs -l app.kubernetes.io/part-of=tokonoma | grep -A2 Events` for `serviceaccount "tokonoma-sa" not found`. In the recommended cloud-provider values, set `objectStorage.serviceAccountCreate: true`, supply the EKS or GKE identity annotation, and upgrade again. If your cluster manages the ServiceAccount externally, confirm that it exists instead.

**Telemetry search pods crash on install.** Confirm top-level `customer` (or `objectStorage.indexesBucket`) points at an existing bucket and workload identity is configured: IRSA on EKS or Workload Identity on GKE.

## Telemetry ingest

**OTLP rejected / "no shards available" after an old upgrade.** Preserve the error and component logs and contact Tokonoma before changing database state. The current [upgrade guide](upgrading.md#older-installations) does not include a generic shard-deletion repair; the correct recovery depends on the source version and current storage state.

**Indexes not created.** Confirm top-level `customer` is set (or `telemetryIndexes` explicitly). Inspect any remaining index-creation Job with `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get jobs`; Helm removes it after successful completion.

## MCP

**`/health` is not reachable.** This endpoint is a process response and does not probe PostgreSQL. Check the MCP pod status, Service or port-forward, and logs: `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-mcp`. An init container checks PostgreSQL access before startup.

## Ingress

**Certificate not issued (nginx/Traefik).** Confirm the cert-manager `ClusterIssuer` exists and DNS points at the Ingress controller.

**ALB not reachable.** Check `certificate-arn`, security groups, and that `target-type: ip` matches your CNI setup.

**GKE ManagedCertificate stuck.** DNS must point at the Ingress IP before the certificate can be issued. Check `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma describe managedcertificate toko-mcp-cert`.
