# Install Tokonoma

Install chart **0.37.0** and application **0.68.0** in an existing Kubernetes cluster. Tokonoma requires its MCP service and investigation runner. Steps 1 through 5 prepare the base services, including PostgreSQL and Ollama. Step 6 configures and verifies the required runner.

This walkthrough uses Slack for investigation results. Before starting, arrange permission to install the Slack app and obtain the tokens listed in [Slack setup](slack-app.md#inputs-and-files).

Run commands on an authorized workstation using Helm, the Kubernetes package manager; `kubectl`, the cluster client; and `curl`. Replace `REPLACE_WITH_...` inputs first. Agents use verified values and ask for missing inputs.

## Before installing

| Decision | How to resolve it | Effect |
| --- | --- | --- |
| Target and existing deployment | Ask the cluster owner for the intended context; inspect the release below | New release: follow this guide. Existing release: [connect your agent](coding-agents.md), or use [upgrading](upgrading.md) for an intended deployment change. |
| Database | Choose bundled PostgreSQL or have your database owner prepare [external PostgreSQL](external-postgres.md) | Prepare it before installing. Changing the address does not migrate data. |
| Access | Choose a local connection for one operator, [private team access](private-access.md), or [public authenticated access](public-mcp-ingress.md) | The base example uses a local connection. Set up authentication and routing before exposing a shared endpoint. |
| Runner | Choose your alert sources, model provider, and investigation tools using [integrations](integrations.md); inspect [data flows](data-flows.md) | Gather credentials before starting. Complete runner setup in step 6. |
| Additional features | Choose Slack features, authentication, or cloud telemetry as needed | Follow any preparation required by the selected guide. |

Use one release per namespace: component names are fixed. Examples use release and namespace `tokonoma`; substitute assigned names consistently. Do not reuse an unrelated deployment's namespace.

## 1. Check prerequisites

| Input or prerequisite | Where it comes from | Check |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | The kubeconfig context supplied by your cluster administrator | It must identify the intended cluster and account. |
| Helm 3.14 or later, `kubectl`, and `curl` | Your workstation's approved tool installation | `helm version --short`, `kubectl version --client`, and `curl --version` must run. |
| Storage and workload permissions | Your platform team | A default StorageClass must provision PersistentVolumes; the namespace must allow the chart's workloads. |
| Capacity and outbound network access | Your platform team | Review the released chart's resource requests and [network destinations](data-flows.md#network-destinations). |
| Issued license | Your Tokonoma contact | Save it using [credentials and license](credentials.md#supply-tokens-from-files). |

```sh
kubectl config get-contexts REPLACE_WITH_KUBE_CONTEXT
kubectl --context REPLACE_WITH_KUBE_CONTEXT cluster-info
kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass
helm version --short
helm --kube-context REPLACE_WITH_KUBE_CONTEXT list --all --namespace tokonoma
```

Confirm the cluster, a `(default)` StorageClass, and no existing `tokonoma` release. If it exists, use the connect or upgrade path above. Permission errors require the cluster owner's help; they do not mean the target is empty.

Check [AWS storage preparation](cloud-providers/aws.md#persistent-volumes) or [Google Cloud prerequisites](cloud-providers/google-cloud.md) as applicable. Neither requires telemetry. The optional Grafana adapter needs Kubernetes 1.25+.

Inspect the package defaults for resource requests and configuration:

```sh
helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma --version 0.37.0
```

If the registry reports an expired token, follow [registry troubleshooting](troubleshooting.md#public-ecr-reports-an-expired-token), then return here.

## 2. Prepare your files

Work from an existing directory outside this checkout. Save nonsecret values there and credentials in a separate protected directory, outside shared or version-controlled folders.

| Input | Meaning and source | Used by |
| --- | --- | --- |
| `REPLACE_WITH_DOCS_DIRECTORY` | Absolute path to this downloaded repository | Copying the supplied example |
| `REPLACE_WITH_SECRET_DIRECTORY` | Absolute protected directory you chose in the credential guide | Helm reads `license.txt` from this workstation |
| `tokonoma-values.yaml` | Your copy of the base example | Every install or upgrade command |

Copy the base example once, before it contains your changes. It prepares the services needed by the runner; step 6 supplies the runner configuration:

```sh
cp "REPLACE_WITH_DOCS_DIRECTORY/examples/memory-values.yaml" tokonoma-values.yaml
```

Review the YAML. It pins application 0.68.0 and uses `mcp.storage.backend: none`. Public routing and authentication are disabled for local access. Any caller who can reach it can use it. Restrict network access and port-forward permissions; configure authentication for shared access.

If you chose an external database, complete its [preparation](external-postgres.md) and save `tokonoma-external-postgres.yaml` before installing. If you chose the optional cloud telemetry stack, prepare `tokonoma-full.yaml` using the platform guide. Authentication and routing guides specify their own files.

Keep a list of every values file in order, starting with `tokonoma-values.yaml`, for future changes. Later files override matching keys and replace lists. Store credential references in YAML and values in protected files or Kubernetes Secrets.

## 3. Install

First install the base services with a local license file. Continue through step 6 to complete the installation:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT install tokonoma \
  oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 \
  --namespace tokonoma --create-namespace \
  --values tokonoma-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

For a prepared optional configuration, add its `--values` argument after the base file and before `--set-file`: `--values tokonoma-external-postgres.yaml` for the external database, or `--values tokonoma-full.yaml` for cloud telemetry. Include every selected authentication/routing file in its documented order. If using an existing license Secret, configure its reference as described in [credentials](credentials.md#use-existing-kubernetes-secrets) and omit the license `--set-file` argument.

Expect status `deployed`. Diagnose timeouts before retrying; do not uninstall to bypass errors. Helm stores the license in release metadata and a Secret. Restrict access to both.

## 4. Verify

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp --timeout=10m
```

Expect ready pods and Bound persistent-volume claims (PVCs). In **terminal A**, start a local connection and leave it running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-mcp 8000:8000
```

After it reports `Forwarding from`, run this in **terminal B**:

```sh
curl -fsS http://127.0.0.1:8000/health
```

Expect `ok`. This confirms the process is responding. Database startup, license access, and integrations need their own checks. See [troubleshooting](troubleshooting.md) for failures.

## 5. Connect and confirm memory access

Follow [Connect a coding agent](coding-agents.md), using `http://127.0.0.1:8000/mcp` for the local path. Keep terminal A open. If you configured shared access, use its authenticated endpoint and complete a real login.

In a new session with the connected agent, ask:

> Save a new test memory titled "Tokonoma installation verification" with the body "Tokonoma installation check. No customer data." Then fetch the full body of that exact record using the identifier returned by the save. Report whether the fetched text matches and include the record identifier.

Require a saved record identifier and matching full body. Search results and health checks are insufficient. The agent must use Tokonoma's tool definitions, not guess arguments.

Optionally run `Run Tokonoma onboard.` to prepare investigation context. Review proposed records and file or hook changes before accepting them; see [onboarding](coding-agents.md#3-onboard-your-coding-agent).

## 6. Configure and verify the runner

The runner is required. Chart `0.37.0` defaults `runner.enabled` to `false`; the runner guide enables it together with its credentials and dedicated MCP instance.

1. Set up the [Tokonoma Slack app](slack-app.md) for the result delivery used by these guides.
2. Follow [runner setup](alert-investigations.md) with your selected model provider and investigation tools. Use the Grafana example only if you use Grafana. For Datadog alerts, follow the [Datadog guide](datadog-alerts.md) alongside the runner prerequisites; webhook setup and query access are separate.
3. Complete the runner guide's [verification](alert-investigations.md#check-it-works): send one approved test alert and confirm the completed investigation, saved record, and result in Slack. Preserve existing paging routes.

Record the target, versions, values-file order, credential locations without secret values, integrations, and check results. Installation is complete when both the memory check and runner investigation check pass.

## Next steps

| Next task | Guide |
| --- | --- |
| Configure additional connections | [Integration choices](integrations.md) |
| Give the team access | [Private access](private-access.md) and [authentication](oauth.md) |
| Change or upgrade this installation | [Upgrading](upgrading.md) |
| Diagnose or remove it | [Troubleshooting](troubleshooting.md), [uninstall](uninstall.md) |

Verify each additional feature separately.
