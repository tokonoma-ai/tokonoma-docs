# Set up the Tokonoma Slack app

`@Tokonoma` runs inside your MCP server. It uses Slack Socket Mode, so it can run in a private cluster without a public Slack callback URL or ingress. This is Tokonoma's own app. The separate `@Claude` integration uses Claude's connectors and has different network requirements.

This guide targets chart 0.37.0 and application 0.68.0. Complete the [base installation](install.md) first.

Before changing an existing release, follow [version and configuration checks](upgrading.md). If its versions differ from this guide, resolve that difference before running the pinned command.

## Inputs and files

Run shell commands on the administration workstation used for the [base installation](install.md), from its customer working directory outside this documentation checkout. Replace placeholders before running commands. An agent must ask the operator for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected credential directory chosen during base installation | File-based credentials |
| `slack-app-token.txt` | Socket Mode app token from Slack, saved in the protected directory | This integration |
| `slack-bot-token.txt` | Bot User OAuth Token from Slack, saved in the protected directory | This integration |
| `license.txt` | Tokonoma-issued license, saved during base installation | Helm upgrade |

Keep `tokonoma-values.yaml` and every existing overlay in the customer working directory. This guide creates no additional values file. Keep all existing credential inputs when upgrading. Optional features that call a model also use `anthropic-api-key.txt`; see [memory processing](memory-llm.md).

## Create the app

You need permission to create and install a Slack app, a working Tokonoma database, and permission to update the Helm release. Allow outbound HTTPS to Slack's API at `slack.com:443` and secure WebSocket connections to the Socket Mode URL Slack returns. A proxy must support the WebSocket upgrade. Slack rotates that URL; do not pin one returned URL permanently. See [Slack's Socket Mode documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

1. Open [Slack's app management page](https://api.slack.com/apps), choose **Create New App**, then **From a manifest**.
2. Select your workspace and paste [slack-app-manifest.yaml](../examples/slack-app-manifest.yaml). Review the requested permissions and create the app.
3. Under **Basic Information > App-Level Tokens**, generate a token with the `connections:write` scope. Save the `xapp-` token in your protected token directory as `slack-app-token.txt`.
4. Under **Install App**, install the app to your workspace. Save the **Bot User OAuth Token** (`xoxb-`) as `slack-bot-token.txt`.

The manifest enables Socket Mode, mentions, channel message events, and interactive buttons. You can optionally upload your preferred icon under **Basic Information > Display Information**. For Slack's manifest workflow, see [configuring apps with manifests](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/).

## Connect it to Tokonoma

Use the protected directory from [credentials](credentials.md). Token files must contain only the token, with no final newline. In the customer working directory, add both Slack inputs to your complete installation command:

```sh
chmod 600 "REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt" "REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt"

helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 \
  --namespace tokonoma \
  --reset-then-reuse-values -f tokonoma-values.yaml \
  --set-string mcp.image.tag=0.68.0 \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set-file credentials.slackBotToken="REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt" \
  --set-file credentials.slackAppToken="REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt" \
  --wait --timeout 10m
```

Helm should report release `tokonoma` as `deployed`. Keep every values overlay and credential input already used by your installation. For Slack features that call a model, also include `--set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt"`. If you use existing Secrets, keep those references in `tokonoma-values.yaml` instead of supplying direct token inputs.

In each public or private channel where you want Tokonoma, run `/invite @Tokonoma`. If you enable the runner, create `#tokonoma-investigations` and invite the app there. This is the default channel for results; set `mcp.slack.investigationsChannel` only when you want a different channel name. The app must be a member of that channel.

## Verify the connection

On the administration workstation, read the MCP logs:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deployment/toko-mcp --tail=200
```

Look for `slack socket mode connected`. Then send `@Tokonoma help` in an invited channel and confirm that it replies. Send `@Tokonoma setup` for a readiness report visible only to you. It reports Slack scopes, model availability, and runner readiness when a runner is installed.

| Symptom | Check |
| --- | --- |
| `Slack listener NOT started` | Both tokens and the database must be configured. |
| No reply in one channel | Invite the app to that channel. |
| `missing_scope` | Apply this version's manifest in Slack's **App Manifest** page and reinstall the app. |
| Questions or timelines unavailable | Supply an Anthropic API key and leave `mcp.memoryLlm.enabled: true`; exact commands still work without it. |
| Runner results wait | Invite the app to the configured investigations channel and enable `runner.destinations.slackApp.enabled`. |
| Connection fails behind a proxy | Allow Slack API traffic and Socket Mode WebSocket upgrades. |

Chart-owned `credentials.slack*` changes trigger a rollout during Helm upgrade. After rotating an externally managed token Secret, run this on the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-mcp
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp
```

Expected result: the Deployment successfully rolls out. Repeat the Slack reply check above.

## Choose what to enable

Without an Anthropic key, exact commands such as `help`, `start REPLACE_WITH_SESSION_TITLE`, `state`, `stop`, and `resume` work. Agents can check into a session. Reading `full record for REPLACE_WITH_RECORD_UUID` needs a valid Tokonoma license. Answering questions, judging relevance, and creating session timelines require the Anthropic key and send relevant content to Anthropic.

Automatic memory recall on alerts is off by default. To make the app reply to alerts from other apps, merge this into `tokonoma-values.yaml` and repeat the complete Helm upgrade:

```yaml
mcp:
  slack:
    autoRecallEnabled: true
```

Automatic recall also requires the Slack features that call a model. This switch does not enable automatic investigations. The runner is a separate optional component; with it configured, `runner.destinations.slackApp.enabled: true` delivers investigation results through this app. Avoid also configuring a legacy Slack webhook destination unless you want both deliveries.

## Channel access and shared records

The app receives channel messages where it is invited. It can read channel history for sessions and post shared records into those channels. Its memory identity can access organization-wide records, not an individual user's private records or records shared only with named identity-provider groups. New records are shared with everyone by default; choose private sharing when needed. See [data flows](data-flows.md).

The release manifest requests channel and user read scopes, `chat:write`, `reactions:write`, and `channels:join`. Application 0.68.0 does not automatically join channels; invite it explicitly. It does not request `chat:write.public`, direct-message history, or `files:write`.

Continue with [alert investigations](alert-investigations.md), or return to [integrations](integrations.md).
