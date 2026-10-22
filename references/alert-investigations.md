# Automatic investigations

`toko-runner` investigates eligible alerts through a dedicated Tokonoma MCP instance and saves its findings. With Slack configured, it posts an announcement and a result thread in the investigations channel.

The [installation example](../examples/values.yaml) enables the required runner with `runner.enabled: true`. [Agentic monitoring](agentic-monitoring.md) can also start investigations from its findings. This guide configures external alert delivery and investigation tools.

Investigations send alert content, retrieved telemetry, memory content, and tool results to the configured model provider. Configured Slack destinations receive summaries and links. Review source permissions before enabling unattended work.

Use Alertmanager, [Datadog](datadog-alerts.md), or both. At least one source token is required. Datadog-only installations omit the Alertmanager token input.

## What gets deployed

| Component | Purpose |
|---|---|
| `toko-runner` | Receives webhooks, applies the guardrails, runs the agent, posts to Slack |
| `toko-mcp-unattended` | A second MCP instance with the same image and database as `toko-mcp` |
| `toko-grafana-mcp-server` | Optional private OSS Grafana MCP subchart, enabled by `grafanaMcp.enabled`, for read-only telemetry queries against your existing Grafana |

The unattended instance separates investigations from interactive requests. It shares PostgreSQL, holds no Slack credentials, and accepts no external traffic. The runner cannot start without database access.

Bundled PostgreSQL needs no additional setup. For external PostgreSQL (`postgres.enabled=false` with `postgres.host`), the `postgres.auth.username` role needs schema `CREATE`, read/write access, and ownership or equivalent migration rights. The runner updates its tables and indexes at startup; missing permissions cause CrashLoopBackOff.

## Before you start

Prepare the runner in your saved `values.yaml`. Follow [credential setup](credentials.md) for the license, model key, and protected files. Complete [Slack app setup](slack-app.md) if you want Slack results. Use the installation's [input conventions](install.md#inputs-and-placeholders).

| Input | Meaning and source | Required when |
|---|---|---|
| `alertmanager-token.txt` | High-entropy shared token created by the operator and also configured on the sender | Alertmanager or Grafana alerts |
| `REPLACE_WITH_GRAFANA_URL`, `grafana-viewer-token.txt` | Existing Grafana URL and Viewer service-account token with the required data-source permissions | Grafana MCP adapter |
| `runner-client-id.txt`, `runner-client-secret.txt` | Dedicated runner credentials from the selected [identity provider](oauth.md) | MCP authentication enabled |
| `REPLACE_WITH_MCP_HOSTNAME`, `REPLACE_WITH_TLS_SECRET_NAME` | Public host and existing TLS Secret from [ingress setup](public-mcp-ingress.md) | External alert sender |

Keep `alertmanagerconfig-tokonoma.yaml`, if used, beside `values.yaml`. Merge any [Datadog settings](datadog-alerts.md) into the same values file.

Generate `alertmanager-token.txt` only if no receiver token exists. Preserve existing tokens when adding a source or upgrading:

```sh
umask 077
openssl rand -hex 32 | tr -d '\n' > "REPLACE_WITH_SECRET_DIRECTORY/alertmanager-token.txt"
```

This writes without printing the token. Configure the same value on the sender.

For externally managed Secrets or offline rendering, follow [credentials](credentials.md#use-existing-kubernetes-secrets). If `mcp.auth` is enabled, configure the runner credential below.

## Prepare runner credentials when MCP authentication is enabled

Use a dedicated Cognito machine-to-machine app client and its ID and secret. Follow [OAuth](oauth.md) to configure its domain, resource-server scope and client-credentials flow. Keep [Google Workspace](google-saml.md) or [Okta SAML](okta-saml.md) alongside Cognito for individual human sign-in.

For the legacy Google Identity Platform/Firebase verifier, enable Email/Password and create a dedicated runner account. Its email is the runner's client ID and its password is the client secret. Google OAuth app credentials do not work.

Declare the Cognito app client ID or Google account email in `mcp.auth.clients` with `origin: external`, grant `client_credentials`, scope `toko-mcp/query`, and `tokenEndpointAuthMethod: client_secret_post`. SAML-only login cannot issue a machine credential: keep the selected credential provider alongside SAML for the runner.

Keep an existing runner credential Secret if it works. Otherwise, save the raw credentials as `runner-client-id.txt` and `runner-client-secret.txt` in the protected directory. [Prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets), then create the runner credential Secret:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-runner-oauth \
  --from-file=clientId="REPLACE_WITH_SECRET_DIRECTORY/runner-client-id.txt" \
  --from-file=clientSecret="REPLACE_WITH_SECRET_DIRECTORY/runner-client-secret.txt"
```

Expected output: `secret/toko-runner-oauth created`. Merge this into `values.yaml`, retaining the full identity-provider settings in that file:

```yaml
runner:
  tokoMcp:
    oauthClientSecretRef:
      name: toko-runner-oauth
      clientIdKey: clientId
      key: clientSecret
```

## Configure the runner

### Install with OSS Grafana MCP

To query an existing Grafana, uncomment `grafanaMcp` in your saved [values file](../examples/values.yaml). Replace the Grafana URL and choose a protected Viewer token file or existing Secret reference. The private adapter requires Kubernetes 1.25+ and connects to the runner automatically.

If you do not use Grafana, configure a [telemetry MCP connection](integrations.md#mcp-connections), such as Datadog or Axiom. Agentic monitoring needs query access; alert webhooks and code access alone are insufficient.

### Apply the configuration

For a new installation, prepare the selected credentials and use [Install](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration). If you enabled Grafana with a token file, include `--set-file grafanaMcp.grafana.apiKey="REPLACE_WITH_SECRET_DIRECTORY/grafana-viewer-token.txt"`.

Retain authentication and the runner credential when MCP authentication is enabled. Complete the shared installation health checks; [investigation checks](#check-it-works) are optional follow-ups.

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

Preserve every paging receiver and route. Add a separate runner route with `continue: true` so runner downtime cannot block paging. Forward all alerts from your existing Alertmanager configuration. The runner applies investigation controls after delivery.

### Raw Alertmanager

Merge this fragment into your existing configuration, retaining the real `oncall` receiver and its settings. Reload through your usual Alertmanager deployment process.

```yaml
route:
  receiver: oncall
  routes:
    - receiver: toko-runner
      continue: true          # let the alert also reach oncall
    - receiver: oncall
receivers:
  - name: toko-runner
    webhook_configs:
      - url: http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager
        http_config:
          authorization:
            # Mounted file containing only the raw source token.
            credentials_file: /etc/alertmanager/runner/token
```

Mount `toko-alertmanager`, or your `runner.sources.alertmanager.tokenSecretRef`, at `/etc/alertmanager/runner/`. Each Secret key becomes a filename: `token` becomes `/etc/alertmanager/runner/token`.

### prometheus-operator (`AlertmanagerConfig`)

Operator-managed Alertmanager reads the Secret directly. Check its namespace-matching policy so the rendered route covers all intended alerts. Save `alertmanagerconfig-tokonoma.yaml` in the working directory. Confirm your operator selects this namespace and resource before applying:

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: toko-runner
  namespace: tokonoma
spec:
  route:
    receiver: toko-runner
    continue: true
  receivers:
    - name: toko-runner
      webhookConfigs:
        - url: http://toko-runner.tokonoma.svc:8080/webhooks/alertmanager
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

Merge these settings into your existing `values.yaml`, retaining other fields under `mcp` and `runner`. They reference an existing TLS Secret and keep the configured Alertmanager token:

```yaml
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

Configure the identity provider and runner OAuth client before applying public routing. Keep their complete configuration in the same `values.yaml`. Replace the host/TLS reference and configure your existing controller using
[Public MCP Ingress](public-mcp-ingress.md). This adds an `Exact` rule for
`/webhooks/alertmanager` to that MCP Ingress, forwarding to `toko-runner:8080`.
It does not enable the runner by itself. For Datadog-only exposure, use the
explicit [Datadog settings](datadog-alerts.md#2-configure-the-runner).

To expose both receivers, set `runner.ingress.webhookPaths: [/webhooks/datadog, /webhooks/alertmanager]` in `values.yaml`. Keep the Alertmanager token and add the Datadog Secret reference using the [Datadog guide](datadog-alerts.md).

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

Adjust these defaults for your alert volume and model budget. The first two controls belong under `runner.sources.alertmanager`; Datadog has its own [source settings](datadog-alerts.md#2-configure-the-runner). The remaining controls belong under `runner.guardrails` and are shared.

| Control | Default | What it bounds |
|---|---|---|
| `filters.severities` | `[critical, warning]` | Which alerts are eligible at all |
| `delaySeconds` | `60` | Wait before investigating; alerts that resolve during the wait are skipped |
| `dedupWindowMinutes` | `60` | Cooldown after a run starts; `0` disables this check |
| `priorArtWindowHours` | `24` | Skip recently investigated alerts; `0` also permits repeats of the same firing episode |
| `maxConcurrentRuns` | `5` | Maximum simultaneous investigations; alerts may use one fewer slot when this exceeds `1` |
| `maxWaitSeconds` | `1800` | Maximum wait for capacity after the delay; timed-out alerts are skipped |
| `maxRunsPerDay` / `maxRunsPerDayCritical` | `200` / `200` | Separate daily limits whose combined maximum is their sum |

Accepted alerts survive runner restarts. Check skipped or failed outcomes in the runner's metrics before resending an alert. During startup, deliveries can return `500`; Alertmanager retries them.

## Check it works

Use these optional checks to verify alert delivery and investigation results after installation. A completed test investigation is not an installation requirement.

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

### Send one controlled alert and verify its result

Use an operator-approved test alert that can make model calls and post to any configured destination. Keep existing paging routes intact. For Grafana Alertmanager, use its documented [contact-point test](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/#test-a-contact-point):

1. Open **Alerting > Notification configuration > Contact points**. Edit the Tokonoma webhook contact point and select **Test**.
2. Choose **Custom**. Use a fresh `alertname`, `severity: warning` and the service or namespace labels needed by your configured filters. State in the annotation that this is an installation test, not a production incident.
3. Select **Send test notification** once. This uses the contact point's configured bearer token. Allow the source's `delaySeconds` and any queue wait before expecting a result.
4. Repeat the metrics command in terminal 2. Check accepted delivery, then a completed run in `runner_run_total`. If the alert was skipped, read the reason in `runner_intake_skipped_total` and correct the test's labels or eligibility before another send.
5. With Slack enabled, find this alert's announcement and result thread in the configured investigations channel. Confirm the summary and linked memory record describe the installation test. Without Slack, use your connected coding agent to find the saved investigation by its unique test alert name and fetch its full body. Require the record identifier and findings that describe this test. An accepted delivery without a completed investigation and saved record does not complete the check.

Grafana's contact-point test is available only for Grafana Alertmanager. With raw or operator-managed Alertmanager, use your team's approved test alert through its existing rule and routing process. For Datadog, follow [its verification steps](datadog-alerts.md#4-verify). Do not change production thresholds or remove paging receivers to force a test.

Stop the port-forward with Ctrl-C when finished. If the test creates a temporary rule, remove only that test rule through the same provider workflow.

## Rotate credentials

Follow [credential rotation](credentials.md#renew-and-rotate) for model, Slack, and Grafana credentials and the required restarts.

For an Alertmanager token, save old and new tokens comma-separated in `alertmanager-token.txt`. [Apply the configuration change](upgrading.md#before-changing-configuration) with the updated `credentials.alertmanagerToken` file. Update the sender and verify delivery before removing the old token and applying again. With an external Secret, update it and restart the runner at each step. For Datadog, use its [token rotation procedure](datadog-alerts.md#rotating-the-token). Webhook credentials do not grant MCP query access.

## Adding your own MCP servers

Use the shared [MCP connection guide](integrations.md#mcp-connections) for Datadog, Axiom, and other compatible telemetry or code servers. Configure endpoints, credentials, and permitted tools in the same `runner.mcpServers` list in `values.yaml`. Alert-source tokens do not grant query access.

## Stop the runner for maintenance

This stops investigations and agentic monitoring, and removes the runner, its dedicated MCP instance, and the Grafana adapter. Use it only for a planned service interruption. Pause only Tokonoma alert deliveries, preserving paging routes.

Record the component settings, then set `runner.enabled`, `mcp.sibling.enabled`, and `grafanaMcp.enabled` to `false` in `values.yaml`. [Apply the configuration change](upgrading.md#before-changing-configuration), preserving credentials. Confirm those components are removed with `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods`; skip their readiness checks while they are disabled. Existing investigation records remain.

Restore the recorded settings and apply again. Verify one controlled alert before resuming routine Tokonoma deliveries.

Return to [integrations](integrations.md) or continue with [Datadog alerts](datadog-alerts.md).
