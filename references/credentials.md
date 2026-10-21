# Credentials and license

Prepare these credentials before [installation](install.md#2-prepare-your-files). Use protected files or existing Kubernetes Secrets.

## What you need

| Credential | Where it comes from | Chart input | Needed for |
| --- | --- | --- | --- |
| Tokonoma license | [support@tokonoma.ai](mailto:support@tokonoma.ai) | `mcp.license` | Reading a memory's full body, including full-record reads in Slack and the UI |
| Anthropic API key | Your Anthropic account | `credentials.anthropicApiKey` | Server-side memory analysis, Slack questions and timelines, and the runner when using the Anthropic API |
| Slack bot token (`xoxb-`) | Your Slack app's **Install App** page | `credentials.slackBotToken` | Reading invited channels and posting as `@Tokonoma` |
| Slack app-level token (`xapp-`) | Your Slack app's **Basic Information** page, with `connections:write` | `credentials.slackAppToken` | Slack Socket Mode; supply both Slack tokens together |
| Alertmanager bearer token | Generate a random token and configure the same value in Alertmanager | `credentials.alertmanagerToken` | Authenticating Alertmanager deliveries to the runner |

The MCP server and runner share the Anthropic key unless you configure separate Secret references. Keep analysis enabled for normal operation. See [analysis maintenance](memory-llm.md#temporarily-stop-analysis) for temporary controls and [data flows](data-flows.md) for what reaches the provider.

A valid Tokonoma license is required for full-body recalls, but not search, saving, or skill discovery. An API key cannot replace it and does not enable the runner.

## Supply tokens from files

Save each raw token in a protected file outside this repository, with no quotes, whitespace, or final newline. Use a secret manager or local editor; keep values out of shell commands.

On the Helm workstation, replace `REPLACE_WITH_SECRET_DIRECTORY` with an approved absolute path. Use it consistently:

```sh
install -d -m 700 "REPLACE_WITH_SECRET_DIRECTORY"
```

Save the issued license as `license.txt`, then restrict that file to your account:

```sh
chmod 600 "REPLACE_WITH_SECRET_DIRECTORY/license.txt"
```

Create the files required by your runner configuration and other selected features:

| File | Content and source | Needed when |
| --- | --- | --- |
| `anthropic-api-key.txt` | Issued API key from your Anthropic account | Required analysis, unless you use an existing Secret |
| `slack-bot-token.txt`, `slack-app-token.txt` | Tokens from your Slack app | Following [Slack setup](slack-app.md) |
| `alertmanager-token.txt` | Token shared with your alert sender | Following [Alertmanager setup](alert-investigations.md) |
| `datadog-webhook-token.txt` | Token shared with Datadog | Following [Datadog setup](datadog-alerts.md) |
| `grafana-viewer-token.txt` | Your existing Grafana service-account credential | Enabling the Grafana query adapter |

Apply `chmod 600` to each created file. Agents ask you to save issued credentials and supply their paths, never their contents in chat.

Keep the protected files, Secret references, and saved configuration for future upgrades.

`--set-file` keeps tokens out of commands but stores them in Helm release records and Kubernetes Secrets. Restrict access to both. Never commit token files or log rendered Secrets.

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

Normal Helm installs generate the bundled PostgreSQL password and Grafana adapter caller token, then reuse their existing Secrets on upgrades. These Secrets survive uninstall; delete them only when intentionally resetting the installation. Client-only `helm template` and GitOps rendering cannot look up those Secrets. Use stable `postgres.auth.password` and `grafanaMcp.auth.token` inputs from protected files, or externally managed Secrets, before rendering. Repeatedly generating new passwords can break an existing installation.

For external references, use `postgres.auth.existingSecret` with `postgres.auth.secretKey`; the [external PostgreSQL example](external-postgres.md#3-save-the-values) shows the shape. Use the commented Secret alternatives in the [values example](../examples/values.yaml). For token changes, follow [credential rotation](#renew-and-rotate). Rendering does not check third-party token permissions; verify the integration after deployment.

## Renew and rotate

For direct file inputs, update the protected file and [apply the configuration change](upgrading.md#before-changing-configuration), including its `--set-file` argument. Changed `credentials.anthropicApiKey`, `credentials.slackBotToken`, `credentials.slackAppToken`, and `credentials.alertmanagerToken` values trigger their consumers' rollouts automatically. Externally managed Secrets require explicit restarts.

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

The generated Grafana caller token stays unchanged on ordinary upgrades. To rotate it, supply `--set-file grafanaMcp.auth.token="REPLACE_WITH_SECRET_DIRECTORY/grafana-caller-token.txt"` on the configuration change, then restart both consumers above. The adapter also needs a restart after its inline Viewer token changes.

Check license status in the local UI's **Setup** page, or `/usage-stats` through your existing connection. `/usage-stats` requires a token with `toko-mcp/query` when authentication is enabled. It reports usage and reasons such as `absent`, `invalid_signature`, or `expired`. Expiry grace and quota enforcement follow the issued license; refused recalls do not consume usage. Contact [support@tokonoma.ai](mailto:support@tokonoma.ai) to renew.
