# Choose integrations

Start with your saved values files and installed release to see which integrations are configured. The runner is required; the example enables [agentic monitoring](agentic-monitoring.md) and automatic investigations. Choose its model provider, alert sources, telemetry query access, and investigation tools as part of [installation](install.md#2-prepare-your-files). Agents inspect existing configuration and ask about missing settings, conflicts, or additions. Each guide supplies the inputs, commands, and checks.

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

Model-assisted memory processing uses the Anthropic API. The investigation runner has its own provider configuration; verify credentials and provider-specific model identifiers before changing that configuration. See [memory LLM setup](memory-llm.md) and [data flows](data-flows.md).

Uncomment your selected integrations in [values.yaml](../examples/values.yaml). The [runner guide](alert-investigations.md) covers credentials, alert routing, and verification.

Return to the [documentation index](../README.md). Agents start with the [root skill](../SKILL.md) and use these same guides.
