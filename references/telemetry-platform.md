# Set up the telemetry platform

Choose the telemetry platform when you want Tokonoma to store and query logs and traces in your cloud. Existing Grafana and telemetry MCP connections can remain in use. Enabling the platform does not expose MCP or collect your applications automatically.

## Include it in your installation

1. Prepare object storage and cloud identity using [AWS](cloud-providers/aws.md#optional-telemetry-and-self-monitoring) or [Google Cloud](cloud-providers/google-cloud.md#optional-telemetry-and-self-monitoring).
2. Merge those settings into your installation values. Keep native telemetry tools enabled; the runner can query them through its private MCP instance without another telemetry MCP connection.
3. Complete [installation](install.md), including required Slack and any selected MCP access. For an existing release, use [configuration preservation](upgrading.md#before-changing-configuration) instead of reinstalling.
4. Verify the backend with the cloud guide, then provide the [customer collector example and endpoints](customer-telemetry.md). Application ingestion and monitoring coverage remain pending until data arrives.

## Capacity and operating choices

Chart 0.42.1 adds these Quickwit requests to the [base installation](planning.md):

| Component | CPU request | Memory request | Persistent volume |
| --- | --- | --- | --- |
| Searcher | 500m | 2 GiB | 20 GiB |
| Indexer | 1000m | 4 GiB | 8 GiB |
| Metastore | 250m | 512 MiB | Uses PostgreSQL |
| Control plane | 250m | 256 MiB | None |
| Janitor | 250m | 256 MiB | None |
| Total | 2250m | 7 GiB | 28 GiB, plus object storage |

These are scheduling requests, not throughput or production sizing guarantees. Inspect the chart you install with `helm show values oci://public.ecr.aws/tokonoma/charts/tokonoma`. Budget for ingestion, queries, object storage requests, retention, and any network transfer. Measure representative traffic and leave room for bursts.

## Optional self-monitoring

These settings default to `false`. Set the selected keys to `true` in your installation values after reviewing their requirements with the platform owner.

- `otelCollector.enabled` collects Tokonoma's own logs and traces. It mounts `/var/log/pods` from each node as a read-only `hostPath` volume. Namespaces enforcing Baseline Pod Security reject that mount. Enable the collector only where your platform owner has approved the mount and the namespace policy permits it.
- `prometheus.enabled` adds metrics collection with cluster-wide scrape targets, including workloads, nodes, and the Kubernetes API. Review scope and permissions before enabling it, or use [existing Prometheus](prometheus.md).
- `grafana.enabled` adds [dashboards](endpoints.md#self-monitoring-grafana-ui) backed by the bundled Prometheus and collector. The pinned Quickwit plugin requires amd64 nodes. See [troubleshooting](troubleshooting.md) if Grafana fails to start on ARM nodes.

These components add resources and storage beyond the table. Customer application collection uses a [separate collector](customer-telemetry.md).

## Indexes and retention

With `customer` set and `telemetryIndexes` empty, the chart creates `CUSTOMER-logs` and `CUSTOMER-traces` with 30-day retention. For new indexes, an explicit list can set retention:

```yaml
telemetryIndexes:
  - name: REPLACE_WITH_CUSTOMER-logs
    schema: logs
    retentionDays: 30
  - name: REPLACE_WITH_CUSTOMER-traces
    schema: traces
    retentionDays: 30
```

This list replaces the default list. Preserve every index you intend to create. Match the collector's headers and the MCP query defaults to the actual index names, especially when using custom names.

The installation hook creates missing indexes; it does not update retention on existing indexes. For an existing index, have the storage owner use the supported Quickwit index-update procedure, review data-loss implications, and verify the stored retention configuration. Changing the Helm value alone is insufficient. Shorter retention can permanently remove older data.

Kubernetes inventory requires its own schema, collection configuration, and query index setting. Neither the default index pair nor the bundled collector establishes customer Kubernetes inventory coverage. See [customer collection](customer-telemetry.md).
