# Choose integrations

The [base installation](install.md) needs no telemetry provider. Start with your saved values files and installed release to identify configured integrations. For a new installation, the supplied examples contain defaults only. Choose the connections you want below. Agents inspect existing configuration first and ask only about missing settings, conflicts, or additions. Each guide supplies inputs, commands, and checks.

| Integration | What it does | Setup |
|---|---|---|
| Tokonoma Slack app | Answers mentions, shares investigation sessions, and delivers runner results through your Slack app | [Slack app](guides/slack-app.md) |
| Claude in Slack | Connects Anthropic's Slack experience to the Tokonoma MCP endpoint | [Claude in Slack](guides/claude-in-slack.md) |
| Existing Grafana | Optional private OSS Grafana MCP adapter queries permitted data sources for the runner | [Alert investigations](guides/alert-investigations.md#install-with-oss-grafana-mcp) |
| Alertmanager or Grafana Alerting | Sends alert webhooks to the runner | [Alert investigations](guides/alert-investigations.md) |
| Datadog | Receives monitor webhooks; optional Datadog MCP access provides query tools | [Datadog alerts](guides/datadog-alerts.md) |
| Tokonoma telemetry platform | Stores and searches ingested logs, traces, and Kubernetes inventory/events | [EKS](platform/eks.md), [GKE](platform/gke.md), [endpoints](reference/endpoints.md) |

The bundled `grafanaMcp` adapter queries an existing Grafana. The separate `grafana.enabled` setting installs a UI for Tokonoma's own monitoring. They are independent options.

CloudWatch is **not a supported adapter in this release**. A proposed adapter is not an installation option. Enabling the telemetry platform does not connect to CloudWatch automatically.

Model-assisted memory processing uses the Anthropic API. The investigation runner has its own provider configuration; verify credentials and provider-specific model identifiers before changing that configuration. See [memory LLM setup](guides/memory-llm.md) and [data flows](data-flows.md).

For the Grafana runner example, use [runner-grafana-values.yaml](../examples/runner-grafana-values.yaml) with the credential command in the [complete guide](guides/alert-investigations.md#install-with-oss-grafana-mcp). This example disables file attachments to avoid sharing a ReadWriteOnce volume across the interactive and unattended MCP pods. Use S3, GCS, or an existing ReadWriteMany claim if you need attachments with both pods.

Return to the [documentation index](../README.md). Agents start with the [root skill](../SKILL.md) and use these same guides.
