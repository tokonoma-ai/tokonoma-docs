# Configuration values

Keep a small values file without secrets in your customer working directory outside this repository. Supply credentials through protected files or existing Secret references. See [installation](install.md) for file preparation.

Run the following command on a workstation with Helm installed. It needs no customer inputs and prints the complete defaults for the latest released chart:

```sh
helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma
```

## Core installation

| Value | Purpose |
|---|---|
| `mcp.image.tag` | Omit to use the chart default, currently `latest`. Keep existing overrides during configuration changes; see [version selection](upgrading.md#before-changing-configuration). |
| `mcp.auth.enabled` | Explicitly `false` for the private installation; `true` with a configured login provider for shared access. |
| `mcp.ingress.enabled` | Default `false`. Configure hostname, TLS and access controls before enabling. |
| `mcp.license` | License supplied with `--set-file`; creates a chart-owned Secret. |
| `mcp.licenseSecret.name` / `.key` | Existing license Secret; takes precedence over inline license. |
| `postgres.enabled` | Default `true`; disable only with [external PostgreSQL](external-postgres.md) configured. |
| `postgres.auth.password` | Normally generated and reused by cluster-connected Helm. Supply a stable secret for deterministic offline/GitOps rendering. |
| `ollama.enabled` | Default `true`; provides local embeddings. The embedding model is `nomic-embed-text:v1.5`. |

## Supplied credentials

| Value | Consumer |
|---|---|
| `credentials.anthropicApiKey` | Memory processing and runner, unless their existing Secret references override it. |
| `credentials.slackBotToken` / `credentials.slackAppToken` | Primary MCP Slack app; supply both. |
| `credentials.alertmanagerToken` | Runner Alertmanager receiver; sender must use the same bearer token. |
| `grafanaMcp.grafana.apiKey` | Grafana Viewer service-account token for the optional adapter. |

See [credentials](credentials.md) for Secret references, storage in Helm metadata, and rotation. The chart does not validate third-party token permissions during template rendering.

## Slack and investigations

| Value | Purpose |
|---|---|
| `mcp.slack.investigationsChannel` | Channel name; empty uses `tokonoma-investigations`. Invite the app to the channel. |
| `mcp.slack.autoRecallEnabled` | Default `false`. Opt in only if you want immediate recall replies to incoming alerts. |
| `mcp.memoryLlm.enabled` | Default `true`, but calls need an Anthropic credential. Enables duplicate adjudication and model-backed Slack features. |
| `llm.model` | Shared model selection; use an identifier available to your provider/account. Consumer overrides are `mcp.memoryLlm.model` and `runner.engine.model`. |
| `runner.enabled` | Set `true` for the required runner. The chart default is `false`; configure model credentials, at least one webhook source credential, and the unattended MCP instance before enabling it. |
| `mcp.sibling.enabled` | Set `true` for the runner's dedicated MCP instance sharing PostgreSQL. |
| `runner.destinations.slackApp.enabled` | Delivers investigations through the native Slack app. |
| `runner.ingress.webhookPaths` | Default `[]`; explicit `[/webhooks/alertmanager]`, `[/webhooks/datadog]`, or both. Lists replace, rather than append. |

Follow [alert investigations](alert-investigations.md) for a complete compatible values file. Detection features in unreleased development builds are outside these guides.

## OSS Grafana MCP

`grafanaMcp.enabled: true` requires `runner.enabled: true`. Set `grafanaMcp.grafana.url` and a Viewer credential. The upstream adapter is `grafana/mcp-grafana:2.0.1`; its private Service defaults to `toko-grafana-mcp-server:8000`.

For externally managed Viewer credentials, leave `grafanaMcp.grafana.apiKey` empty and set `grafanaMcp.grafana.apiKeySecret.name` and `.key`. Inline Viewer credentials take precedence upstream. The internal adapter caller token is separate: `grafanaMcp.auth.token`, or `grafanaMcp.auth.createSecret: false` with `grafanaMcp.envValueFrom.MCP_GRAFANA_SERVER_TOKEN.secretKeyRef` for an externally managed Secret.

Generated PostgreSQL and adapter caller credentials rely on cluster lookup. For offline/GitOps rendering, supply stable explicit credentials or external Secret references. Do not apply repeated offline renders with freshly generated passwords. See [rotation](alert-investigations.md#rotate-credentials).

## Telemetry and storage

Installing on EKS or GKE does not require telemetry or object storage. Complete the cloud-provider guide's persistent-volume checks for a base installation. Set `telemetryPlatform: true` only when you choose Tokonoma's telemetry backend. Supply an organization slug in `customer`, a `region`, a telemetry bucket, and a workload identity. `objectStorage.serviceAccountCreate` defaults to `false`; the cloud-provider examples explicitly create the annotated account.

The chart uses the shared `customer` value to build index names and default bucket names. Set `objectStorage.indexesBucket` for an explicit bucket name. Use `objectStorage.indexesScheme: gs` with GCS. The chart does not create buckets or cloud IAM roles.

`otelCollector.enabled`, `prometheus.enabled`, and `grafana.enabled` install optional self-monitoring components. These are disabled by default. See [EKS](cloud-providers/aws.md), [GKE](cloud-providers/google-cloud.md), and [endpoints](endpoints.md).
