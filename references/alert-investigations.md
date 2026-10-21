# Alert-triggered investigations

Alertmanager sends firing alerts to `toko-runner`. After a delay and duplicate check, the runner investigates through a dedicated Tokonoma MCP instance, saves its findings, and posts a Slack summary.

To receive results in Slack, supply `credentials.slackBotToken` and `credentials.slackAppToken`, or `mcp.slack.tokenSecret`. Enable `runner.destinations.slackApp.enabled` and invite the app to the alert and investigations channels. Each alert gets an announcement, followed by its result in a thread. Omit `runner.destinations.slack.webhookUrlSecretRef` to avoid duplicate delivery through the legacy webhook.

Leave `mcp.slack.autoRecallEnabled: false` unless you want immediate memory recall replies. Those replies require an Anthropic key through `credentials.anthropicApiKey` or `mcp.memoryLlm.apiKeySecret`, with `mcp.memoryLlm.enabled: true`. Explicit mentions and session updates work independently.

The runner is required for a complete Tokonoma installation. Chart `0.37.0` defaults `runner.enabled` to `false`; this guide sets it to `true` with the required credentials and dedicated MCP instance. Investigations send alert content, retrieved telemetry, memory content, and tool results to the configured model provider. Summaries and links go to Slack. Review source permissions before enabling unattended work.

For Datadog-only alerts, create the [Datadog token Secret](datadog-alerts.md) first. Omit the Alertmanager token input and include the Datadog values file in the same upgrade. Both sources can run together. The chart requires at least one source token; a missing referenced Secret leaves the pod in `CreateContainerConfigError`.

## What gets deployed

| Component | Purpose |
|---|---|
| `toko-runner` | Receives webhooks, applies the guardrails, runs the agent, posts to Slack |
| `toko-mcp-unattended` | A second MCP instance with the same image and database as `toko-mcp` |
| `toko-grafana-mcp-server` | Optional private OSS Grafana MCP subchart, enabled by `grafanaMcp.enabled`, for read-only telemetry queries against your existing Grafana |
| `runner_runs` | A table the runner creates in your Postgres at startup, holding one row per attempt |

The unattended instance separates alert traffic from interactive requests. It shares your PostgreSQL, holds no Slack credentials, and accepts no external traffic. The runner stores duplicate checks in PostgreSQL so they survive restarts. It refuses to start if the database is unreachable.

Bundled PostgreSQL needs no additional setup. For external PostgreSQL (`postgres.enabled=false` with `postgres.host`), the `postgres.auth.username` role needs schema `CREATE`, read/write access, and ownership or equivalent migration rights. The runner updates its tables and indexes at startup; missing permissions cause CrashLoopBackOff.

## Before you start

Complete steps 1 through 5 of [installation](install.md), then [Tokonoma Slack app setup](slack-app.md). This guide completes the required runner step. Use Helm 3.14+, chart `0.37.0`, and application image `0.68.0`. Follow the [existing-version check](upgrading.md#before-upgrading) before applying these pinned examples to an existing release.

Run commands from the installation's working directory on its administration workstation, outside this checkout. Replace placeholders first; agents must ask for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Target cluster context from `kubectl config get-contexts` | Every cluster command |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected directory chosen during base installation | File-based credentials |
| `license.txt` | Tokonoma-issued license in the protected directory | Helm upgrades |
| `anthropic-api-key.txt` | Anthropic API key shared by memory processing and the runner | This example |
| `slack-bot-token.txt`, `slack-app-token.txt` | Tokens from [Slack app setup](slack-app.md) | Slack results |
| `alertmanager-token.txt` | High-entropy shared token created by the operator and also configured on the sender | Alertmanager or Grafana alerts |
| `REPLACE_WITH_GRAFANA_URL`, `grafana-viewer-token.txt` | Existing Grafana URL and Viewer service-account token with the required data-source permissions | Grafana MCP adapter |
| `runner-client-id.txt`, `runner-client-secret.txt` | Dedicated runner credentials from the selected [identity provider](oauth.md) | MCP authentication enabled |
| `REPLACE_WITH_MCP_HOSTNAME`, `REPLACE_WITH_TLS_SECRET_NAME` | Public host and existing TLS Secret from [ingress setup](public-mcp-ingress.md) | External alert sender |

Save raw credentials under `REPLACE_WITH_SECRET_DIRECTORY`, without quotes or a trailing newline. Keep all values files and `alertmanagerconfig-tokonoma.yaml`, if used, in the installation's working directory. The sections below name each file; Datadog-only setups also use `runner-datadog-values.yaml` from the [Datadog guide](datadog-alerts.md).

Generate `alertmanager-token.txt` only if no receiver token exists. Preserve existing tokens when adding a source or upgrading:

```sh
umask 077
openssl rand -hex 32 | tr -d '\n' > "REPLACE_WITH_SECRET_DIRECTORY/alertmanager-token.txt"
```

This writes without printing the token. Configure the same value on the sender.

`--set-file` creates chart-owned Secrets; no prior `kubectl create secret` is needed. To use an external secret manager, give each component a reference to its Secret.

Helm generates the bundled PostgreSQL password and Grafana MCP caller token during installation and reuses them on upgrades. Their Secrets survive uninstall; remove them only when intentionally resetting that installation. Client-only `helm template` and Argo rendering cannot reliably look up these Secrets. Supply `postgres.auth.password` and `grafanaMcp.auth.token`, or [external Secret references](values.md#oss-grafana-mcp), for consistent rendering.

Image `0.68.0` includes Grafana MCP support; no separate Grafana MCP release or external MCP OAuth setup is needed. If `mcp.auth` is enabled, configure the runner's `runner.tokoMcp.oauthClientSecretRef` below.

## Prepare runner credentials when MCP authentication is enabled

Use a dedicated Cognito machine-to-machine app client and its ID and secret. Follow [OAuth](oauth.md) to configure its domain, resource-server scope and client-credentials flow. Keep [Google Workspace](google-saml.md) or [Okta SAML](okta-saml.md) alongside Cognito for individual human sign-in.

For the legacy Google Identity Platform/Firebase verifier, enable Email/Password and create a dedicated runner account. Its email is the runner's client ID and its password is the client secret. Google OAuth app credentials do not work.

Declare the Cognito app client ID or Google account email in `mcp.auth.clients` with `origin: external`, grant `client_credentials`, scope `toko-mcp/query`, and `tokenEndpointAuthMethod: client_secret_post`. SAML-only login cannot issue a machine credential: keep the selected credential provider alongside SAML for the runner.

Keep an existing runner credential Secret if it works. Otherwise, save the raw credentials as `runner-client-id.txt` and `runner-client-secret.txt` in the protected directory, then create the Secret in the existing namespace:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-runner-oauth \
  --from-file=clientId="REPLACE_WITH_SECRET_DIRECTORY/runner-client-id.txt" \
  --from-file=clientSecret="REPLACE_WITH_SECRET_DIRECTORY/runner-client-secret.txt"
```

Expected output: `secret/toko-runner-oauth created`. Merge this into `runner-values.yaml` below before the upgrade. Keep the full identity-provider settings in `tokonoma-values.yaml`:

```yaml
runner:
  tokoMcp:
    oauthClientSecretRef:
      name: toko-runner-oauth
      clientIdKey: clientId
      key: clientSecret
```

## Install

### Install with OSS Grafana MCP

This example queries an existing Grafana and keeps both MCP endpoints private. `grafanaMcp.enabled` installs the upstream `grafana-mcp` subchart and connects the runner automatically. The adapter requires Kubernetes 1.25+. Leave it disabled if you do not need it.

Save this as `runner-values.yaml` in the customer working directory. Merge the authentication block above when needed. On an existing public installation, retain its ingress settings instead of adding `mcp.ingress.enabled: false`.

```yaml
# runner-values.yaml
mcp:
  image:
    tag: "0.68.0"
  ingress:
    enabled: false
  storage:
    backend: none
  sibling:
    enabled: true
  memoryLlm:
    enabled: true
  slack:
    autoRecallEnabled: false

runner:
  enabled: true
  destinations:
    slackApp:
      enabled: true

grafanaMcp:
  enabled: true
  grafana:
    url: REPLACE_WITH_GRAFANA_URL
```

For a deployment without Grafana, omit the `grafanaMcp` block and the `--set-file grafanaMcp.grafana.apiKey` argument below. Configure your actual [investigation tools](#adding-your-own-mcp-servers), including their endpoints, credentials, and allowed tools, before verification. Alert webhooks alone do not provide query access.

If using Grafana, replace its URL. Replace the file paths and run this from the customer working directory, including every existing overlay and credential input:

```sh
helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT --reset-then-reuse-values oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma --wait --timeout 10m \
  --values tokonoma-values.yaml --values runner-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set-file credentials.anthropicApiKey="REPLACE_WITH_SECRET_DIRECTORY/anthropic-api-key.txt" \
  --set-file credentials.slackBotToken="REPLACE_WITH_SECRET_DIRECTORY/slack-bot-token.txt" \
  --set-file credentials.slackAppToken="REPLACE_WITH_SECRET_DIRECTORY/slack-app-token.txt" \
  --set-file credentials.alertmanagerToken="REPLACE_WITH_SECRET_DIRECTORY/alertmanager-token.txt" \
  --set-file grafanaMcp.grafana.apiKey="REPLACE_WITH_SECRET_DIRECTORY/grafana-viewer-token.txt"
```

Expected result: Helm reports `tokonoma` as `deployed`. Keep all values and credentials on every upgrade. When MCP authentication is enabled, configure the runner credential above. Keep authentication enabled.

Protected files keep tokens out of shell history, but Helm stores their values in release metadata. Restrict access to the files, Helm metadata, and Secrets.

Default Secret names and keys are:

| Secret/key | Consumer |
|---|---|
| `toko-anthropic/apiKey` | Memory processing and runner |
| `toko-slack/botToken`, `toko-slack/appToken` | Primary MCP only |
| `toko-alertmanager/token` | Alert receiver |
| `toko-grafana-mcp-server/api-key` | Grafana Viewer credential |
| `toko-grafana-mcp-auth/token` | Adapter and runner caller credential |

Anthropic, Slack, and Alertmanager names follow the parent `fullnameOverride` or `nameOverride`, defaulting to `toko`. The adapter uses `grafanaMcp.fullnameOverride`; its caller Secret follows `envValueFrom.MCP_GRAFANA_SERVER_TOKEN.secretKeyRef`.

The adapter permits read-only data-source, Prometheus, Loki, Tempo, Pyroscope, and assertions tools. Dashboard/navigation, general API, annotation, and alert-management tools are excluded. Available data depends on your Grafana sources and Viewer permissions. The independent `grafana.enabled` self-monitoring UI is unnecessary for querying an existing Grafana.

Rendering fails and names the missing value if the runner lacks its sibling, a source token, a model credential, or an OAuth client when authentication is enabled.

## Wire up Alertmanager

Preserve every paging receiver and route. Add a separate runner route with `continue: true` so runner downtime cannot block paging. Select eligible alerts in your existing Alertmanager configuration.

### Raw Alertmanager

Merge this fragment into your existing configuration, retaining the real `oncall` receiver and its settings. Reload through your usual Alertmanager deployment process.

```yaml
route:
  receiver: oncall
  routes:
    - receiver: toko-runner
      matchers: [severity =~ "critical|warning"]
      continue: true          # let the alert also reach oncall
    - receiver: oncall
receivers:
  - name: toko-runner
    webhook_configs:
      - url: http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager
        # authorization nests under http_config. At the top level Alertmanager
        # rejects the config: `field authorization not found in type config.plain`.
        http_config:
          authorization:
            # The file holds the raw token string and nothing else.
            credentials_file: /etc/alertmanager/runner/token
```

Mount `toko-alertmanager`, or your `runner.sources.alertmanager.tokenSecretRef`, at `/etc/alertmanager/runner/`. Each Secret key becomes a filename: `token` becomes `/etc/alertmanager/runner/token`.

### prometheus-operator (`AlertmanagerConfig`)

Operator-managed Alertmanager reads the Secret directly. Save `alertmanagerconfig-tokonoma.yaml` in the working directory. Confirm your operator selects this namespace and resource before applying:

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: toko-runner
  namespace: tokonoma
spec:
  route:
    receiver: toko-runner
    matchers:
      - name: severity
        matchType: =~
        value: critical|warning
    continue: true
  receivers:
    - name: toko-runner
      webhookConfigs:
        - url: http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager
          # httpConfig, matching the WebhookConfig CRD schema: authorization is a
          # field of HTTPConfig, not of the webhook config itself.
          httpConfig:
            authorization:
              credentials:
                name: toko-alertmanager
                key: token
```

From the administration workstation, apply the saved resource:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma apply -f alertmanagerconfig-tokonoma.yaml
```

Expected result: `alertmanagerconfig.monitoring.coreos.com/toko-runner` is created or configured. Confirm the operator has loaded it before sending a test alert. Retain the existing notification routes.

> Bundled Alertmanager defaults to `prometheus.alertmanager.enabled: false`. Enable it if you rely on the bundled Prometheus.

### External Alertmanager or Grafana Alerting

In-cluster Alertmanager uses the private URL without Ingress. External senders, including Grafana Cloud, need an approved HTTPS ingress or relay. Grafana Cloud cannot reach ClusterIP or Tailscale-only addresses.

Save this as `runner-alertmanager-ingress-values.yaml` in the customer working directory. Add it after the complete runner values above. It references an existing TLS Secret and keeps the Alertmanager token supplied during installation:

```yaml
# runner-alertmanager-ingress-values.yaml
domain: REPLACE_WITH_MCP_HOSTNAME
mcp:
  auth:
    enabled: true
  ingress:
    enabled: true
    host: REPLACE_WITH_MCP_HOSTNAME
    tls:
      enabled: true
      secretName: REPLACE_WITH_TLS_SECRET_NAME
runner:
  ingress:
    enabled: true
    webhookPaths: [/webhooks/alertmanager]
```

Configure the identity provider and runner OAuth client above before applying either public overlay. Add the overlay after `runner-values.yaml` in the Helm command, and keep the complete OAuth configuration in your base values. Replace the host/TLS reference and configure your existing controller using
[Public MCP Ingress](public-mcp-ingress.md). This adds an `Exact` rule for
`/webhooks/alertmanager` to that MCP Ingress, forwarding to `toko-runner:8080`.
It does not enable the runner by itself. For Datadog-only exposure, use the
explicit [Datadog overlay](datadog-alerts.md#2-configure-the-runner).

To expose both receivers, save this as `runner-both-ingress-values.yaml` in the customer working directory. Use it instead of the single-source ingress overlay. It keeps the chart-created Alertmanager token and adds the Datadog token Secret from the [Datadog guide](datadog-alerts.md):

```yaml
# runner-both-ingress-values.yaml
domain: REPLACE_WITH_MCP_HOSTNAME
mcp:
  auth:
    enabled: true
  ingress:
    enabled: true
    host: REPLACE_WITH_MCP_HOSTNAME
    tls:
      enabled: true
      secretName: REPLACE_WITH_TLS_SECRET_NAME
runner:
  ingress:
    enabled: true
    webhookPaths: [/webhooks/datadog, /webhooks/alertmanager]
  sources:
    datadog:
      tokenSecretRef:
        name: toko-runner-datadog-webhook
        key: token
```

`webhookPaths` defaults to `[]`, exposing no webhooks. Helm replaces the whole list. Use absolute paths served by the runner with `Exact` matching. Routing requires the runner, runner ingress, and MCP Ingress to be enabled; it does not create receivers or change token authentication. Health and metrics stay private.

For a Grafana webhook contact point, use **POST** to
`https://REPLACE_WITH_MCP_HOSTNAME/webhooks/alertmanager`, keep its default JSON payload,
and set authorization scheme **Bearer** with the raw source token in the
protected credential field. Do not place the token in the URL or values file,
and do not configure Basic auth. The receiver parses Alertmanager-compatible
`alerts[]`; verify one actual firing/resolved payload before relying on custom
payload templates. [Grafana webhook settings](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/).

This receiver authenticates with a shared bearer token; it does not verify
Grafana HMAC signatures, supply TLS or cap Alertmanager request bodies.
Use company-approved edge authentication, body/rate limits and timeouts
before external exposure. All MCP Ingress annotations affect these paths,
including auth, allowlists and rewrites: ensure they permit the intended
sender and preserve its Authorization header. Chart routing does not enforce
HTTPS or establish reachability. If using a separate ingress/relay, leave
`runner.ingress.enabled: false` and configure that edge independently.

## Guardrails

The runner filters alerts, delays them, and checks for duplicates before making model calls. Adjust the default limits for your alert volume.

| Control | Default | What it bounds |
|---|---|---|
| `filters.severities` | `[critical, warning]` | Which alerts are eligible at all |
| `delaySeconds` | `60` | An alert that resolves within the window is skipped; one that lasts a few minutes is investigated. A longer delay skips longer alerts too, but postpones findings. With Alertmanager the run typically starts on a group's first delivery, before members that join at the next `group_interval` |
| `dedupWindowMinutes` | `60` | Cooldown after a run starts; `0` disables this check |
| `priorArtWindowHours` | `24` | A repeat of an alert already investigated is skipped; `0` disables this check, including repeats of the same firing episode, with MCP 0.55.0 or later |
| `maxConcurrentRuns` | `5` | Limits how many investigations can run at once. Alerts may hold one slot fewer than this (all of them at `1`), so a `@Tokonoma investigate` request still finds a slot during a wave |
| `maxWaitSeconds` | `1800` | How long an alert whose delay is up waits for a slot, in arrival order. One still waiting after this is skipped as `cap_concurrent`; an alert that resolves while waiting is skipped as `resolved` |
| `maxRunsPerDay` / `maxRunsPerDayCritical` | `200` / `200` | Bounds sustained spend. The two counters are independent, so the daily total is their sum. |

PostgreSQL retains accepted alerts across restarts. Delayed and waiting alerts resume; interrupted runs retry once, then become `retry_exhausted` after a second interruption. Alerts left unattended longer than `priorArtWindowHours` become `stale`.

Until startup loads the queue, deliveries return `500` and increment `runner_deliveries_total{outcome="intake_error"}`. Alertmanager retries them. Queue reads retry indefinitely, starting every 5 seconds and doubling up to 1 minute.

Tune limits using the cost and duration recorded in `runner.agent_run` spans and the counters at `/metrics`.

## Check it works

### Check the deployment

On the administration workstation:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods -l app.kubernetes.io/component=runner
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma logs deploy/toko-runner --tail=200
```

The runner pod should be ready. Resolve startup errors before testing an alert.

In terminal 1, keep this command running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-runner 8080:8080
```

Expected output includes `Forwarding from 127.0.0.1:8080`. In terminal 2 on the same workstation:

```sh
curl --fail --show-error --silent http://localhost:8080/health
curl --fail --show-error --silent http://localhost:8080/metrics | grep runner_
```

The health request should return HTTP 200. Record the counters before sending the test so you can compare them afterwards. Health alone does not prove investigations or Slack delivery.

### Send one controlled alert and verify its Slack result

Use an operator-approved test alert that can make model calls and post to the investigations channel. Keep existing paging routes intact. For Grafana Alertmanager, use its documented [contact-point test](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/#test-a-contact-point):

1. Open **Alerting > Notification configuration > Contact points**. Edit the Tokonoma webhook contact point and select **Test**.
2. Choose **Custom**. Use a fresh `alertname`, `severity: warning` and the service or namespace labels needed by your configured filters. State in the annotation that this is an installation test, not a production incident.
3. Select **Send test notification** once. This uses the contact point's configured bearer token. Allow the source's `delaySeconds` and any queue wait before expecting a result.
4. Repeat the metrics command in terminal 2. Check accepted delivery, then a completed run in `runner_run_total`. If the alert was skipped, read the reason in `runner_intake_skipped_total` and correct the test's labels or eligibility before another send.
5. In the configured investigations channel, find this alert's announcement and its result thread. Confirm the summary and linked memory record describe the installation test. A delivery count without that result does not complete the check.

Grafana's contact-point test is available only for Grafana Alertmanager. With raw or operator-managed Alertmanager, use your team's approved test alert through its existing rule and routing process. For Datadog, follow [its verification steps](datadog-alerts.md#4-verify). Do not change production thresholds or remove paging receivers to force a test.

Stop the port-forward with Ctrl-C when finished. If the test creates a temporary rule, remove only that test rule through the same provider workflow.

## Rotate credentials

Update protected Anthropic, Slack, or Alertmanager files and repeat the complete Helm upgrade. Changed inputs restart their consumers. External Secret changes require explicit restarts.

For the Grafana Viewer token, update the protected file and repeat the Helm
upgrade, then restart the adapter so its environment reads the updated Secret:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-grafana-mcp-server
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-grafana-mcp-server
```

The upstream subchart does not automatically restart the adapter when only its
inline API key changes. The generated internal caller token stays unchanged on
ordinary upgrades. To deliberately rotate it, supply the new value with
`--set-file grafanaMcp.auth.token="REPLACE_WITH_SECRET_DIRECTORY/grafana-caller-token.txt"`
on the Helm upgrade, then restart both consumers:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-grafana-mcp-server deployment/toko-runner
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-grafana-mcp-server
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-runner
```

Expect successful rollouts. Substitute actual Deployment names when using name overrides. External Grafana or caller-token Secret changes need the same restarts.

For source-token rotation, save old and new tokens comma-separated, then upgrade to restart the runner. Update the sender and verify delivery before removing the old token and upgrading again. With external Secrets, update the Secret and restart the runner at each step. Webhook authentication is separate from hosted Grafana MCP query authentication.

## Adding your own MCP servers

To add vendor telemetry or read-only source control, merge its connection into `runner-values.yaml` and create the referenced Secret before the next complete Helm upgrade:

```yaml
runner:
  mcpServers:
    - name: source-control
      kind: source-control
      url: https://api.githubcopilot.com/mcp/
      # Only listed tools are permitted; an unlisted call is denied, not prompted for.
      expectedTools: [get_pull_request, list_commits]
      authSecretRef:
        name: toko-runner-github
        key: appInstallationToken
```

Limit the GitHub App installation token to the permissions the runner needs. The runner gains all access that credential grants.

## Stop the runner for maintenance

This stops investigations and removes the runner, its dedicated MCP instance, and the Grafana adapter. Use it only for a planned service interruption. Pause only Tokonoma alert deliveries, preserving existing paging routes. Record the component settings, then set these three flags to `false` in the saved installation values. From the customer working directory, include every existing overlay and credential input when applying the change:

```sh
helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma --reset-then-reuse-values \
  --values tokonoma-values.yaml --values runner-values.yaml \
  --set-string mcp.image.tag=0.68.0 \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --set runner.enabled=false --set mcp.sibling.enabled=false \
  --set grafanaMcp.enabled=false \
  --wait --timeout 10m
```

Expect Helm status `deployed`. Confirm the runner and unattended pods are removed with `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods`. Existing investigation records remain. Restore the recorded settings and repeat the complete runner upgrade. Verify one controlled alert before resuming routine Tokonoma deliveries.

Return to [integrations](integrations.md) or continue with [Datadog alerts](datadog-alerts.md).
