# Install Tokonoma

Install Tokonoma in an existing Kubernetes cluster using one `values.yaml`. The example includes the required MCP service, memory analysis, and runner, with agentic monitoring and automatic investigations enabled. The chart also installs PostgreSQL and Ollama.

The command below uses Anthropic and Alertmanager. Slack is optional. Choose your actual [integrations](integrations.md) before installing; the YAML includes commented sections for them.

Run commands on an authorized workstation using Helm, the Kubernetes package manager; `kubectl`, the cluster client; and `curl`. Follow the [input conventions](#inputs-and-placeholders) before running commands.

## Before installing

| Decision | How to resolve it | Effect |
| --- | --- | --- |
| Target and existing deployment | Ask the cluster owner for the intended context; inspect the release below | New release: follow this guide. Existing release: [connect your agent](coding-agents.md), or use [upgrading](upgrading.md) for an intended deployment change. |
| Database | Choose bundled PostgreSQL or have your database owner prepare [external PostgreSQL](external-postgres.md) | Prepare it before installing. Changing the address does not migrate data. |
| Access | Choose a local connection for one operator, [private team access](private-access.md), or [public authenticated access](public-mcp-ingress.md) | The example starts with a local connection. Set up authentication and routing before exposing a shared endpoint. |
| Analysis, monitoring, and investigations | Prepare an Anthropic API key; it serves both analysis and the runner. Choose the runner's alert sources and telemetry tools using [integrations](integrations.md). Set the monitored cluster and namespaces using [agentic monitoring](agentic-monitoring.md); inspect [data flows](data-flows.md) | Monitoring makes model and telemetry calls after startup. Prepare access and scope before running Helm. |
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
helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma
```

The chart's defaults mention Bedrock, Vertex, and Foundry through `runner.extraEnv`. Tokonoma supports only the Anthropic API, so do not configure these.

If the registry reports an expired token, follow [registry troubleshooting](troubleshooting.md#public-ecr-reports-an-expired-token), then return here.

## 2. Prepare your files

Work from an existing directory outside this checkout. Save nonsecret values there and credentials in a separate protected directory, outside shared or version-controlled folders.

### Inputs and placeholders

Replace every `REPLACE_WITH_...` marker, including those inside paths and URLs. Edit commands directly; do not use shell exports or wrappers. Keep quotes around paths. Agents use verified values and ask for missing decisions or credential paths, never secret contents.

| Input | Meaning and source | Used by |
| --- | --- | --- |
| `REPLACE_WITH_DOCS_DIRECTORY` | Absolute path to this downloaded repository, including `references/` and `examples/` | Copying the supplied example |
| `REPLACE_WITH_SECRET_DIRECTORY` | Absolute protected directory you chose in the credential guide | Helm reads the license and selected credential files from this workstation |
| `values.yaml` | Your saved or supplied customer configuration, completed using the example and chart defaults | Every install or upgrade command |

Read YAML comments for settings and each guide's tables for provider inputs. Obtain identifiers from the provider or its administrator. Use hostnames your organization controls; `example.com` is illustrative. Keep provider template variables such as Datadog's `$ID` and `$TOKONOMA_TOKEN` intact.

### Merge supplied configuration

Read any supplied README and supporting files first. For an existing installation, start with its saved configuration. For a new installation with supplied customer values, add required or selected settings from the [commented example](../examples/values.yaml) only where the customer values and selected chart's defaults do not already satisfy them. Keep settings that can use chart defaults omitted; do not load the entire example as a base values layer.

Customer choices take precedence over examples. Preserve explicit `false`, `0`, `null`, `""`, and `[]`; they are not omitted fields. Ask about missing required inputs, `REPLACE_WITH_...` markers, and conflicts, including explicitly disabled required components. Merge mappings by key without duplicating YAML keys; lists replace rather than append. For an existing installation, merge only the requested changes into its saved configuration and preserve values-file order, ensuring list replacements retain unrelated integrations.

Supporting deployment files remain separate inputs. Use their configured routes, resource names, and Secret references to adapt the relevant guides and commands, preserving existing alert destinations and ownership of resources managed outside Helm. Review the resulting nonsecret values and intended changes before applying them. Supplied equivalents replace guide examples. An instruction to uncomment a setting means add or keep that configuration when it is selected. Do not enable a second webhook route or expose MCP when a separate route is already supplied.

Only when there are no supplied or existing values files, copy the example to your working directory:

```sh
cp "REPLACE_WITH_DOCS_DIRECTORY/examples/values.yaml" values.yaml
```

Summarize the configured integrations, list the remaining [supported options](integrations.md), and ask whether the customer would like to add any. Read the comments in `values.yaml`, fill missing monitoring inputs, and configure only selected additions. Keep credentials in protected files or existing Secrets.

1. Prepare the [license and credentials](credentials.md). One Anthropic API key serves both analysis and the runner.
2. Prepare [runner credentials and investigation tools](alert-investigations.md#before-you-start). Select at least one alert source and configure [monitoring](agentic-monitoring.md) with telemetry query access and the intended cluster and namespaces. For Datadog, follow its [token setup](datadog-alerts.md) before installation; alert delivery and query access are separate.
3. If Slack is selected, use the [Slack app guide](slack-app.md#create-the-app) to prepare any missing app, tokens, or channel access, and configure Slack delivery in `values.yaml`.
4. Merge any [external database](external-postgres.md), [authentication](oauth.md), [routing](public-mcp-ingress.md), or cloud telemetry settings into the same file. Complete their prerequisites first. Configure authentication before sharing access.

Keep the commented source files for future changes; `helm get values` does not retain comments. Merge any further snippets using the same rules above.

## 3. Install

Install after the required credentials and selected integrations are ready. Without `--version`, Helm selects the latest stable chart; the chart currently defaults to the application image tag `latest`:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT install tokonoma \
  oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --namespace tokonoma --create-namespace \
  --values values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt" \
  --set-file credentials.alertmanagerToken="REPLACE_WITH_SECRET_DIRECTORY/alertmanager-token.txt" \
  --wait --timeout 10m
```

Use only the credential inputs for your choices. Existing Secret references replace their matching `--set-file` arguments. For Datadog-only alerts, omit the Alertmanager token and retain the Datadog Secret reference. With Slack selected, add `--set-file credentials.slackBotToken="REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt"` and `--set-file credentials.slackAppToken="REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt"`, or use the Slack Secret reference. If Grafana is enabled, add `--set-file grafanaMcp.grafana.apiKey="REPLACE_WITH_SECRET_DIRECTORY/grafana-viewer-token.txt"` or use its existing Secret option. Keep the analysis credential in every complete installation.

Expect status `deployed`. Diagnose timeouts before retrying; do not uninstall to bypass errors. Helm stores the license in release metadata and a Secret. Restrict access to both.

## 4. Verify

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods,pvc
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp --timeout=10m
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp-unattended --timeout=10m
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-runner --timeout=10m
```

Expect ready pods and Bound persistent-volume claims (PVCs). In **terminal A**, start a local connection and leave it running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-mcp 8000:8000
```

After it reports `Forwarding from`, run this in **terminal B**:

```sh
curl -fsS http://127.0.0.1:8000/health
```

Expect `ok`. Installation is complete when Helm reports `deployed`, required workloads are ready, PVCs are Bound, and this health check passes. See [troubleshooting](troubleshooting.md) for failures.

Monitoring setup continues in the background. Do not wait for setup, evaluation results, or a completed investigation to finish installation. Record the target, versions, saved configuration, credential locations without secret values, monitoring scope, and deployment health. Also record whether end-to-end telemetry access has been validated. Until a follow-up check shows it, report it as not yet validated. This is information and does not block completion.

## After installation

Use the guides below to connect clients and alert senders when needed. Feature tests are optional follow-ups and do not block installation completion.

### Connect and confirm memory access

Follow [Connect a coding agent](coding-agents.md), using `http://127.0.0.1:8000/mcp` for the local path. Keep terminal A open. If you configured shared access, use its authenticated endpoint and complete a real login.

In a new session with the connected agent, ask:

> Save a new test memory titled "Tokonoma installation verification" with the body "Tokonoma installation check. No customer data." Then fetch the full body of that exact record using the identifier returned by the save. Report whether the fetched text matches and include the record identifier.

Require a saved record identifier and matching full body. Search results and health checks are insufficient. The agent must use Tokonoma's tool definitions, not guess arguments.

Optionally run `Run Tokonoma onboard.` to prepare investigation context. Review proposed records and file or hook changes before accepting them; see [onboarding](coding-agents.md#3-onboard-your-coding-agent).

### Check monitoring and integrations

Check [analysis configuration](memory-llm.md) and [monitoring setup and coverage](agentic-monitoring.md#verify-monitoring), then verify the runner with your selected integrations.

1. Complete the [Slack connection checks](slack-app.md#verify-the-connection) if enabled.
2. Add the selected [Alertmanager](alert-investigations.md#wire-up-alertmanager) or [Datadog](datadog-alerts.md) sender configuration after the receiver is ready. Preserve existing paging routes.
3. Complete the runner guide's [verification](alert-investigations.md#check-it-works): send one approved test alert and confirm the completed investigation, saved record, and configured result delivery.

Report any follow-up checks you perform separately from deployment health. Mark untested integrations as unverified; monitoring can still be setting up while the installation is running.

## Next steps

| Next task | Guide |
| --- | --- |
| Configure additional connections | [Integration choices](integrations.md) |
| Give the team access | [Private access](private-access.md) and [authentication](oauth.md) |
| Change or upgrade this installation | [Upgrading](upgrading.md) |
| Diagnose or remove it | [Troubleshooting](troubleshooting.md), [uninstall](uninstall.md) |
