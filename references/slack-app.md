# Set up the Tokonoma Slack app

`@Tokonoma` runs inside your MCP server. Slack Socket Mode lets it connect from a private cluster without a public callback URL or ingress. The separate [`@Claude` integration](claude-in-slack.md) has different network requirements.

Create the Slack app and prepare its tokens before [installation](install.md#3-install). For an existing deployment, apply the settings with the [upgrade guide](upgrading.md#before-changing-configuration).

## Create the app

You need permission to create and install a Slack app. Tokonoma does not need to be running yet. Allow outbound HTTPS to Slack's API at `slack.com:443` and secure WebSocket connections to the Socket Mode URL Slack returns. A proxy must support the WebSocket upgrade. Slack rotates that URL; do not pin one returned URL permanently. See [Slack's Socket Mode documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

Follow [credential setup](credentials.md#supply-credentials-in-commands) when supplying the two tokens below.

1. Open [Slack's app management page](https://api.slack.com/apps), choose **Create New App**, then **From a manifest**.
2. Select your workspace and paste [slack-app-manifest.yaml](../examples/slack-app-manifest.yaml). Review the requested permissions and create the app.
3. Under **Basic Information > App-Level Tokens**, generate an `xapp-` token with the `connections:write` scope.
4. Under **Install App**, install the app to your workspace and obtain the **Bot User OAuth Token** (`xoxb-`).

For an existing app, update **App Manifest** with this manifest. Reinstall if the change adds required permissions that are not already granted. Save the current bot token; keep the app-level token unless you are rotating it.

For channel-join welcomes, add and save `member_joined_channel` under **Event Subscriptions > Subscribe to bot events**. This requires an application build containing [the channel-join welcome change](https://github.com/tokonoma-ai/tokonoma-mcp/issues/1442). Updating the application or repository manifest alone does not update an existing Slack app's subscriptions. Saving this subscription takes effect without reinstalling when the relevant permission is already granted: `channels:read` for public channels or `groups:read` for private channels. See Slack's [subscription and reinstall rules](https://docs.slack.dev/app-management/distribution/#when-is-a-reinstall-required).

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
| No welcome after adding the app | Check the application build, `member_joined_channel` subscription, configured channel name, and that the listener was connected when the app joined. |
| `missing_scope` | Apply this version's manifest in Slack's **App Manifest** page and reinstall the app. |
| Questions or timelines unavailable | These features require [incident sessions](#optional-incident-sessions). When enabled, supply an Anthropic API key and leave `mcp.memoryLlm.enabled: true`. |
| Runner results wait | Invite the app to the configured investigations channel and enable `runner.destinations.slackApp.enabled`. |
| Connection fails behind a proxy | Allow Slack API traffic and Socket Mode WebSocket upgrades. |

For token changes, follow [credential rotation](credentials.md#renew-and-rotate), then repeat the Slack reply check above.

### Receive the monitoring welcome

After the listener connects, open the designated monitoring channel and add the installed app. For its default name, use `/invite @Tokonoma`. Only the app's own join to this configured channel triggers the welcome; another person joining or adding the app elsewhere does not.

If a completed saved monitoring report and plan are available, the welcome posts an introduction first, then the formatted setup report as a second channel message. The full saved plan attaches to the report's thread. The card uses saved setup findings with current monitoring counts and coverage, using the existing report title/date. The document is a saved snapshot: detector statuses may differ from their current enable/disable state. Otherwise the welcome directs you to mention the app with `admin status` for the current status and next steps. The same response is used if the report cannot be read or prepared.

The welcome uses the same runner request path as `admin get plan`. If the runner cannot answer, the generic response can take about three minutes. Like ordinary plan requests, a crash after the request is consumed can lose the response. Delivery uses the same cached channel lookup as ordinary reports; it discards a welcome if its original join channel differs from the resolved destination.

The welcome does not start monitoring setup or produce a fresh report. Later setup and daily reports arrive through their normal delivery path, not as a promised reply to the welcome. Restarting the application does not welcome an app already in the channel. Removing and re-adding it after the listener connects can produce another welcome; a missed join event is not replayed.

## Use Tokonoma in a channel

Mention the app in a channel where it has been invited. Run `@Tokonoma help` for the commands supported by your installed version.

With `mcp.slack.multiplayerEnabled: false`, mentions run only supported exact commands. Unknown commands, incomplete or malformed commands, and ordinary questions return normal help without model interpretation or memory recall. The normal help contains only these five entries:

- `help` shows available commands
- `investigate` or `investigate <what to look into>` asks Tokonoma to investigate an alert; use this command in an alert’s Slack thread
- `monitoring summary` requests a fresh monitoring report for the last 24 hours
- `enable detector <detector_id; separate multiple IDs with spaces>` turns detectors on
- `disable detector <detector_id; separate multiple IDs with spaces>` stops future checks until you enable them again

| Task | Command and expected behavior |
| --- | --- |
| Request a monitoring summary | `@Tokonoma monitoring summary` composes a fresh summary for the last 24 hours and posts it in the investigations channel. It does not replace the scheduled daily report. Requests within 10 minutes of the last manual summary, or while one is being composed, are refused. |
| Change detector activity | `@Tokonoma disable detector REPLACE_WITH_DETECTOR_ID` stops future checks; `@Tokonoma enable detector REPLACE_WITH_DETECTOR_ID` starts or resumes them. Copy complete IDs from a report or saved plan; use `enable detector <detector_id; separate multiple IDs with spaces>` or `disable detector <detector_id; separate multiple IDs with spaces>`. Review its scope and query before enabling it. |
| Investigate an alert | Reply `@Tokonoma investigate` in the alert's thread to send it to the runner. Add a steer, such as `@Tokonoma investigate checkout 502s for EU users`, to specify the symptom. This needs a configured runner and telemetry access. |
| Read the saved result | Click **Full record** on a result or recalled record. Reading the body requires a valid license. |

In scheduled and requested summaries, each Recurring finding and any **Full record** button appear before the `disable detector` command. The command appears in a code block below the italic text "To stop future checks for this detector:" (or "these detectors" for multiple IDs). Use the complete detector IDs shown in that command; consult the full plan for IDs that do not fit.

Use `disable detector` for unwanted or unhelpful monitoring and `enable detector` to resume the same checks. The choice is kept when the detector is carried into a new plan. Repeated commands are safe; obsolete or superseded IDs are unavailable. Work already in flight may finish. Useful or not useful feedback rates an investigation result; it is separate from disabling its detectors.

When multiplayer is enabled, ask ordinary questions with `@Tokonoma <question>` to find relevant saved records. See [Using Tokonoma](using-tokonoma.md) for the investigation workflow and an illustrative result.

### Operator commands

Use `@Tokonoma admin` for operator help. These commands run in invited channels with no additional permission check. Normal help, setup reports, refresh reports, and daily summaries do not advertise them. The admin help contains:

- `admin` shows this help
- `admin status` shows what is connected and what needs attention; only you see it
- `admin get plan` attaches the full current monitoring plan
- `admin replan` runs monitoring discovery and builds a new plan

| Task | Command and expected behavior |
| --- | --- |
| Check readiness | `@Tokonoma admin status` reports connections, missing access, and runner readiness. Only the requester sees the reply. |
| Run monitoring setup | `@Tokonoma admin replan` requests discovery again. The completed report posts in the investigations channel. |
| Read the monitoring plan | `@Tokonoma admin get plan` attaches the full saved current plan document with a short label in the request's thread, without running setup. If no current plan is available, it says so. |

The plan includes detector IDs for `enable detector` and `disable detector`. It is a saved setup or refresh snapshot: its statuses may differ from live detector state after those commands.

### Optional incident sessions

With compatible chart and application builds, Slack multiplayer incident coordination is off by default. The single chart setting `mcp.slack.multiplayerEnabled` applies to the primary MCP service, its unattended sibling, and the runner. MCP and the runner each enforce the setting.

Use [application 0.77.0](https://github.com/tokonoma-ai/tokonoma-mcp/releases/tag/v0.77.0) and [chart 0.39.0](https://github.com/tokonoma-ai/tokonoma-charts/releases/tag/v0.39.0) or newer compatible releases for the help, command replies, summary format, and multiplayer setting described here. These public releases include the exact-command behavior and concise summary controls. Application 0.76.0 does not include those follow-up changes. Older application images may ignore the flag and expose incident coordination; a chart change alone does not enforce it.

Remove any `SLACK_MULTIPLAYER_ENABLED` entry from `mcp.extraEnv` and `runner.extraEnv`, preserving other entries. The chart rejects these entries, including matching values and `valueFrom`. If Helm has saved an old list, explicitly replace it with the remaining entries, or `[]` when none remain; deleting a line from the file alone can retain saved values. See [configuration changes](upgrading.md#before-changing-configuration).

To enable incident coordination, set this value in your saved `values.yaml`:

```yaml
mcp:
  slack:
    multiplayerEnabled: true
```

[Apply the configuration change](upgrading.md#before-changing-configuration), then run `@Tokonoma help` to confirm that session commands are listed.

To disable incident coordination, explicitly set `mcp.slack.multiplayerEnabled: false` and apply the configuration change again. Removing the key alone can preserve a saved `true` when Helm reuses values. Confirm that `@Tokonoma help` omits session commands. Requests for those commands return the normal help while coordination is off.

While disabled, session lookup, agent check-ins, progress updates, discussion tracking, expiry, and timelines do not run. The `investigation-session` skill and `get_investigation_session` tool are unavailable. The runner does not receive coordination instructions and refuses requests to join a `TKNM-<N>` session. Session cleanup and metadata backfills also stop; session tables remain installed and existing data is not deleted.

Ordinary investigations, memory reads and writes, and saved outcomes remain available through coding agents. In Slack, use the supported exact commands while coordination is off. You can still mark an investigation `resolved`, `dead_end`, or `wont_fix` and save its `resolution_summary`. The Slack `investigate` command still requests an ordinary runner investigation.

Existing session-linked investigations can still be edited, resolved, and archived under the ordinary memory rules. Keep their session metadata exactly unchanged, including older formats. These updates do not access coordination tables. Adding, changing, or removing session metadata, or publishing a private check-in into a shared session, is refused while coordination is off.

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

The app receives channel messages where it is invited. With incident sessions enabled, it can read channel history for sessions. It can post shared records into invited channels. Its memory identity can access organization-wide records, not an individual user's private records or records shared only with named identity-provider groups. New records are shared with everyone by default; choose private sharing when needed. See [data flows](data-flows.md).

The manifest requests channel and user read scopes, `chat:write`, `reactions:write`, and `channels:join`. It also uses `reactions:read` for monitoring feedback and `files:write` for setup reports. Tokonoma does not automatically join channels; invite it explicitly. It does not request `chat:write.public` or direct-message history.

Continue with [alert investigations](alert-investigations.md), or return to [integrations](integrations.md).
