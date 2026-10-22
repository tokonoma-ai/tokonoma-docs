# Install Tokonoma

Install Tokonoma in an existing Kubernetes cluster using one `values.yaml`. The example includes the required MCP service, memory analysis, and runner, with agentic monitoring and automatic investigations enabled. The chart also installs PostgreSQL and Ollama.

Follow the [installation walkthrough](../README.md#2-install-tokonoma), including Slack. Ask whether the customer wants either automatic feature disabled; follow [feature choices](#choose-automatic-features) and preserve existing opt-outs. The command below uses Anthropic and Alertmanager. Choose your actual [integrations](integrations.md) before installing; the YAML includes commented sections for them.

Run commands on an authorized workstation using Helm, the Kubernetes package manager; `kubectl`, the cluster client; and `curl`. Follow the [input conventions](#inputs-and-placeholders) before running commands.

## Before installing

| Decision | How to resolve it | Effect |
| --- | --- | --- |
| Target and existing deployment | Ask the cluster owner for the intended context; inspect the release below | New release: follow this guide. Existing release: [connect your agent](coding-agents.md), or use [upgrading](upgrading.md) for an intended deployment change. |
| Database | Use bundled PostgreSQL for the standard installation. Prepare [external PostgreSQL](external-postgres.md) only when your organization requires it | Helm creates the bundled database credentials. Changing an existing database address does not migrate data. |
| Access | Use a local operator connection. For shared access, follow [authentication](oauth.md) and [team access](private-access.md) | New installations keep MCP inside the cluster with authentication disabled. Preserve supplied or existing authentication. |
| Analysis, monitoring, and investigations | Prepare an Anthropic API key; it serves both analysis and the runner. Choose the runner's alert sources and telemetry tools using [integrations](integrations.md). Set the monitored cluster and namespaces using [agentic monitoring](agentic-monitoring.md); inspect [data flows](data-flows.md) | Both automatic features require telemetry query access. Prepare access before running Helm; monitoring also needs its scope. |
| Additional features | Choose code access or cloud telemetry storage as needed | Follow any preparation required by the selected guide. |

Use one release per namespace: component names are fixed. Examples use release and namespace `tokonoma`; substitute assigned names consistently. Do not reuse an unrelated deployment's namespace.

## 1. Check prerequisites

| Input or prerequisite | Where it comes from | Check |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | The kubeconfig context supplied by your cluster administrator | It must identify the intended cluster and account. |
| Helm 3.14 or later, `kubectl`, and `curl` | Your workstation's approved tool installation | `helm version --short`, `kubectl version --client`, and `curl --version` must run. |
| Storage and workload permissions | Your platform team | A default StorageClass must provision PersistentVolumes; the namespace must allow the chart's workloads. |
| Capacity and outbound network access | Your platform team | Review the released chart's resource requests and [network destinations](data-flows.md#network-destinations). |
| Issued license | Your Tokonoma contact | Have it ready for the [installation command](#3-install). |

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

Work from an existing directory outside this checkout. Save nonsecret settings in `values.yaml`; enter credentials directly in commands or use existing Kubernetes Secret references.

### Inputs and placeholders

Replace every `REPLACE_WITH_...` marker, including those inside paths and URLs. Edit commands directly; do not use shell exports or wrappers. Keep quotes around paths and credential values. If an agent is helping, fill secret placeholders and run those commands locally; do not paste secrets into chat. See [credential input](credentials.md#supply-credentials-in-commands).

| Input | Meaning and source | Used by |
| --- | --- | --- |
| `REPLACE_WITH_DOCS_DIRECTORY` | Absolute path to this downloaded repository, including `references/` and `examples/` | Copying the supplied example |
| Credential placeholders | License, keys, and tokens from their providers or owners | Replace directly in the command examples on your workstation |
| `values.yaml` | Your saved or supplied customer configuration, completed using the example and chart defaults | Every install or upgrade command |

Read YAML comments for settings and each guide's tables for provider inputs. Obtain identifiers from the provider or its administrator. Use hostnames your organization controls; `example.com` is illustrative. Keep provider template variables such as Datadog's `$ID` and `$TOKONOMA_TOKEN` intact.

### Choose automatic features

Enable Agentic Monitoring and automatic investigations by default for new installations. Ask whether the customer wants either disabled. For supplied or existing values, call out disabled features and preserve those choices unless the customer asks to change them. Keep the runner and its dedicated MCP instance enabled.

- To turn off Agentic Monitoring, set `runner.detection.enabled: false` and remove unused scope placeholders. Alert investigations can still run.
- To pause automatic investigations, follow [pause automatic investigations](alert-investigations.md#pause-automatic-investigations). This pauses investigations from alerts and monitoring findings; monitoring checks can remain enabled.

Telemetry query access is required while either feature stays enabled. Resolve missing access before installing. If the customer turns both off, telemetry setup can wait until they enable one. Alert-source credentials remain required by the chart even when automatic investigations are paused.

### Merge supplied configuration

Read any supplied README and supporting files first. For an existing installation, start with its saved configuration. For a new installation with supplied customer values, add required or selected settings from the [commented example](../examples/values.yaml) only where the customer values and selected chart's defaults do not already satisfy them. Keep settings that can use chart defaults omitted; do not load the entire example as a base values layer.

Customer choices take precedence over examples. Preserve explicit `false`, `0`, `null`, `""`, and `[]`; they are not omitted fields. Ask about missing required inputs, `REPLACE_WITH_...` markers, and conflicts, including explicitly disabled required components. Merge mappings by key without duplicating YAML keys; lists replace rather than append. For an existing installation, merge only the requested changes into its saved configuration and preserve values-file order, ensuring list replacements retain unrelated integrations.

Supporting deployment files remain separate inputs. Use their configured routes, resource names, and Secret references to adapt the relevant guides and commands, preserving existing alert destinations and ownership of resources managed outside Helm. Review the resulting nonsecret values and intended changes before applying them.

Only when there are no supplied or existing values files, copy the example to your working directory:

```sh
cp "REPLACE_WITH_DOCS_DIRECTORY/examples/values.yaml" values.yaml
```

Summarize the configured integrations, list the remaining [supported options](integrations.md), and ask whether the customer would like to add any. Read the comments in `values.yaml`, fill missing monitoring inputs, and configure only selected additions. Keep raw credentials out of `values.yaml`; use command inputs or existing Secrets.

1. Prepare the [license and credentials](credentials.md). One Anthropic API key serves both analysis and the runner.
2. Prepare [investigation tools and alert-source credentials](alert-investigations.md#before-you-start). Identify your alert senders, or record **none configured**; the current chart still requires a receiver token in either case. Prepare telemetry query access when either automatic feature is enabled, and the intended cluster and namespaces for [monitoring](agentic-monitoring.md) when enabled. For Datadog, follow its [token setup](datadog-alerts.md) before installation; alert delivery and query access are separate.
3. If Slack is selected, use the [Slack app guide](slack-app.md#create-the-app) to prepare any missing app, tokens, or channel access, and configure Slack delivery in `values.yaml`.
4. Merge any selected [external database](external-postgres.md) or cloud telemetry settings into the same file. Preserve supplied or existing authentication and its [runner credentials](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled).

Keep the commented source files for future changes; `helm get values` does not retain comments. Merge any further snippets using the same rules above.

## 3. Install

Install after the required credentials and selected integrations are ready. Without `--version`, Helm selects the latest stable chart; the chart currently defaults to the application image tag `latest`:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT install tokonoma \
  oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --namespace tokonoma --create-namespace \
  --values values.yaml \
  --set-literal 'mcp.license=REPLACE_WITH_LICENSE' \
  --set-literal 'credentials.anthropicApiKey=REPLACE_WITH_ANTHROPIC_API_KEY' \
  --set-literal 'credentials.alertmanagerToken=REPLACE_WITH_ALERTMANAGER_TOKEN' \
  --set-literal 'credentials.slackBotToken=REPLACE_WITH_SLACK_BOT_TOKEN' \
  --set-literal 'credentials.slackAppToken=REPLACE_WITH_SLACK_APP_TOKEN' \
  --wait --timeout 10m
```

Use only the credential inputs for your choices. Existing Secret references replace their matching `--set-literal` arguments. For Datadog-only alerts, omit the Alertmanager token and retain the Datadog Secret reference. Omit both Slack arguments if Slack is disabled or uses an existing Secret. If Grafana is enabled, add `--set-literal 'grafanaMcp.grafana.apiKey=REPLACE_WITH_GRAFANA_VIEWER_TOKEN'` or use its existing Secret option. Keep the analysis credential in every complete installation.

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

Expect `ok`. Helm status `deployed`, ready workloads, Bound PVCs, and this response complete the deployment health checks. Continue with monitoring and integrations below. See [troubleshooting](troubleshooting.md) for failures.

Record the target, versions, saved configuration, credential locations without secret values, monitoring scope, and deployment health. Record disabled features and evidence from the checks below. Do not describe telemetry access as verified until a check actually queries it.

### Check monitoring and integrations

Check [analysis configuration](memory-llm.md), then complete these checks for enabled features:

1. Confirm [monitoring setup and coverage](agentic-monitoring.md#verify-monitoring): setup completed for the intended scope, checks are active, and evaluation counters advance. Report inactive or degraded checks as coverage gaps.
2. Complete the [Slack connection checks](slack-app.md#verify-the-connection) if enabled.
3. Connect each selected [Alertmanager](alert-investigations.md#wire-up-alertmanager) or [Datadog](datadog-alerts.md) sender after the receiver is ready. Preserve existing paging routes.
4. Follow [investigation verification](alert-investigations.md#check-it-works) with a real alert or approved source-side test. Confirm accepted delivery, a completed automatic investigation, its saved record, and configured Slack delivery. Do not create a production anomaly to test monitoring.

Report incomplete setup, unconnected senders, and unverified investigations as blockers. If no sender is configured, report **none configured**; an unused receiver token does not verify delivery. Record explicit customer opt-outs separately.

## Shared engineer access

Configure [MCP authentication](oauth.md), including the [runner's machine login](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled), before sharing access. Follow [team access](private-access.md) for the shared hostname, route, and human sign-in. Verify the runner still completes investigations, then complete a real login from the chosen coding agent.

### Connect and confirm memory access

This standalone memory check is optional. Follow [Connect a coding agent](coding-agents.md) using the chosen endpoint. An operator can also use `http://127.0.0.1:8000/mcp` with terminal A open.

In a new session with the connected agent, ask:

> Save a new test memory titled "Tokonoma installation verification" with the body "Tokonoma installation check. No customer data." Then fetch the full body of that exact record using the identifier returned by the save. Report whether the fetched text matches and include the record identifier.

Require a saved record identifier and matching full body. Search results and health checks are insufficient. The agent must use Tokonoma's tool definitions, not guess arguments.

Optionally run `Run Tokonoma onboard.` to prepare investigation context. Review proposed records and file or hook changes before accepting them; see [onboarding](coding-agents.md#3-onboard-your-coding-agent).

## Next steps

| Next task | Guide |
| --- | --- |
| Configure additional connections | [Integration choices](integrations.md) |
| Give the team access | [Private access](private-access.md) and [authentication](oauth.md) |
| Change or upgrade this installation | [Upgrading](upgrading.md) |
| Diagnose or remove it | [Troubleshooting](troubleshooting.md), [uninstall](uninstall.md) |
