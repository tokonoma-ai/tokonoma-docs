# Credentials and license

Prepare the credentials needed for your [installation](install.md#2-prepare-your-files). Enter their values directly in the command examples, or reuse existing Kubernetes Secrets.

## What you need

| Credential | Where it comes from | Chart input | Needed for |
| --- | --- | --- | --- |
| Tokonoma license | [support@tokonoma.ai](mailto:support@tokonoma.ai) | `mcp.license` | Reading a memory's full body, including full-record reads in Slack and the UI |
| Anthropic API key | Your Anthropic account | `credentials.anthropicApiKey` | Server-side memory analysis, Slack questions and timelines, and the runner |
| Slack bot token (`xoxb-`) | Your Slack app's **Install App** page | `credentials.slackBotToken` | Reading invited channels and posting as `@Tokonoma` |
| Slack app-level token (`xapp-`) | Your Slack app's **Basic Information** page, with `connections:write` | `credentials.slackAppToken` | Slack Socket Mode; supply both Slack tokens together |
| Runner client ID and secret | Dedicated machine client from your [identity provider](oauth.md#1-prepare-the-provider) | `mcp.auth.clients`, `runner.tokoMcp.oauthClientSecretRef`, and `mcp.extraEnv` | When MCP authentication is enabled; see [runner credential setup](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled) |

Add only the credentials required by your selected [telemetry connection](integrations.md#mcp-connections), such as a Grafana Viewer token or a provider's API credentials. Telemetry query access is required while either automatic feature is enabled. Reuse existing working connections and Secrets.

For alert delivery, generate an [Alertmanager receiver token](alert-investigations.md#before-you-start) or prepare the [Datadog token](datadog-alerts.md). The current chart requires at least one receiver token even when no alert sender is configured. In that case, retain the Alertmanager token argument in the installation command and record the sender as **none configured**. A configured receiver does not prove that any sender is connected.

Cluster names, endpoints, provider IDs and scopes are configuration, not additional secrets. Obtain them from the selected service's owner; keep nonsecret settings in `values.yaml`.

The MCP server and runner share the Anthropic key unless you configure separate Secret references. Keep analysis enabled for normal operation. See [analysis maintenance](memory-llm.md#temporarily-stop-analysis) for temporary controls and [data flows](data-flows.md) for what reaches the provider.

A valid Tokonoma license is required for full-body recalls, but not search, saving, or skill discovery. An API key cannot replace it and does not enable the runner.

## What Helm creates

Normal Helm installs generate the bundled PostgreSQL password and, when the Grafana adapter is enabled, its private caller token. You do not need to create either for the standard installation. Helm reuses their existing Secrets on upgrades; these Secrets survive uninstall. Delete them only when intentionally resetting the installation.

The Grafana caller token authenticates the runner to the adapter. It does not replace the customer-supplied Grafana Viewer token. [Offline rendering](#offline-rendering) needs stable credentials supplied separately.

## Supply credentials in commands

Replace credential placeholders directly in the commands on your workstation. Keep the surrounding single quotes. Helm examples use `--set-literal` to preserve each value as an exact string, including commas and backslashes. Kubernetes Secret examples use `--from-literal`. Use one flag per value; follow your shell's quoting rules if a credential contains a single quote.

These commands contain secrets. They can remain in shell history and may be visible in process arguments. Helm also stores direct inputs in release records and Kubernetes Secrets. Use existing Secret references or your organization's secret-management workflow when direct input is unsuitable. Never commit filled commands or log rendered Secrets.

When using an installation agent, replace secret placeholders and run those commands yourself locally. Do not paste secret values or filled commands into chat. The agent can verify the resulting deployment and Secret references without seeing their contents.

Keep credentials in your secret manager and record Secret names and keys with the installation configuration. Existing credential files remain usable with Helm's `--set-file` if that is already your workflow; they are not required by these examples.

## Certificate files

SAML signing certificates and their JSON representation remain files. Choose a directory outside this repository, replace `REPLACE_WITH_SECRET_DIRECTORY` in those examples with its absolute path, and prepare it on your workstation:

```sh
install -d -m 700 "REPLACE_WITH_SECRET_DIRECTORY"
```

## Use existing Kubernetes Secrets

Existing Secrets must be in the release namespace. Replace example names and keys with those supplied by the secret owner. Uncomment the matching Secret references in [values.yaml](../examples/values.yaml), preserving other settings. For license, analysis, Slack, and runner credentials, references override direct inputs. The example notes the separate Grafana precedence rule.

References do not create Secrets. Prepare them before installing, using the namespace check below. `mcp.memoryLlm.apiKeySecret` does not configure the runner; supply both references when sharing that key.

## Prepare the namespace for Secrets

When creating a Secret before the first installation, check the release namespace:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT get namespace tokonoma
```

Reuse it if it exists. Only if the response is `NotFound`, create it:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT create namespace tokonoma
```

Use your assigned namespace if it differs. Permission errors need the cluster owner's help. Create Secrets through the selected integration guide or your secret-management workflow; preserve existing Secrets and their owners.

## Offline rendering

Client-only `helm template` and GitOps rendering cannot look up the [generated Secrets](#what-helm-creates). Supply stable `postgres.auth.password` and `grafanaMcp.auth.token` values with `--set-literal`, or use externally managed Secrets, before rendering. Repeatedly generating new passwords can break an existing installation.

For external references, use `postgres.auth.existingSecret` with `postgres.auth.secretKey`; the [external PostgreSQL example](external-postgres.md#3-save-the-values) shows the shape. Use the commented Secret alternatives in the [values example](../examples/values.yaml). For token changes, follow [credential rotation](#renew-and-rotate). Rendering does not check third-party token permissions; verify the integration after deployment.

## Renew and rotate

For direct inputs, [apply the configuration change](upgrading.md#before-changing-configuration) with a `--set-literal` argument for each changed credential. Changed `credentials.anthropicApiKey`, `credentials.slackBotToken`, `credentials.slackAppToken`, and `credentials.alertmanagerToken` values trigger their consumers' rollouts automatically. Externally managed Secrets require explicit restarts.

Use this table for changes that need a manual restart. Names shown are the defaults; substitute any configured overrides.

| Changed credential | Deployments to restart |
| --- | --- |
| License, including direct `mcp.license` | `toko-mcp`, `toko-mcp-unattended` |
| External Anthropic key | `toko-mcp`, `toko-mcp-unattended`; also `toko-runner` if it uses that Secret |
| External Slack tokens | `toko-mcp` |
| External runner model, MCP, or alert-source credential | `toko-runner` |
| Grafana Viewer token, including direct `grafanaMcp.grafana.apiKey` | `toko-grafana-mcp-server` |
| Grafana adapter caller token | `toko-grafana-mcp-server`, `toko-runner` |

For each affected Deployment, replace `REPLACE_WITH_DEPLOYMENT_NAME` with its name and run:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/REPLACE_WITH_DEPLOYMENT_NAME
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/REPLACE_WITH_DEPLOYMENT_NAME --timeout=5m
```

Expect a successful rollout, then repeat the integration's connection check. Keep the old credential valid until its replacement works where the provider allows overlap. For incoming alert tokens, follow the [Alertmanager](alert-investigations.md#rotate-credentials) or [Datadog](datadog-alerts.md#rotating-the-token) overlap procedure.

The generated Grafana caller token stays unchanged on ordinary upgrades. To rotate it, supply `--set-literal 'grafanaMcp.auth.token=REPLACE_WITH_GRAFANA_CALLER_TOKEN'` on the configuration change, then restart both consumers above. The adapter also needs a restart after its inline Viewer token changes.

Check license status in the local UI's **Setup** page, or `/usage-stats` through your existing connection. `/usage-stats` requires a token with `toko-mcp/query` when authentication is enabled. It reports usage and reasons such as `absent`, `invalid_signature`, or `expired`. Expiry grace and quota enforcement follow the issued license; refused recalls do not consume usage. Contact [support@tokonoma.ai](mailto:support@tokonoma.ai) to renew.
