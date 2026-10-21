# Choose integrations

Check your saved values files and installed release before adding integrations. The example enables [agentic monitoring](agentic-monitoring.md) and automatic investigations. Choose the runner's model provider, alert sources, telemetry query access, and tools during [installation](install.md#2-prepare-your-files). Agents read existing choices and ask for missing inputs.

| Integration | What it does | Setup |
|---|---|---|
| Tokonoma Slack app | Answers mentions, shares investigation sessions, and delivers runner results through your Slack app | [Slack app](slack-app.md) |
| Claude in Slack | Connects Anthropic's Slack experience to the Tokonoma MCP endpoint | [Claude in Slack](claude-in-slack.md) |
| Existing Grafana | Private OSS Grafana MCP adapter queries permitted data sources for monitoring and investigations | [Alert investigations](alert-investigations.md#install-with-oss-grafana-mcp) |
| Alertmanager or Grafana Alerting | Sends alert webhooks to the runner | [Alert investigations](alert-investigations.md) |
| Datadog | Receives monitor webhooks; separately configured Datadog MCP access provides telemetry query tools | [Datadog alerts](datadog-alerts.md) |
| Tokonoma telemetry platform | Stores and searches ingested logs, traces, and Kubernetes inventory/events | [EKS](cloud-providers/aws.md), [GKE](cloud-providers/google-cloud.md), [endpoints](endpoints.md) |

The bundled `grafanaMcp` adapter queries an existing Grafana. The separate `grafana.enabled` setting installs a UI for Tokonoma's own monitoring. They are independent options.

This release has no CloudWatch adapter. Enabling telemetry storage does not connect Tokonoma to CloudWatch.

Memory analysis uses the Anthropic API. The runner has its own provider configuration; verify credentials and model identifiers before changing it. See [memory analysis](memory-llm.md) and [data flows](data-flows.md).

Uncomment your selected integrations in [values.yaml](../examples/values.yaml). The [runner guide](alert-investigations.md) covers credentials, alert routing, and verification.
