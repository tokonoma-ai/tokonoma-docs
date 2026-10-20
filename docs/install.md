# Install Tokonoma

Install chart **0.37.0** and application **0.68.0** in an existing Kubernetes cluster. The base includes Tokonoma, PostgreSQL, and Ollama. Integrations and shared access are optional.

Run commands on an authorized workstation using Helm, the Kubernetes package manager; `kubectl`, the cluster client; and `curl`. Replace `REPLACE_WITH_...` inputs first. Agents use verified values and ask for missing inputs.

## Before installing

| Decision | How to resolve it | Effect |
| --- | --- | --- |
| Target and existing deployment | Ask the cluster owner for the intended context; inspect the release below | New release: follow this guide. Existing release: [connect your agent](guides/coding-agents.md), or use [upgrading](guides/upgrading.md) for an intended deployment change. |
| Database | Choose bundled PostgreSQL or have your database owner prepare [external PostgreSQL](guides/external-postgres.md) | Prepare it before installing. Changing the address does not migrate data. |
| Access | Choose a local connection for one operator, [private team access](guides/private-access.md), or [public authenticated access](guides/public-mcp-ingress.md) | The base example is local. Prepare authentication and routing together before exposing a shared endpoint. |
| Optional features | Choose from [integrations](integrations.md); inspect [data flows](data-flows.md) | Install the base first unless a selected guide requires additional preparation. |

Use one release per namespace: component names are fixed. Examples use release and namespace `tokonoma`; substitute assigned names consistently. Do not reuse an unrelated deployment's namespace.

## 1. Check prerequisites

| Input or prerequisite | Where it comes from | Check |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | The kubeconfig context supplied by your cluster administrator | It must identify the intended cluster and account. |
| Helm 3.14 or later, `kubectl`, and `curl` | Your workstation's approved tool installation | `helm version --short`, `kubectl version --client`, and `curl --version` must run. |
| Storage and workload permissions | Your platform team | A default StorageClass must provision PersistentVolumes; the namespace must allow the chart's workloads. |
| Capacity and outbound network access | Your platform team | Review the released chart's resource requests and [network destinations](data-flows.md#network-destinations). |
| Issued license | Your Tokonoma contact | Save it using [credentials and license](guides/credentials.md#supply-tokens-from-files). |

```sh
kubectl config get-contexts REPLACE_WITH_KUBE_CONTEXT
kubectl --context REPLACE_WITH_KUBE_CONTEXT cluster-info
kubectl --context REPLACE_WITH_KUBE_CONTEXT get storageclass
helm version --short
helm --kube-context REPLACE_WITH_KUBE_CONTEXT list --all --namespace tokonoma
```

Confirm the cluster, a `(default)` StorageClass, and no existing `tokonoma` release. If it exists, use the connect or upgrade path above. Permission errors require the cluster owner's help; they do not mean the target is empty.

Check [AWS storage preparation](platform/eks.md#persistent-volumes) or [Google Cloud prerequisites](platform/gke.md) as applicable. Neither requires telemetry. The optional Grafana adapter needs Kubernetes 1.25+.

Inspect the package defaults for resource requests and configuration:

```sh
helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma --version 0.37.0
```

If the registry reports an expired token, follow [registry troubleshooting](guides/troubleshooting.md#public-ecr-reports-an-expired-token), then return here.

## 2. Prepare your files

Work from an existing directory outside this checkout. Save nonsecret values there and credentials in a separate protected directory, outside shared or version-controlled folders.

| Input | Meaning and source | Used by |
| --- | --- | --- |
| `REPLACE_WITH_DOCS_DIRECTORY` | Absolute path to this downloaded repository | Copying the supplied example |
| `REPLACE_WITH_SECRET_DIRECTORY` | Absolute protected directory you chose in the credential guide | Helm reads `license.txt` from this workstation |
| `tokonoma-values.yaml` | Your copy of the base example | Every install or upgrade command |

Copy the base example once, before it contains your changes:

```sh
cp "REPLACE_WITH_DOCS_DIRECTORY/examples/memory-values.yaml" tokonoma-values.yaml
```

Review the YAML. It pins application 0.68.0 and disables public routing and authentication for local access. Any caller who can reach it can use it. Restrict network access and port-forward permissions; configure authentication for shared access.

If you chose an external database, complete its [preparation](guides/external-postgres.md) and save `tokonoma-external-postgres.yaml` before installing. If you chose the optional cloud telemetry stack, prepare `tokonoma-full.yaml` using the platform guide. Authentication and routing guides specify their own files.

Record every values file in order, starting with `tokonoma-values.yaml`, for future changes. Later files override matching keys and replace lists. Store credential references in YAML and values in protected files or Kubernetes Secrets.

## 3. Install

For the base installation with a local license file:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT install tokonoma \
  oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 \
  --namespace tokonoma --create-namespace \
  --values tokonoma-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

For a prepared optional configuration, add its `--values` argument after the base file and before `--set-file`: `--values tokonoma-external-postgres.yaml` for the external database, or `--values tokonoma-full.yaml` for cloud telemetry. Include every selected authentication/routing file in its documented order. If using an existing license Secret, configure its reference as described in [credentials](guides/credentials.md#use-existing-kubernetes-secrets) and omit the license `--set-file` argument.

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

Expect `ok`. This checks process health; license access and integrations need functional checks. Database and object-storage startup checks are separate. See [troubleshooting](guides/troubleshooting.md) for failures.

## 5. Connect and confirm memory access

Follow [Connect a coding agent](guides/coding-agents.md), using `http://127.0.0.1:8000/mcp` for the local path. Keep terminal A open. If you configured shared access, use its authenticated endpoint and complete a real login.

In a new session with the connected agent, ask:

> Save a new test memory titled "Tokonoma installation verification" with the body "Tokonoma installation check. No customer data." Then fetch the full body of that exact record using the identifier returned by the save. Report whether the fetched text matches and include the record identifier.

Require a saved record identifier and matching full body. Search results and health checks are insufficient. The agent must use Tokonoma's tool definitions, not guess arguments.

Optionally run `Run Tokonoma onboard.` to prepare investigation context. Review proposed records and file or hook changes before accepting them; see [onboarding](guides/coding-agents.md#3-onboard-your-coding-agent).

## Add only what you need

| Next task | Guide |
| --- | --- |
| Connect Slack | [Slack app](guides/slack-app.md) |
| Investigate alerts | [Integration choices](integrations.md) |
| Give the team access | [Private access](guides/private-access.md) and [authentication](guides/oauth.md) |
| Change or upgrade this installation | [Upgrading](guides/upgrading.md) |
| Diagnose or remove it | [Troubleshooting](guides/troubleshooting.md), [uninstall](guides/uninstall.md) |

Record the target, versions, values-file order, credential locations without secret values, features, and check results. Verify each optional feature separately.
