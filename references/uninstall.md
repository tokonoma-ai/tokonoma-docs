# Uninstall

Run commands on an authorized workstation. Replace `REPLACE_WITH_KUBE_CONTEXT` with the verified context for the installation to remove. Release and namespace are `tokonoma` in these examples; substitute the existing names consistently if different. Confirm what you intend to remove before uninstalling or deleting the namespace.

[Back up PostgreSQL and check recovery](backup.md), along with all other data you need, including telemetry and monitoring data. Inspect persistent volume claims (PVCs) and retention settings for every enabled component.

## Stop incoming work

Remove or disable only the routes that send alerts to this Tokonoma installation before removing its receiver. Preserve all existing paging destinations.

- **Datadog:** remove the Tokonoma monitor notification rule through the Terraform project or administrator workflow that created it. Review the plan to confirm other notification rules and monitor settings remain. Once nothing references the Tokonoma webhook, remove that webhook and its dedicated custom variable. The [Datadog recipe](datadog-alerts.md#3-configure-datadog) creates these as separate resources; uninstalling Helm does not remove them.
- **Alertmanager or Grafana Alerting:** remove only the Tokonoma route or contact-point integration. Remove its receiver/contact point only after checking that no other route uses it. Preserve parent routes, `continue` behavior, and other receivers so normal paging still works.
- **Other senders:** stop any separately managed deployment-event or webhook delivery to this installation through its owning system.

Let any in-progress investigations finish, or record that they will be interrupted. Then retire the Kubernetes release.

## Remove the release

The chart's default uninstall behavior is:

| Resource | Result |
|---|---|
| PostgreSQL and Ollama PVCs, generated PostgreSQL Secret | Retained |
| Generated Grafana MCP caller Secret | Retained when the adapter was enabled |
| Generated runner machine Secret | Retained when native runner authentication was enabled; preserve it for reinstalling |
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

## Retire external resources

Helm does not remove manually managed webhook Ingresses, DNS records, certificates, identity-provider clients, or cloud resources. Remove only resources dedicated to this retired installation, through their existing owners and configuration. A shared load balancer, certificate, identity provider, or observability service can still serve other systems.

If retiring the Slack integration, remove the app from its channels and uninstall it from the workspace only when no other installation uses it. Revoke its dedicated bot and app-level tokens. Retained Slack messages and files follow the workspace's retention policy; removing the app does not erase them.

Revoke credentials dedicated to this installation, including model-provider, TypeSafe, Grafana, telemetry MCP, and machine-client credentials. Do not revoke a credential still used by another deployment. Object-storage buckets, cloud IAM, secret-manager entries, Terraform state, and backups have their own ownership and retention requirements; review those separately before deletion.
