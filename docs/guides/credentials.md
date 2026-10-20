# Credentials and license

For chart 0.37.0 and application 0.68.0, prepare the license before [installation](../install.md#2-prepare-your-files). Add credentials for selected features only.

## What you need

| Credential | Where it comes from | Chart input | Needed for |
| --- | --- | --- | --- |
| Tokonoma license | [support@tokonoma.ai](mailto:support@tokonoma.ai) | `mcp.license` | Reading a memory's full body, including full-record reads in Slack and the UI |
| Anthropic API key | Your Anthropic account | `credentials.anthropicApiKey` | Server-side memory analysis, Slack questions and timelines, and the runner when using the Anthropic API |
| Slack bot token (`xoxb-`) | Your Slack app's **Install App** page | `credentials.slackBotToken` | Reading invited channels and posting as `@Tokonoma` |
| Slack app-level token (`xapp-`) | Your Slack app's **Basic Information** page, with `connections:write` | `credentials.slackAppToken` | Slack Socket Mode; supply both Slack tokens together |
| Alertmanager bearer token | Generate a random token and configure the same value in Alertmanager | `credentials.alertmanagerToken` | Authenticating Alertmanager deliveries to an enabled runner |

The MCP server and enabled runner share the Anthropic key unless given separate Secret references. Adding it enables memory analysis by default. Set `mcp.memoryLlm.enabled: false` to disable analysis and model-backed Slack features while retaining the runner's key. See [data flows](../data-flows.md).

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

For optional features, create only the files that their guide requires:

| File | Content and source | Needed when |
| --- | --- | --- |
| `anthropic-api-key.txt` | Issued API key from your Anthropic account | Using the features in the credential table above |
| `slack-bot-token.txt`, `slack-app-token.txt` | Tokens from your Slack app | Following [Slack setup](slack-app.md) |
| `alertmanager-token.txt` | Token shared with your alert sender | Following [Alertmanager setup](alert-investigations.md) |
| `grafana-viewer-token.txt` | Your existing Grafana service-account credential | Enabling the Grafana query adapter |

Apply `chmod 600` to each created file. Agents ask you to save issued credentials and supply their paths, never their contents in chat.

The [base command](../install.md#3-install) needs only `license.txt`. Feature guides supply additional `--set-file` arguments. Save the complete values-file order and credential inputs for upgrades.

`--set-file` keeps tokens out of commands but stores them in Helm release records and Kubernetes Secrets. Restrict access to both. Never commit token files or log rendered Secrets.

## Use existing Kubernetes Secrets

Existing Secrets must be in the release namespace. Replace example names and keys with those supplied by the secret owner. Merge selected sections into `tokonoma-values.yaml`, preserving other settings. References take precedence over direct inputs.

```yaml
mcp:
  licenseSecret:
    name: tokonoma-license
    key: license
  memoryLlm:
    apiKeySecret:
      name: tokonoma-anthropic
      key: apiKey
  slack:
    tokenSecret:
      name: tokonoma-slack
      botTokenKey: botToken
      appTokenKey: appToken

# Include this section only when the runner is enabled.
runner:
  engine:
    apiKeySecret:
      name: tokonoma-anthropic
      key: apiKey
  sources:
    alertmanager:
      tokenSecretRef:
        name: tokonoma-alertmanager
        key: token
```

These references do not create Secrets. Omit unused features. `mcp.memoryLlm.apiKeySecret` does not configure the runner; supply both references when needed.

Selected integration guides cover Datadog tokens and API keys, Grafana credentials, OAuth clients, and storage identities. These do not replace the license or Slack tokens.

## Renew and rotate

Use the verified cluster context. For direct `credentials.*` inputs, update the protected file and rerun the complete Helm upgrade. Chart 0.37.0 automatically restarts consumers of changed Anthropic, Slack, and Alertmanager values.

After changing `mcp.license`, restart MCP and its enabled unattended sibling. Externally managed Secret changes also require consumer restarts. With default component names:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-mcp
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp --timeout=5m
```

When enabled, restart `deployment/toko-mcp-unattended` after license or shared model-key changes, and `deployment/toko-runner` after its credentials change. Use your actual deployment names.

Check license status in the local UI's **Setup** page, or `/usage-stats` through your existing connection. `/usage-stats` requires a token with `toko-mcp/query` when authentication is enabled. It reports usage and reasons such as `absent`, `invalid_signature`, or `expired`. Expiry grace and quota enforcement follow the issued license; refused recalls do not consume usage. Contact [support@tokonoma.ai](mailto:support@tokonoma.ai) to renew.
