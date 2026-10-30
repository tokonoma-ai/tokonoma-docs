# Agentic Monitoring

Agentic Monitoring checks connected telemetry and starts automatic investigations for eligible findings. It works alongside investigations triggered by Alertmanager or Datadog alerts.

The [values example](../examples/values.yaml) enables `runner.detection.enabled: true` and the required runner. The shared [investigation limits](alert-investigations.md#pause-automatic-investigations) can pause automatic investigations from both monitoring findings and incoming alerts while monitoring checks continue. Detectors are saved monitoring checks. Setup activates checks that pass validation. Inactive or degraded checks leave gaps in coverage.

Monitoring discovery currently uses Kubernetes clusters and namespaces. Choose a Kubernetes scope; it can differ from the cluster hosting Tokonoma. In a mixed Kubernetes and ECS environment, ECS workloads may be absent from discovery and monitoring coverage. Treat that as a known coverage gap, not evidence that those workloads are healthy. [Datadog alert investigations](datadog-alerts.md) can still receive alerts from both environments.

## Prepare the inputs

Use the same `values.yaml` as the rest of the installation. For an existing deployment, edit its saved file and preserve the current integrations and credentials.

| Input | What to configure |
| --- | --- |
| Telemetry access | Connect [Datadog, Axiom, or another compatible MCP server](integrations.md#mcp-connections), or the [Grafana adapter](alert-investigations.md#install-with-oss-grafana-mcp). Use `kind: telemetry` for external monitoring connections and permit the required read-only query tools. Monitoring runs unattended and can call every tool a connection lists, so [list read-only tools only](integrations.md#1-choose-the-connection-and-tools). Alert webhooks alone do not provide query access. |
| Model credentials | Keep the Anthropic API key from [installation](install.md#2-prepare-your-files). It serves both analysis and the runner. |
| Cluster | Set `runner.detection.scope.cluster` to the cluster name in your telemetry source. It may differ from the Kubernetes context name. Ask the source owner when unsure; a source containing multiple clusters needs an explicit choice. |
| Namespaces | Set `runner.detection.scope.namespaces` to exact namespace names. An empty list watches all namespaces, including system namespaces. Choose that scope deliberately. |
| Alert source (optional) | Monitoring does not require an alert receiver. To investigate incoming Alertmanager or Datadog alerts too, configure that receiver's credential using [runner setup](alert-investigations.md#before-you-start). |

Check telemetry access with the source owner before deploying. Configure [Slack](slack-app.md) for setup reports, status commands, investigation results, and feedback.

Setup and investigations can make model calls and query your integrations. Review the chosen scope and [data flows](data-flows.md) before enabling them.

For a new release, finish preparation and use the [installation command](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration).

## Check setup and scope

Monitoring starts setup automatically when first enabled. Operators can check it with these commands in a channel where Tokonoma is invited:

```text
@Tokonoma admin status
@Tokonoma admin get plan
```

The status response reports progress, missing access, scope questions, or failures. Confirm that the reported cluster, namespaces, and services match your chosen scope. The plan lists checks and their IDs as a saved setup or refresh snapshot. Its statuses may differ from live detector state after `enable detector` or `disable detector`; report coverage gaps rather than assuming every service is monitored. `@Tokonoma admin` lists the operator commands.

If setup stopped, correct the reported configuration or access problem. To request setup again:

```text
@Tokonoma admin replan
```

## Read the monitoring views

In Slack, `@Tokonoma monitoring summary` requests a fresh report for the last 24 hours in the investigations channel. Operators can retrieve the saved plan with `@Tokonoma admin get plan`. See [Slack commands](slack-app.md#use-tokonoma-in-a-channel).

For unwanted or unhelpful monitoring, use `@Tokonoma disable detector REPLACE_WITH_DETECTOR_ID` with an ID from the report or plan. It stops future evaluations; an evaluation already running may finish. `enable detector` reverses a disable unless the detector has since been retired. Useful or not useful feedback on a result rates that investigation and is separate from disabling a detector.

Use the local connection from [installation](install.md#4-verify), then open [the local UI](http://localhost:8000/ui/) and choose **Agentic Monitoring**:

- **Coverage** shows the monitored entities, saved detector configuration, and status. Expand a row to read its purpose, query, and available evidence.
- **Significant Findings** shows recorded findings and their associated investigations. Open the investigation record to read the result.

Keep these views on the direct localhost connection. Opening a view does not start setup or activate checks. Use Slack for finding feedback.

## Ongoing monitoring and maintenance

Tokonoma refreshes the monitoring plan on `runner.detection.refreshEvery`, every 7 days by default. It checks the current services and telemetry, proposes monitoring for newly discovered services, and records changes in the saved plan and refresh report. Use `@Tokonoma admin replan` when you need fresh discovery before the next scheduled refresh.

Refresh can retune detectors that were degraded after repeated negative feedback. It validates revised checks and tests them against history before they can run. An unusable proposal leaves the detector degraded, so retuning does not guarantee restored coverage. This is separate from your choice to disable a detector; that choice is preserved when the detector carries into a new plan.

With Slack delivery and `runner.digest.enabled` configured, the daily monitoring summary lists investigations worth a look and detectors repeatedly firing on known behavior. Open **Full record** for evidence or **Why these?** for the selection reasons. `@Tokonoma monitoring summary` requests a fresh report for the last 24 hours without replacing the scheduled report. See [Slack commands](slack-app.md#use-tokonoma-in-a-channel) for controls and request limits.

## Verify monitoring

A ready runner pod does not prove monitoring is working. When Agentic Monitoring is enabled, confirm that setup completed for the intended scope and detector evaluations are running. Report missing telemetry access, incomplete setup, and inactive or degraded checks as coverage limitations.

To check ongoing evaluations, use the runner port-forward in [runner verification](alert-investigations.md#check-the-deployment). From another terminal:

```sh
curl --fail --show-error --silent http://localhost:8080/metrics | grep runner_detector_evaluations_total
```

Compare the counters across the configured evaluation interval. Investigate repeated degraded or insufficient evaluations; a static coverage list is not evidence of current execution.

When a finding occurs, confirm its investigation completes and open the saved record. Check its Slack result too when enabled. An empty findings view does not prove the monitored systems are healthy. Do not force a production anomaly to test setup; any controlled test needs the system owner's approval.

Verify external alert delivery separately with the [runner checks](alert-investigations.md#check-it-works).
