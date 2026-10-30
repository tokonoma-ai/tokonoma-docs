# Upgrade Tokonoma

Install and upgrade commands use the latest released chart and its application image defaults. Chart and application versions are independent. Test the upgrade with your configuration before changing a production release.

Run the commands from the existing installation's working directory on an authorized workstation. Use [installation](install.md) for a new release.

| Input | Where to find it | How it is used |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | The existing installation record, verified against kubeconfig | Select the intended cluster explicitly |
| Release and namespace | The existing release; examples use `tokonoma` | Replace both consistently if yours differ |
| `values.yaml` | The saved installation configuration | Keep the required services and selected integrations in one file |
| Changed credentials or existing Secret references | Your secret manager and provider owners | Preserve the existing license and selected integrations |

## Before changing configuration

Review the deployed revision and saved configuration before changing settings. The commands below use the latest released chart, so applying a configuration change can also upgrade the chart. Confirm that this is within the customer's requested change, and complete the upgrade preparation below before applying it. Record the current revision for possible rollback:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT history tokonoma -n tokonoma
```

Apply the edited `values.yaml` using the chart defaults:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  -n tokonoma \
  --reset-then-reuse-values --values values.yaml \
  --wait --timeout 15m
```

This preserves previously supplied values, including credentials. Add `--set-literal 'KEY=REPLACE_WITH_VALUE'` for each new or changed credential, using the keys in [credentials](credentials.md#what-you-need) or the selected integration guide. Keep existing Secret references. Removing a setting from the file alone does not clear its saved value; set its intended replacement explicitly.

To remove obsolete keys, review a complete replacement values file and all required credential inputs, then replace `--reset-then-reuse-values` with `--reset-values` in the command above.

After Helm reports `deployed`, use the [installation health checks](install.md#4-verify). Follow [credential rotation](credentials.md#renew-and-rotate) for any required restarts. Integration guides provide optional functional checks.

The chart's application image default is `latest`, with image pull policy `Always`. A restarted pod can therefore pull a newer application build even when the chart version stays the same. Configuration changes that restart workloads can have this effect too. The unattended MCP and runner inherit the primary MCP image unless overridden.

Use the chart's application image defaults. Record the deployed chart version and actual image digest in the installation report so changes can be traced without fixing an installation version in these commands.

## Before upgrading

1. [Back up PostgreSQL](backup.md) and all other persistent data with your normal recovery process, and verify that you can restore them.
2. Record the current release revision and image, and review your saved values and externally managed Secrets. Helm values can contain credentials; do not paste them into tickets or public logs.
3. Check the migration notes below, including webhook paths, Grafana adapter values, authentication, and retired meeting capture.
4. Keep one complete nonsecret `values.yaml` and protected credential inputs. Do not assume an old override is still valid in a new chart.

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT history tokonoma -n tokonoma
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deployment toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].image}'
```

## Apply the upgrade

Review the latest chart defaults:

```sh
helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma
```

Review any saved primary MCP or runner image overrides. To return an existing deployment to chart image defaults, remove those overrides from a complete replacement values file and use the reviewed `--reset-values` procedure above with all required credential inputs. Removing a file entry alone does not clear a value preserved by `--reset-then-reuse-values`. The unattended MCP shares `mcp.image`.

Apply the upgrade:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  -n tokonoma \
  --reset-then-reuse-values --values values.yaml \
  --wait --timeout 15m
```

Expect Helm to report status `deployed`. Unchanged credentials are preserved; add `--set-literal` arguments only for new or changed values. Keep existing Secret references. Helm 3.14+ is required for `--reset-then-reuse-values`: it starts from new chart defaults, reapplies the previous supplied values, and then applies this command's overrides. Plain `--reuse-values` can retain old chart defaults. When intentionally removing obsolete keys, use a complete replacement values file and all required credential inputs with `--reset-values` after reviewing the effect.

An unchanged image reference alone does not trigger a Helm rollout. If the requested upgrade includes pulling the newest application behind `latest`, restart its Deployments after Helm finishes:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart \
  deployment/toko-mcp deployment/toko-mcp-unattended deployment/toko-runner
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp --timeout=10m
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-mcp-unattended --timeout=10m
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-runner --timeout=10m
```

Use the Deployment names in your release. Restart only workloads whose rolling images you intend to update. During runner rollout, investigations pause.

Confirm readiness and `/health` with the [installation checks](install.md#4-verify). Restart the MCP deployments after a license change; see [credentials](credentials.md). Optional integration checks can then verify model requests, Slack permissions, and alert delivery; Helm's wait does not test these.

Helm rollback restores chart resources and values, not database state, deleted objects, or revoked credentials. Review application and database compatibility before rolling back; use your backups when a state migration cannot be reversed.

## PostgreSQL and Ollama restarts

In chart [0.40.0](https://github.com/tokonoma-ai/tokonoma-charts/releases/tag/v0.40.0) and later, changing only `mcp.image.tag` or the chart version leaves bundled PostgreSQL and Ollama running. Changes to their own images or pod configuration still restart them.

Upgrading from chart 0.39.0 or earlier to 0.40.0 or later restarts both components once. Plan for a database interruption and for Ollama to reload its model.

## Grafana adapter: 0.35.x to 0.36.0 or later

The adapter moved to the upstream `grafana-mcp` subchart. Old keys are not automatically translated. Before upgrading an enabled adapter, migrate these values:

| Old key | Current key |
|---|---|
| `grafanaMcp.grafana.token` | `grafanaMcp.grafana.apiKey` |
| `grafanaMcp.grafana.existingSecret` | `grafanaMcp.grafana.apiKeySecret.name` |
| `grafanaMcp.grafana.secretKey` | `grafanaMcp.grafana.apiKeySecret.key` |
| `grafanaMcp.auth.existingSecret` | Set `grafanaMcp.auth.createSecret: false` and `grafanaMcp.envValueFrom.MCP_GRAFANA_SERVER_TOKEN.secretKeyRef.name` |
| `grafanaMcp.auth.secretKey` | `grafanaMcp.envValueFrom.MCP_GRAFANA_SERVER_TOKEN.secretKeyRef.key` |

`grafanaMcp.auth.token` remains the direct caller-token input. Keep the Viewer credential separate from the internal caller credential. Current adapter Deployment, Service, and inline Viewer Secret names default to `toko-grafana-mcp-server`; the caller Secret defaults to `toko-grafana-mcp-auth`. Review any name, port, allowed-host, and external Secret overrides together.

Preserve or rotate credentials and verify the rendered Secret references before applying. Remove obsolete keys from the complete values file and use the reset workflow above. After upgrading, restart consumers as described in [credential rotation](credentials.md#renew-and-rotate) and check that an investigation can query Grafana.

## Webhook paths: 0.34.x to 0.35.0 or later

`runner.ingress.enabled: true` no longer selects a webhook path on its own. Its `webhookPaths` default is `[]`. Set exactly the paths you need, keep the receiver bearer-token configuration, and keep MCP Ingress enabled:

```yaml
runner:
  ingress:
    enabled: true
    webhookPaths: [/webhooks/alertmanager, /webhooks/datadog]
```

Use only one entry if you use one source. Lists replace rather than append. An Ingress rule does not create a receiver or change its authentication.

## Native machine authentication: release prerequisite

The generated runner login requires application [v0.76.0](https://github.com/tokonoma-ai/tokonoma-mcp/releases/tag/v0.76.0) or later and chart [0.39.0](https://github.com/tokonoma-ai/tokonoma-charts/releases/tag/v0.39.0) or later. The application accepts native configured `client_credentials` clients; the chart provisions and connects the runner client. Application [v0.77.0](https://github.com/tokonoma-ai/tokonoma-mcp/releases/tag/v0.77.0) with chart 0.39.0 is the verified release pair for this guide. Chart 0.38.0 does not provision the native client.

Chart 0.39.0 also permits monitoring-only or Slack-requested investigations without an alert receiver token. With no alert sender, keep `runner.detection.enabled` or `runner.destinations.slackApp.enabled` true. Preserve credentials for receivers that are still in use; removing an Alertmanager or Datadog token disables that receiver.

With generated machine credentials, the first upgrade of a new installation restarts both MCP instances and the runner once to record the stored credential's revision. It keeps the same client ID and secret and does not revoke tokens.

For an existing installation, preserve its provider, declared clients, client IDs, and `runner.tokoMcp.oauthClientSecretRef`. Remove obsolete copies of the runner credential variables from `mcp.extraEnv`; the read-only UI needs no sign-in or machine credential setup. Remove `runner.extraEnv` entries only when they duplicate the runner's chart-managed credential references. Preserve other environment overrides. Follow the normal configuration-change procedure with a compatible released chart and application, then verify the runner.

When `runner.tokoMcp.url` targets an external MCP, preserve its explicit credential reference even if local MCP authentication is disabled. Those remote credentials configure the runner only; keep local MCP authentication independent.

Do not replace an existing external client with a new generated client without an identity migration plan. Client IDs identify record owners. For GitOps or client-only rendering, use the [explicit native credential](alert-investigations.md#gitops-or-an-existing-native-machine-secret) instead of rendering a fresh random Secret repeatedly.

## Authentication

Set `mcp.auth.enabled` explicitly. `true` requires a base URL and an active native machine client, credential provider, or SAML login method. The standard enabled runner provisions the native client. `provider: none` keeps native and SAML authentication enabled without external credential verification; it does not disable authentication. `mcp.auth.enabled: false` rejects leftover provider or SAML settings. See [OAuth](oauth.md), including client admission and rotation, before changing an existing authenticated deployment.

The unattended MCP shares authentication configuration. A new normal Helm install generates the runner's client-credentials grant and query scope automatically. Existing explicit runner credentials continue to work; custom external MCP URLs require an explicit credential reference. Use a top-level `domain` or explicit `mcp.auth.baseUrl` for a shared auth base URL; the sibling does not inherit `mcp.domain` alone.

## Older installations

- Chart 0.32.0 introduced durable intake settings, including `runner.guardrails.maxWaitSeconds`; the application must support them. Review the saved runner configuration when upgrading an older pinned image.
- Chart 0.30.0 changed the alert delay default from 300 to 60 seconds. Set the relevant source's `delaySeconds` explicitly if you want to retain the old delay.
- Chart 0.28.0 centralized model selection in `llm.model`, with per-consumer overrides. Use Anthropic model identifiers supported by your account; memory analysis and the runner both use the Anthropic API.
- Chart 0.8.0 pinned `nomic-embed-text:v1.5`. External or offline Ollama must provide that exact model and a compatible embedding version. A missing model can leave keyword search working while semantic search is unavailable.

For installations predating these changes, review the complete target values with your Tokonoma contact before applying an upgrade. Do not run old database repair commands simply because they appear in a historical guide.

## Retired meeting capture: charts 0.16.0 through 0.17.1

The target chart removes the Google Meet and Zoom attendee. A pre-upgrade cleanup hook stops active attendees and deletes their labeled Jobs, Pods, and per-meeting Secrets. Those deleted resources cannot be recovered by Helm rollback.

Notify participants before upgrading. Keep the old `meetingCapture.enabled` and namespace settings in the supplied values for this upgrade so automatic cleanup can find them. If you remove those settings, explicitly supply the old namespace and enable cleanup:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  -n tokonoma \
  --reset-then-reuse-values --values values.yaml \
  --set meetingCaptureCleanup.mode=enabled \
  --set-string meetingCaptureCleanup.namespace=REPLACE_WITH_OLD_NAMESPACE \
  --wait --timeout 15m
```

Replace the namespace before running. Retain all required credential inputs. If the retired subchart created that namespace, set `meetingCaptureCleanup.retainNamespace: true` for manual review. Automatic cleanup assumes a namespace dedicated to one release. If it was shared, stop all attendees and remove the resources carrying both `tokonoma.ai/meeting-bot=true` and `runtime.managed=true` through your operator process before setting cleanup mode to `disabled`.

Confirm no attendee workloads remain in the old namespace. The cleanup does not delete shared operator Secrets or PostgreSQL records. Review retained data separately.
