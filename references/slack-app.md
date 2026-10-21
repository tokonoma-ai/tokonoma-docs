# Set up the Tokonoma Slack app

`@Tokonoma` runs inside your MCP server. It uses Slack Socket Mode, so it can run in a private cluster without a public Slack callback URL or ingress. This is Tokonoma's own app. The separate `@Claude` integration uses Claude's connectors and has different network requirements.

Create the Slack app and prepare its tokens before [installation](install.md#3-install). For an existing deployment, apply the settings with the [upgrade guide](upgrading.md#before-changing-configuration).

## Inputs and files

Run shell commands on the administration workstation used for [installation](install.md), from its customer working directory outside this documentation checkout. Replace placeholders before running commands. An agent must ask the operator for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected credential directory chosen in [credentials](credentials.md) | File-based credentials |
| `slack-app-token.txt` | Socket Mode app token from Slack, saved in the protected directory | This integration |
| `slack-bot-token.txt` | Bot User OAuth Token from Slack, saved in the protected directory | This integration |

Keep all settings in your working `values.yaml`. Preserve existing settings and credential inputs when upgrading. Slack questions and timelines use the required `anthropic-api-key.txt`; see [memory analysis](memory-llm.md).

## Create the app

You need permission to create and install a Slack app. Tokonoma does not need to be running yet. Allow outbound HTTPS to Slack's API at `slack.com:443` and secure WebSocket connections to the Socket Mode URL Slack returns. A proxy must support the WebSocket upgrade. Slack rotates that URL; do not pin one returned URL permanently. See [Slack's Socket Mode documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

1. Open [Slack's app management page](https://api.slack.com/apps), choose **Create New App**, then **From a manifest**.
2. Select your workspace and paste [slack-app-manifest.yaml](../examples/slack-app-manifest.yaml). Review the requested permissions and create the app.
3. Under **Basic Information > App-Level Tokens**, generate a token with the `connections:write` scope. Save the `xapp-` token in your protected token directory as `slack-app-token.txt`.
4. Under **Install App**, install the app to your workspace. Save the **Bot User OAuth Token** (`xoxb-`) as `slack-bot-token.txt`.

The manifest enables Socket Mode, mentions, channel message events, and interactive buttons. You can optionally upload your preferred icon under **Basic Information > Display Information**. For Slack's manifest workflow, see [configuring apps with manifests](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/).

## Save the connection settings

Use the protected directory from [credentials](credentials.md). Token files must contain only the token, with no final newline:

```sh
chmod 600 "REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt" "REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt"
```

In `values.yaml`, uncomment the Slack settings from the [example](../examples/values.yaml) and set `runner.destinations.slackApp.enabled: true` for investigation results. Include both token files in the complete install or upgrade command: `--set-file credentials.slackBotToken="REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt"` and `--set-file credentials.slackAppToken="REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt"`. For existing Secrets, use `mcp.slack.tokenSecret` in `values.yaml` instead of these direct inputs.

In each public or private channel where you want Tokonoma, run `/invite @Tokonoma`. Create `#tokonoma-investigations` and invite the app there for runner results. This is the default results channel; set `mcp.slack.investigationsChannel` only for a different channel name.

After preparing all selected integrations, [install Tokonoma](install.md#3-install) once. For an existing deployment, [apply the configuration change](upgrading.md#before-changing-configuration). Keep the license, required analysis key, source token, and other selected credentials in that command.

## Verify the connection

These connection checks are optional follow-ups after installation. Read the MCP logs on the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deployment/toko-mcp --tail=200
```

Look for `slack socket mode connected`. Then send `@Tokonoma help` in an invited channel and confirm that it replies. Send `@Tokonoma setup` for a readiness report visible only to you. It reports Slack scopes, model availability, and runner readiness. You can test investigation delivery separately with [runner verification](alert-investigations.md#check-it-works).

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

Automatic memory recall on alerts is off by default. To make the app reply to alerts from other apps, set `mcp.slack.autoRecallEnabled: true` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration).

Automatic recall also requires the Slack features that call a model. This switch does not configure the required runner. Set `runner.destinations.slackApp.enabled: true` in the [runner setup](alert-investigations.md) to deliver investigation results through this app. Avoid also configuring a legacy Slack webhook destination unless you want both deliveries.

## Channel access and shared records

The app receives channel messages where it is invited. It can read channel history for sessions and post shared records into those channels. Its memory identity can access organization-wide records, not an individual user's private records or records shared only with named identity-provider groups. New records are shared with everyone by default; choose private sharing when needed. See [data flows](data-flows.md).

The release manifest requests channel and user read scopes, `chat:write`, `reactions:write`, and `channels:join`. Tokonoma does not automatically join channels; invite it explicitly. It does not request `chat:write.public`, direct-message history, or `files:write`.

Continue with [alert investigations](alert-investigations.md), or return to [integrations](integrations.md).
