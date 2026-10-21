# Uninstall

Run commands on an authorized workstation. Replace `REPLACE_WITH_KUBE_CONTEXT` with the verified context for the installation to remove. Release and namespace are `tokonoma` in these examples; substitute the existing names consistently if different. Confirm what you intend to remove before uninstalling or deleting the namespace.

Back up PostgreSQL and all other data you need, including telemetry and monitoring data. Inspect persistent volume claims (PVCs) and retention settings for every enabled component. Pause only Tokonoma alert deliveries, preserving existing paging routes.

The chart's default uninstall behavior is:

| Resource | Result |
|---|---|
| PostgreSQL and Ollama PVCs, generated PostgreSQL Secret | Retained |
| Generated Grafana MCP caller Secret | Retained when the adapter was enabled |
| Self-monitoring Grafana and Prometheus PVCs | Removed; back up or configure retention before uninstalling |
| Chart-owned license, Anthropic, Slack, and Alertmanager Secrets | Removed |
| Externally managed Secrets | Remain under your secret manager's control |

Older or customized installations can differ. Backing-disk deletion depends on each volume's reclaim policy.

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT uninstall tokonoma -n tokonoma
```

Expect Helm to report that the release was uninstalled. This does not mean all data was deleted.

Inspect what remains:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pvc,secrets
```

Keep the credentials needed to read retained databases on reinstall. A new random password will not unlock the existing data.

Only if this namespace is dedicated to Tokonoma and you intend to delete everything in it:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT delete namespace tokonoma
kubectl --context REPLACE_WITH_KUBE_CONTEXT wait --for=delete namespace/tokonoma --timeout=10m
```

Namespace deletion removes retained claims and Secrets too. Whether backing disks are deleted depends on the PV/StorageClass reclaim policy. Follow your platform's storage recovery procedure if deletion stalls; do not force-remove storage finalizers as routine cleanup.

Object-storage buckets and cloud IAM are not managed by this chart. Review their retention requirements separately. Revoke unneeded Slack, model-provider, and Grafana credentials when retiring the installation.
