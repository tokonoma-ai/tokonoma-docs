# Send application telemetry

After Tokonoma setup is complete, use the [example collector configuration](../examples/customer-otel-collector.yaml) to send application logs and traces to your telemetry platform. This is a starting configuration for a collector you manage. It does not deploy a collector or instrument applications. The chart's bundled collector gathers Tokonoma's own telemetry only.

## Prepare the connection

Review [platform capacity and retention](telemetry-platform.md) before ingesting application data. First verify the selected [AWS](cloud-providers/aws.md#3-verify-the-optional-services) or [Google Cloud](cloud-providers/google-cloud.md#3-verify-the-optional-services) backend and finish any selected [MCP query access](team-access.md). Record the release namespace, `customer` slug, and actual index names. With default index configuration, the chart creates `CUSTOMER-logs` and `CUSTOMER-traces`; custom `telemetryIndexes` can change them.

| Setting | Value for the standard installation |
| --- | --- |
| Export protocol | OTLP over gRPC |
| Endpoint from the same cluster | `toko-indexer.tokonoma.svc.cluster.local:7281` |
| Logs index header | `qw-otel-logs-index: REPLACE_WITH_CUSTOMER-logs` |
| Traces index header | `qw-otel-traces-index: REPLACE_WITH_CUSTOMER-traces` |

Replace the namespace and index placeholders with verified values. These headers select indexes; they are not authentication credentials. Port 7281 is the indexer's gRPC ingest endpoint, not an OTLP/HTTP endpoint and not the MCP endpoint. MCP query exposure does not expose ingestion.

The example uses plaintext gRPC inside the cluster. Limit access to approved collectors through your network controls. For applications outside that cluster, have the platform owner provide private connectivity or a protected TLS ingress that supports gRPC before sending data. Use the verified hostname, certificate settings, and authentication required by that route; do not publish the internal endpoint or disable TLS verification to make it work.

## Adapt the collector

Use an approved OpenTelemetry Collector distribution and validate this configuration against its version before deploying it through your normal workflow. Review resource limits and buffering for your volume; the example's memory limit is only a starting point.

The example receives OTLP/gRPC on port 4317. Point instrumented applications at your collector's reachable address. It does not scrape container log files or discover Kubernetes workloads. If you need those, configure the appropriate receivers and permissions with your platform owner. Preserve the service, cluster, and namespace attributes needed by your [monitoring scope](agentic-monitoring.md#choose-the-monitored-cluster).

Kubernetes inventory and events need separate receivers, permissions, and routing. The default customer indexes cover logs and traces only. Do not claim cluster inventory is collected from this example. Agree on inventory schema and the corresponding query index with Tokonoma before adding that collection.

Metrics need a Prometheus-compatible query source. This example sends logs and traces only; use the bundled Prometheus after reviewing its cluster-wide scrape scope, connect [existing Prometheus](prometheus.md), an existing Grafana, or another supported query source for metrics. Review the [data flows](data-flows.md) before changing collection destinations.

## Verify application data

Use `@Tokonoma admin status` to check [Slack and runner readiness](slack-app.md#verify-the-connection). Verify application data separately.

1. Send an approved sample log and trace from a known service.
2. Query both samples through MCP or, if you enabled [Grafana](endpoints.md#self-monitoring-grafana-ui), use Grafana Explore with data sources configured for your application indexes. The bundled Grafana data sources point to Tokonoma's own telemetry. Confirm the samples have the expected service, timestamps, cluster, and namespace.
3. Complete the [monitoring checks](agentic-monitoring.md#verify-monitoring) for those services. Revisit coverage after adding more applications.

Keep application ingestion pending until both samples are queryable. Track monitoring coverage separately.
