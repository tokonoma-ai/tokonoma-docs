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

For an existing app, update **App Manifest** with this manifest and reinstall the app to grant any added permissions. Save the current bot token; keep the app-level token unless you are rotating it.

The manifest enables Socket Mode, mentions, channel message events, feedback reactions, report uploads, and interactive buttons. See Slack's [manifest instructions](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/) if needed.

## Save the connection settings

In `values.yaml`, uncomment the Slack settings from the [example](../examples/values.yaml), including `runner.destinations.slackApp.enabled: true` for investigation results. Supply both arguments below in the installation or configuration-change command, filling the token placeholders locally. The [installation example](install.md#3-install) already includes them:

```sh
  --set-literal 'credentials.slackBotToken=REPLACE_WITH_SLACK_BOT_TOKEN' \
  --set-literal 'credentials.slackAppToken=REPLACE_WITH_SLACK_APP_TOKEN'
```

For existing Secrets, use `mcp.slack.tokenSecret` instead of the two Slack arguments.

In each public or private channel where you want Tokonoma, run `/invite @Tokonoma`. Create `#tokonoma-investigations` and invite the app there for runner results. This is the default results channel; set `mcp.slack.investigationsChannel` only for a different channel name.

For an existing deployment, [apply the configuration change](upgrading.md#before-changing-configuration), including any changed token arguments and preserving other credentials.

## Verify the connection

When Slack is enabled, read the MCP logs on the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deployment/toko-mcp --tail=200
```

Look for `slack socket mode connected`. Then send `@Tokonoma help` in an invited channel and confirm that it replies. Send `@Tokonoma admin status` for a readiness report visible only to you. It reports Slack scopes, model availability, and runner readiness. When automatic investigations are enabled, also confirm investigation result delivery with [runner verification](alert-investigations.md#check-it-works).

| Symptom | Check |
| --- | --- |
| `Slack listener NOT started` | Both tokens and the database must be configured. |
| No reply in one channel | Invite the app to that channel. |
| `missing_scope` | Apply this version's manifest in Slack's **App Manifest** page and reinstall the app. |
| Questions or timelines unavailable | Supply an Anthropic API key and leave `mcp.memoryLlm.enabled: true`. Timelines also require [incident sessions](#optional-incident-sessions). |
| Runner results wait | Invite the app to the configured investigations channel and enable `runner.destinations.slackApp.enabled`. |
| Connection fails behind a proxy | Allow Slack API traffic and Socket Mode WebSocket upgrades. |

For token changes, follow [credential rotation](credentials.md#renew-and-rotate), then repeat the Slack reply check above.

## Use Tokonoma in a channel

Mention the app in a channel where it has been invited. Run `@Tokonoma help` for the commands supported by your installed version.

| Task | Command and expected behavior |
| --- | --- |
| Read the monitoring plan | `@Tokonoma plan` posts the full current plan document in the request's thread. It reads the saved plan without running setup. If no current plan is available, it says so. |
| Request a monitoring summary | `@Tokonoma summary` composes a fresh summary for the last 24 hours and posts it in the investigations channel. It does not replace the scheduled daily report. Requests within 10 minutes of the last manual summary, or while one is being composed, are refused. |
| Change detector activity | `@Tokonoma enable REPLACE_WITH_DETECTOR_ID` turns a detector on; `@Tokonoma disable REPLACE_WITH_DETECTOR_ID` stops evaluation until enabled again. Each command accepts multiple IDs. Review its scope and query before enabling it. |
| Investigate an alert | Reply `@Tokonoma investigate` in the alert's thread to send it to the runner. Add a steer, such as `@Tokonoma investigate checkout 502s for EU users`, to specify the symptom. This needs a configured runner and telemetry access. |
| Read the saved result | Click **Full record** on a result or recalled record. Reading the body requires a valid license. |

`enable` can resume disabled or degraded detectors and start unwatched detectors. A disabled detector stays off through replans until enabled again. System-retired detectors cannot be enabled. Newly created detectors follow normal backtest rules.

Ask ordinary questions with `@Tokonoma <question>` to find relevant saved records. See [Using Tokonoma](using-tokonoma.md) for the investigation workflow and an illustrative result.

### Operator commands

Use `@Tokonoma admin` or `@Tokonoma admin help` for operator help. These commands run in invited channels with no additional permission check. Normal help, setup reports, refresh reports, and daily summaries do not advertise them.

| Task | Command and expected behavior |
| --- | --- |
| Check readiness | `@Tokonoma admin status` reports connections, missing access, and runner readiness. Only the requester sees the reply. |
| Run monitoring setup | `@Tokonoma admin replan` requests discovery again. The completed report posts in the investigations channel. |
| Read a service profile | `@Tokonoma admin profile REPLACE_WITH_ENTITY_NAME` shows its saved profile. |
| Inspect detectors | `@Tokonoma admin detectors` lists detectors. `@Tokonoma admin detectors show proposals` or `@Tokonoma admin detectors show findings` reads a saved report section. |

The old top-level `setup` and `detectors` commands are no longer supported.

### Optional incident sessions

Slack multiplayer incident coordination is off by default across Slack, the MCP services, and the runner. This switch requires an application build with `SLACK_MULTIPLAYER_ENABLED` support. Older builds ignore the setting and may still expose incident coordination.

To enable incident coordination, add the flag to both `mcp.extraEnv` and `runner.extraEnv` in your saved `values.yaml`, preserving existing entries. The MCP setting also applies to its unattended sibling:

```yaml
mcp:
  extraEnv:
    - name: SLACK_MULTIPLAYER_ENABLED
      value: "true"
runner:
  extraEnv:
    - name: SLACK_MULTIPLAYER_ENABLED
      value: "true"
```

[Apply the configuration change](upgrading.md#before-changing-configuration), then run `@Tokonoma help` to confirm that session commands are listed.

To disable incident coordination, set both entries to `"false"` and apply the configuration change again. Removing them from the file alone can preserve saved `"true"` values. Confirm that `@Tokonoma help` omits session commands; those commands now return a disabled reply.

While disabled, session lookup, agent check-ins, progress updates, discussion tracking, expiry, and timelines do not run. The `investigation-session` skill and `get_investigation_session` tool are unavailable. The runner does not receive coordination instructions and refuses requests to join a `TKNM-<N>` session. Session cleanup and metadata backfills also stop; session tables remain installed and existing data is not deleted.

Ordinary investigations, memory reads and writes, and saved outcomes remain available. You can still mark an investigation `resolved`, `dead_end`, or `wont_fix` and save its `resolution_summary`. The Slack `investigate` command still requests an ordinary runner investigation.

| Task | Command and expected behavior when enabled |
| --- | --- |
| Start or rename a session | `@Tokonoma start checkout errors` creates a `TKNM-<N>` session and posts a prompt teammates can give their coding agents to join it. Bare `start` uses recent discussion for a title when available; `set title to <title>` changes the active title. |
| Resume a session | `@Tokonoma resume` reopens the most recent closed session in this channel within 24 hours. `resume TKNM-<N>` selects an older session in its original channel. |
| Review progress | `@Tokonoma state` summarizes the active session; `@Tokonoma timeline` assembles its timeline. Use `timeline TKNM-<N>` for a specific session in this channel. |
| Close and save | `@Tokonoma stop` closes the session. Then `@Tokonoma save` saves the closed session as one investigation; `save TKNM-<N>` selects a specific closed session. |

A Slack session coordinates teammates and their agents. Starting one does not itself start a runner investigation. Follow the handoff prompt to join from a coding agent, or request an investigation in the alert thread.

## Choose what to enable

Questions, relevance checks, and session timelines use the required Anthropic key and send relevant content to Anthropic. During an analysis outage, `help` remains available. With incident sessions enabled, exact session commands such as `state`, `stop`, and `resume` also remain available. Full record buttons need a valid Tokonoma license.

Automatic memory recall on alerts is off by default. To make the app reply to alerts from other apps, set `mcp.slack.autoRecallEnabled: true` in `values.yaml` and [apply the configuration change](upgrading.md#before-changing-configuration).

Automatic recall is separate from runner investigations. Investigation results use `runner.destinations.slackApp.enabled`. Avoid also configuring a legacy Slack webhook destination unless you want both deliveries.

## Channel access and shared records

The app receives channel messages where it is invited. With incident sessions enabled, it can read channel history for sessions. It can post shared records into invited channels. Its memory identity can access organization-wide records, not an individual user's private records or records shared only with named identity-provider groups. New records are shared with everyone by default; choose private sharing when needed. See [data flows](data-flows.md).

The manifest requests channel and user read scopes, `chat:write`, `reactions:write`, and `channels:join`. It also uses `reactions:read` for monitoring feedback and `files:write` for setup reports. Tokonoma does not automatically join channels; invite it explicitly. It does not request `chat:write.public` or direct-message history.

Continue with [alert investigations](alert-investigations.md), or return to [integrations](integrations.md).
