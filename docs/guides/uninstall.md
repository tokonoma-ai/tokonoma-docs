# Uninstall

Run commands on an authorized workstation. Replace `REPLACE_WITH_KUBE_CONTEXT` with the verified context for the installation to remove. Release and namespace are `tokonoma` in these examples; substitute the existing names consistently if different. Confirm removal scope before running either uninstall or namespace deletion.

Back up PostgreSQL, attachments, and any telemetry or monitoring data you need before removal. Inspect the PVCs and backup/retention settings for every enabled component. Stop alert senders or route them elsewhere before removing a runner.

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT uninstall tokonoma -n tokonoma
```

Expect Helm to report that the release was uninstalled. Inspect the remaining resources below; successful uninstall does not mean all data was deleted.

The base memory installation retains its PostgreSQL data claim, attachment PVC, Ollama model PVC, and generated PostgreSQL Secret. This is not a blanket retention policy for optional components: the default self-monitoring Grafana and Prometheus PVCs have no Helm retention annotation and are removed on uninstall. Back them up or configure an approved retention policy before running the command. Backing-disk deletion depends on each PV/StorageClass reclaim policy. The generated Grafana MCP caller Secret is also retained when that adapter was enabled. The chart-owned license and supplied Anthropic, Slack, and Alertmanager Secrets are removed. Externally managed Secrets remain under your secret manager's control.

Inspect what remains:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pvc,secrets
```

Retained credentials may be required to read retained databases on reinstall. Do not delete them while keeping the data and expecting a new random password to work.

Only if this namespace is dedicated to Tokonoma and you intend to delete everything in it:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT delete namespace tokonoma
kubectl --context REPLACE_WITH_KUBE_CONTEXT wait --for=delete namespace/tokonoma --timeout=10m
```

Namespace deletion removes retained claims and Secrets too. Whether backing disks are deleted depends on the PV/StorageClass reclaim policy. Follow your platform's storage recovery procedure if deletion stalls; do not force-remove storage finalizers as routine cleanup.

Object-storage buckets and cloud IAM are not managed by this chart. Review their retention requirements separately. Revoke unneeded Slack, model-provider, and Grafana credentials when retiring the installation.
