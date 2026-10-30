# Set up the Tokonoma Slack app

`@Tokonoma` uses Slack Socket Mode to connect from a private cluster without a public callback URL or ingress. The separate [`@Claude` integration](claude-in-slack.md) has different network requirements.

Create the Slack app and prepare its tokens before [installation](install.md#3-install). For an existing deployment, apply the settings with the [upgrade guide](upgrading.md#before-changing-configuration).

## Create the app

You need permission to create and install a Slack app. Tokonoma does not need to be running yet. Allow outbound HTTPS to Slack's API at `slack.com:443` and secure WebSocket connections to the Socket Mode URL Slack returns. A proxy must support the WebSocket upgrade. Slack rotates that URL; do not pin one returned URL permanently. See [Slack's Socket Mode documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

Follow [credential setup](credentials.md#supply-credentials-in-commands) when supplying the two tokens below.

1. Open [Slack's app management page](https://api.slack.com/apps), choose **Create New App**, then **From a manifest**.
2. Select your workspace and paste [slack-app-manifest.yaml](../examples/slack-app-manifest.yaml). Review the requested permissions and create the app.
3. Under **Basic Information > App-Level Tokens**, generate an `xapp-` token with the `connections:write` scope.
4. Under **Install App**, install the app to your workspace and obtain the **Bot User OAuth Token** (`xoxb-`).

For an existing app, update **App Manifest** with this manifest. Reinstall if the change adds required permissions that are not already granted. Save the current bot token; keep the app-level token unless you are rotating it.

Channel-join welcomes require [Tokonoma v0.78.0](https://github.com/tokonoma-ai/tokonoma-mcp/releases/tag/v0.78.0) or newer. The manifest above includes `member_joined_channel` for new apps. For an existing app, add and save it under **Event Subscriptions > Subscribe to bot events**. Updating Tokonoma alone does not update an existing Slack app's subscriptions. Saving this subscription takes effect without reinstalling when the relevant permission is already granted: `channels:read` for public channels or `groups:read` for private channels. See Slack's [subscription and reinstall rules](https://docs.slack.dev/app-management/distribution/#when-is-a-reinstall-required).

The manifest enables Socket Mode, mentions, membership and channel message events, feedback reactions, report uploads, and interactive buttons. See Slack's [manifest instructions](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/) if needed.

## Save the connection settings

In `values.yaml`, uncomment the Slack settings from the [example](../examples/values.yaml), including `runner.destinations.slackApp.enabled: true` for investigation results. Supply both arguments below in the installation or configuration-change command, filling the token placeholders locally. The [installation example](install.md#3-install) already includes them:

```sh
  --set-literal 'credentials.slackBotToken=REPLACE_WITH_SLACK_BOT_TOKEN' \
  --set-literal 'credentials.slackAppToken=REPLACE_WITH_SLACK_APP_TOKEN'
```

For existing Secrets, use `mcp.slack.tokenSecret` instead of the two Slack arguments.

Choose an existing or new public or private `#tokonoma-investigations` channel for monitoring and runner results. Set `mcp.slack.investigationsChannel` only for a different channel name. Invite the app after it connects, as described below.

For an existing deployment, [apply the configuration change](upgrading.md#before-changing-configuration), including any changed token arguments and preserving other credentials.

## Verify the connection

When Slack is enabled, read the MCP logs on the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deployment/toko-mcp --tail=200
```

Look for `slack socket mode connected`. Add the app to the designated monitoring channel to [receive its welcome](#receive-the-monitoring-welcome), and invite it to other channels where you want to use it. Then send `@Tokonoma help` in an invited channel and confirm that it replies. Send `@Tokonoma admin status` for a readiness report visible only to you. It reports Slack scopes, model availability, and runner readiness. When automatic investigations are enabled, also confirm investigation result delivery with [runner verification](alert-investigations.md#check-it-works).

| Symptom | Check |
| --- | --- |
| `Slack listener NOT started` | Both tokens and the database must be configured. |
| No reply in one channel | Invite the app to that channel. |
| No welcome after adding the app | Check that Tokonoma is v0.78.0 or newer, the `member_joined_channel` subscription is saved, and the app joined the configured monitoring channel after the listener connected. Follow the [welcome checks](#receive-the-monitoring-welcome) below. |
| `missing_scope` | Apply this version's manifest in Slack's **App Manifest** page and reinstall the app. |
| Questions or timelines unavailable | These features require [incident sessions](#optional-incident-sessions). When enabled, supply an Anthropic API key and leave `llm.serverFeatures` unset; see [server model features](server-features.md). |
| Runner results wait | Invite the app to the configured investigations channel and enable `runner.destinations.slackApp.enabled`. |
| Connection fails behind a proxy | Allow Slack API traffic and Socket Mode WebSocket upgrades. |

For token changes, follow [credential rotation](credentials.md#renew-and-rotate), then repeat the Slack reply check above.

### Receive the monitoring welcome

After the listener connects, open the designated monitoring channel and add the installed app. For its default name, use `/invite @Tokonoma`. Only the app's own join to this configured channel triggers the welcome; another person joining or adding the app elsewhere does not.

If a completed monitoring plan is available, Tokonoma posts an introduction first, then the formatted setup report as a second channel message. The full saved plan attaches to the report's thread. The report combines saved setup findings with current monitoring counts and coverage; its date identifies the plan. The attached plan remains a saved snapshot, so its detector statuses may differ from their current enable/disable state.

If setup is incomplete, the saved plan is unavailable, or Tokonoma cannot read or prepare the report, it posts one standalone message containing its introduction and a paragraph saying the report is not ready. That message directs you to `@Tokonoma admin status` to check progress and anything that needs fixing. No report or plan is attached.

If the runner cannot answer, the not-ready message can take about three minutes. A restart or Slack delivery failure can leave the welcome missing. Check `@Tokonoma admin status` and the connection checks above; once the listener is connected, remove and re-add the app to retry.

The welcome does not start monitoring setup or generate a new plan. Later setup and daily reports arrive separately. Restarting Tokonoma does not welcome an app already in the channel, and a missed join does not produce a welcome later.

## Use Tokonoma in a channel

Mention the app in a channel where it has been invited. Run `@Tokonoma help` for the commands supported by your installed version.

With `mcp.slack.multiplayerEnabled: false`, use the exact commands below. Other input, including ordinary questions and incomplete commands, returns help without model interpretation or memory recall.

| Task | Command and expected behavior |
| --- | --- |
| Get help | `@Tokonoma help` lists available commands. |
| Request a monitoring summary | `@Tokonoma monitoring summary` composes a fresh summary for the last 24 hours and posts it in the investigations channel. It does not replace the scheduled daily report. Requests within 10 minutes of the last manual summary, or while one is being composed, are refused. |
| Change detector activity | `@Tokonoma disable detector REPLACE_WITH_DETECTOR_ID` stops future checks; `@Tokonoma enable detector REPLACE_WITH_DETECTOR_ID` starts or resumes them. Copy complete IDs from a report or saved plan; separate multiple IDs with spaces. Review the scope and query before enabling a detector. |
| Investigate an alert | Reply `@Tokonoma investigate` in the alert's thread to send it to the runner. Add a steer, such as `@Tokonoma investigate checkout 502s for EU users`, to specify the symptom. This needs a configured runner and telemetry access. |
| Read the saved result | Click **Full record** on a result or recalled record. Reading the body requires a valid license. |

Recurring findings show how to stop future checks. Use the complete detector IDs in the command, or consult the saved plan for IDs that do not fit.

Use `disable detector` for unwanted or unhelpful monitoring and `enable detector` to resume the same checks. The choice is kept when the detector is carried into a new plan. Repeated commands are safe; obsolete or superseded IDs are unavailable. Work already in flight may finish. Useful or not useful feedback rates an investigation result; it is separate from disabling its detectors.

When multiplayer is enabled, ask ordinary questions with `@Tokonoma <question>` to find relevant saved records. See [Using Tokonoma](using-tokonoma.md) for the investigation workflow and an illustrative result.

### Operator commands

Use `@Tokonoma admin` for operator help. Anyone in an invited channel can run these commands.

| Task | Command and expected behavior |
| --- | --- |
| Check readiness | `@Tokonoma admin status` reports connections, missing access, and runner readiness. Only the requester sees the reply. |
| Run monitoring setup | `@Tokonoma admin replan` requests discovery again. The completed report posts in the investigations channel. |
| Read the monitoring plan | `@Tokonoma admin get plan` attaches the saved monitoring plan in the request's thread without running setup. If no plan is available, it says so. |

The plan includes detector IDs for `enable detector` and `disable detector`. It is a saved setup or refresh snapshot: its statuses may differ from live detector state after those commands.

### Optional incident sessions

Incident coordination is off by default. Enable it with `mcp.slack.multiplayerEnabled`.

The commands and settings in this guide require [application 0.77.0](https://github.com/tokonoma-ai/tokonoma-mcp/releases/tag/v0.77.0) and [chart 0.39.0](https://github.com/tokonoma-ai/tokonoma-charts/releases/tag/v0.39.0) or newer compatible releases. Older application images may ignore the multiplayer setting and expose incident coordination; upgrading only the chart is insufficient.

Remove any `SLACK_MULTIPLAYER_ENABLED` entry from `mcp.extraEnv` and `runner.extraEnv`, preserving other entries. The chart rejects these entries, including matching values and `valueFrom`. If Helm has saved an old list, explicitly replace it with the remaining entries, or `[]` when none remain; deleting a line from the file alone can retain saved values. See [configuration changes](upgrading.md#before-changing-configuration).

To enable incident coordination, set this value in your saved `values.yaml`:

```yaml
mcp:
  slack:
    multiplayerEnabled: true
```

[Apply the configuration change](upgrading.md#before-changing-configuration), then run `@Tokonoma help` to confirm that session commands are listed.

To disable incident coordination, explicitly set `mcp.slack.multiplayerEnabled: false` and apply the configuration change again. Removing the key alone can preserve a saved `true` when Helm reuses values. Confirm that `@Tokonoma help` omits session commands. Requests for those commands return the normal help while coordination is off.

While disabled, incident sessions, timelines, and agent check-ins are unavailable, including the `investigation-session` skill and `get_investigation_session` tool. Existing session data is retained.

Ordinary investigations, saved records, and their outcomes remain available through coding agents. The Slack `investigate` command also remains available.

Existing session-linked investigations can still be edited, resolved, and archived under the normal access rules. Their session information must stay unchanged, and private check-ins cannot be published to a shared session while coordination is off.

| Task | Command and expected behavior when enabled |
| --- | --- |
| Start or rename a session | `@Tokonoma start checkout errors` creates a `TKNM-<N>` session and posts a prompt teammates can give their coding agents to join it. Bare `start` uses recent discussion for a title when available; `set title to <title>` changes the active title. |
| Resume a session | `@Tokonoma resume` reopens the most recent closed session in this channel within 24 hours. `resume TKNM-<N>` selects an older session in its original channel. |
| Review progress | `@Tokonoma state` summarizes the active session; `@Tokonoma timeline` assembles its timeline. Use `timeline TKNM-<N>` for a specific session in this channel. |
| Close and save | `@Tokonoma stop` closes the session. Then `@Tokonoma save` saves the closed session as one investigation; `save TKNM-<N>` selects a specific closed session. |

A Slack session coordinates teammates and their agents. Starting one does not itself start a runner investigation. Follow the handoff prompt to join from a coding agent, or request an investigation in the alert thread.

## Choose what to enable

Questions and session timelines require multiplayer to be enabled. They and automatic alert relevance checks use the required Anthropic key and send relevant content to Anthropic. During an analysis outage, `help` remains available. With incident sessions enabled, exact session commands such as `state`, `stop`, and `resume` also remain available. Full record buttons need a valid Tokonoma license.

Automatic memory recall on alerts is off by default. To make the app reply to alerts from other apps, set `mcp.slack.autoRecallEnabled: true` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration).

Automatic recall is separate from runner investigations. Investigation results use `runner.destinations.slackApp.enabled`. Avoid also configuring a legacy Slack webhook destination unless you want both deliveries.

## Channel access and shared records

The app receives channel messages where it is invited. With incident sessions enabled, it can read channel history for sessions. It can post shared records into invited channels. It can access organization-wide records, not an individual user's private records or records shared only with named identity-provider groups. New records are shared with everyone by default; choose private sharing when needed. See [data flows](data-flows.md).

The manifest requests channel and user read scopes, `chat:write`, `reactions:write`, and `channels:join`. It also uses `reactions:read` for monitoring feedback and `files:write` for setup reports. Tokonoma does not automatically join channels; invite it explicitly. It does not request `chat:write.public` or direct-message history.

Continue with [alert investigations](alert-investigations.md), or return to [integrations](integrations.md).
