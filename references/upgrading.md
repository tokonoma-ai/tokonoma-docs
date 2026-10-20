# Upgrade Tokonoma

This guide targets chart **0.37.0** and application **0.68.0**. Chart and image versions are independent. Test the target versions with your configuration before changing a production release.

Run the commands from the existing installation's working directory on an authorized workstation. Use [installation](install.md) for a new release.

| Input | Where to find it | How it is used |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT` | The existing installation record, verified against kubeconfig | Select the intended cluster explicitly |
| Release and namespace | The existing release; examples use `tokonoma` | Replace both consistently if yours differ |
| Values files and order | The saved installation configuration | Include every selected file after the base values file |
| `REPLACE_WITH_SECRET_DIRECTORY` or existing Secret references | Your credential storage | Preserve the existing license and selected integrations |

For a feature-only change, first verify that the installed chart and application match this guide. If they differ, use instructions verified for the installed versions or agree on the version change before using the pinned commands. Adding Slack or another feature must not silently upgrade or downgrade the deployment.

## Before upgrading

1. Back up PostgreSQL and all other persistent data with your normal recovery process, and verify that you can restore them.
2. Record the current release revision and image, and review your saved values and externally managed Secrets. Helm values can contain credentials; do not paste them into tickets or public logs.
3. Check the migration notes below, including webhook paths, Grafana adapter values, authentication, and retired meeting capture.
4. Keep one complete nonsecret values file and protected credential inputs. Do not assume an old override is still valid in a new chart.

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT history tokonoma -n tokonoma
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get deployment toko-mcp \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="mcp")].image}'
```

## Apply the upgrade

Update `mcp.image.tag` to `"0.68.0"` in `tokonoma-values.yaml`, then:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma \
  --reset-then-reuse-values --values tokonoma-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 15m
```

Expect Helm to report status `deployed`. Include every selected `--values` file in its original order, every changed credential input, and existing Secret references. If the license uses an existing Secret reference, omit the direct license-file argument. Helm 3.14+ is required for `--reset-then-reuse-values`: it starts from new chart defaults, reapplies the previous supplied values, and then applies this command's overrides. Plain `--reuse-values` can retain old chart defaults. When intentionally removing obsolete keys, use a complete replacement values file and all required credential inputs with `--reset-values` after reviewing the effect.

Check pod readiness, the `/health` response, a licensed memory read, and the optional integrations you enabled. Restart the MCP deployments after a license change; see [credentials](credentials.md). A successful Helm wait does not verify Slack permissions, model-provider access, or external alert delivery.

Helm rollback restores chart resources and values, not database state, deleted objects, or revoked credentials. Review application and database compatibility before rolling back; use your backups when a state migration cannot be reversed.

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

Preserve or rotate the credentials during migration, and verify the new rendered Secret references before applying. Remove obsolete keys from your complete values file and use the reset workflow above. After the upgrade, verify the adapter and runner, restart consumers as described in [credential rotation](alert-investigations.md#rotate-credentials), and check that an investigation can query Grafana. This migration has been checked by rendering; test it against your running configuration before rollout.

## Webhook paths: 0.34.x to 0.35.0 or later

`runner.ingress.enabled: true` no longer selects a webhook path on its own. Its `webhookPaths` default is `[]`. Set exactly the paths you need, keep the receiver bearer-token configuration, and keep MCP Ingress enabled:

```yaml
runner:
  ingress:
    enabled: true
    webhookPaths: [/webhooks/alertmanager, /webhooks/datadog]
```

Use only one entry if you use one source. Lists replace rather than append. An Ingress rule does not create a receiver or change its authentication.

## Authentication

Set `mcp.auth.enabled` explicitly. `true` requires the provider/login configuration and a stable base URL. `false` rejects leftover provider or SAML settings. See [OAuth](oauth.md), including client admission and rotation, before changing an existing authenticated deployment.

The unattended MCP shares authentication configuration. An authenticated runner needs a separately configured client-credentials grant with the required query scope. Use a top-level `domain` or explicit `mcp.auth.baseUrl` for a shared auth base URL; the sibling does not inherit `mcp.domain` alone.

## Older installations

- Chart 0.32.0 introduced durable intake settings, including `runner.guardrails.maxWaitSeconds`; the application must support them. Review the saved runner configuration when upgrading an older pinned image.
- Chart 0.30.0 changed the alert delay default from 300 to 60 seconds. Set the relevant source's `delaySeconds` explicitly if you want to retain the old delay.
- Chart 0.28.0 centralized model selection in `llm.model`, with per-consumer overrides. Use model identifiers supported by your provider; memory analysis uses the Anthropic API independently of the runner provider.
- Chart 0.8.0 pinned `nomic-embed-text:v1.5`. External or offline Ollama must provide that exact model and a compatible embedding version. A missing model can leave keyword search working while semantic search is unavailable.

For installations predating these changes, review the complete target values with your Tokonoma contact before applying an upgrade. Do not run old database repair commands simply because they appear in a historical guide.

## Retired meeting capture: charts 0.16.0 through 0.17.1

The target chart removes the Google Meet and Zoom attendee. A pre-upgrade cleanup hook stops active attendees and deletes their labeled Jobs, Pods, and per-meeting Secrets. Those deleted resources cannot be recovered by Helm rollback.

Notify participants before upgrading. Keep the old `meetingCapture.enabled` and namespace settings in the supplied values for this upgrade so automatic cleanup can find them. If you remove those settings, explicitly supply the old namespace and enable cleanup:

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT upgrade tokonoma oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma \
  --reset-then-reuse-values --values tokonoma-values.yaml \
  --set-string mcp.image.tag=0.68.0 \
  --set meetingCaptureCleanup.mode=enabled \
  --set-string meetingCaptureCleanup.namespace=REPLACE_WITH_OLD_NAMESPACE \
  --wait --timeout 15m
```

Replace the namespace before running. Retain all required credential inputs. If the retired subchart created that namespace, set `meetingCaptureCleanup.retainNamespace: true` for manual review. Automatic cleanup assumes a namespace dedicated to one release. If it was shared, stop all attendees and remove the resources carrying both `tokonoma.ai/meeting-bot=true` and `runtime.managed=true` through your operator process before setting cleanup mode to `disabled`.

Confirm no attendee workloads remain in the old namespace. The cleanup does not delete shared operator Secrets or PostgreSQL records. Review retained data separately.
