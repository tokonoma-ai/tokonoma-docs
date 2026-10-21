# Agentic Monitoring

Agentic Monitoring checks connected telemetry and starts automatic investigations for eligible findings. It works alongside investigations triggered by Alertmanager or Datadog alerts.

The [values example](../examples/values.yaml) enables `runner.detection.enabled: true` and the required runner. Automatic investigation of monitoring findings has no separate enable switch. Detectors are saved monitoring checks. Setup activates checks that pass validation; proposals held for review stay inactive until approved.

## Prepare the inputs

Use the same `values.yaml` as the rest of the installation. For an existing deployment, edit its saved file and preserve the current integrations and credentials.

| Input | What to configure |
| --- | --- |
| Telemetry access | Connect [Grafana or another telemetry integration](integrations.md) with read access to the intended systems. External monitoring connections in `runner.mcpServers` need `kind: telemetry`, an endpoint, credentials, and permitted tools. Alert webhooks alone do not provide query access. |
| Model credentials | Keep the runner's model credential and the required Anthropic analysis credential from [installation](install.md#2-prepare-your-files). |
| Cluster | Set `runner.detection.scope.cluster` to the cluster name in your telemetry source. It may differ from the Kubernetes context name. Ask the source owner when unsure; a source containing multiple clusters needs an explicit choice. |
| Namespaces | Set `runner.detection.scope.namespaces` to exact namespace names. An empty list watches all namespaces, including system namespaces. Choose that scope deliberately. |
| Alert source | Keep at least one Alertmanager or Datadog source credential, as required by the chart. Follow [runner setup](alert-investigations.md#before-you-start). |

Check telemetry access with the source owner before deploying. Configure [Slack](slack-app.md) for setup reports, investigation results, and approval commands. Without Slack, automatically activated detectors can run, but proposals held for review remain inactive. Connect Slack to approve or reject them.

Setup and investigations can make model calls and query your integrations. Review the chosen scope and [data flows](data-flows.md) before enabling them.

For a new release, finish preparation and use the [installation command](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration).

## Check setup and review proposals

Monitoring starts setup automatically when first enabled. With Slack connected, send these commands in a channel where Tokonoma is invited:

```text
@Tokonoma setup
@Tokonoma detectors
```

The setup response reports progress, missing access, scope questions, or failures. The detector list shows active checks and proposals awaiting your decision.

If setup stopped, correct the reported configuration or access problem. To request setup again:

```text
@Tokonoma detectors setup
```

Review each held proposal's purpose and query before approving it. Replace the placeholder with an ID from the detector list:

```text
@Tokonoma detectors approve REPLACE_WITH_DETECTOR_ID
@Tokonoma detectors reject REPLACE_WITH_DETECTOR_ID
```

Choose one action per proposal, then check `@Tokonoma detectors` to confirm. Approval permits monitoring and automatic investigations.

## Read the monitoring views

Use the local connection from [installation](install.md#4-verify), then open [the local UI](http://localhost:8000/ui/) and choose **Agentic Monitoring**:

- **Coverage** shows the monitored entities, saved detector configuration, and pending approvals. Expand a row to review its purpose, query, and available evidence.
- **Significant Findings** shows recorded findings and their associated investigations. Open the investigation record to read the result.

Keep this UI on the direct localhost connection. Browser sessions cannot apply detector actions; use the Slack commands above. Opening a view does not start setup or activate proposals.

## Verify monitoring

These are optional follow-up checks after installation. Monitoring setup and evaluations run in the background; installation does not wait for them.

A ready runner pod does not prove monitoring is working. Confirm that setup completed for the intended scope and that detectors are approved. Address missing telemetry access, incomplete setup, and degraded detectors before treating coverage as operational.

To check ongoing evaluations, use the runner port-forward in [runner verification](alert-investigations.md#check-the-deployment). From another terminal:

```sh
curl --fail --show-error --silent http://localhost:8080/metrics | grep runner_detector_evaluations_total
```

Compare the counters across the configured evaluation interval. Investigate repeated degraded or insufficient evaluations; a static coverage list is not evidence of current execution.

When a finding occurs, confirm its investigation completes and open the saved record. Check its Slack result too when enabled. An empty findings view does not prove the monitored systems are healthy. Do not force a production anomaly to test setup; any controlled test needs the system owner's approval.

Verify external alert delivery separately with the [runner checks](alert-investigations.md#check-it-works).
