# Uninstall

Run commands on an authorized workstation. Replace `REPLACE_WITH_KUBE_CONTEXT` with the verified context for the installation to remove. Release and namespace are `tokonoma` in these examples; substitute the existing names consistently if different. Confirm what you intend to remove before uninstalling or deleting the namespace.

Back up PostgreSQL and all other persistent data you need before removal, including telemetry and monitoring data. Inspect the PVCs and backup/retention settings for every enabled component. Stop alert senders or route them elsewhere before removing a runner.

```sh
helm --kube-context REPLACE_WITH_KUBE_CONTEXT uninstall tokonoma -n tokonoma
```

Expect Helm to report that the release was uninstalled. Inspect the remaining resources below; successful uninstall does not mean all data was deleted.

The base memory installation retains its PostgreSQL data claim, Ollama model PVC, and generated PostgreSQL Secret. Older or customized installations may have other retained volumes; inspect them before deleting anything. The default self-monitoring Grafana and Prometheus PVCs have no Helm retention annotation and are removed on uninstall. Back them up or configure an approved retention policy before running the command. Backing-disk deletion depends on each PV/StorageClass reclaim policy. The generated Grafana MCP caller Secret is also retained when that adapter was enabled. The chart-owned license and supplied Anthropic, Slack, and Alertmanager Secrets are removed. Externally managed Secrets remain under your secret manager's control.

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
