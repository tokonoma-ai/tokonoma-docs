# Datadog alerts

Datadog notifications start investigations through `toko-runner`, which delays, checks for duplicates, investigates, and posts results to Slack. The [runner guardrails](alert-investigations.md#guardrails) apply; Datadog has its own delay, severity filter, and token.

Datadog needs a public HTTPS webhook. The chart adds it to your existing MCP Ingress.

## Before you start

- **Helm 3.14+, chart `0.37.0`, and image `0.68.0`.** Keep the complete install values, including HTTPS ingress and authentication, in `tokonoma-values.yaml`.
- **The [runner prerequisites](alert-investigations.md):** `mcp.sibling.enabled`, a model provider key, a Slack destination, and OAuth credentials when `mcp.auth` is enabled. Datadog-only installations need no Alertmanager token, but at least one source token is required.
- **MCP Ingress must serve HTTPS only.** Follow [Public MCP Ingress](public-mcp-ingress.md). The bearer token travels in a header; the chart cannot enforce HTTPS terminated through provider annotations. GKE's GCE controller initially serves HTTP too. Once its certificate and load balancer are active, add `kubernetes.io/ingress.allow-http: "false"` to `mcp.ingress.annotations`, upgrade, and verify HTTPS-only access before enabling deliveries.
- **Datadog Terraform provider 3.83.0 or later**, which supports notification-rule `filter.scope`. Add the three resources below to your existing project. Outside US1, set your site's API in `provider "datadog"`, for example `api_url = "https://api.us3.datadoghq.com/"`.
- **Read and write credentials** for webhooks, custom variables, and notification rules. Terraform reads resources after creation and during refresh, so write-only keys fail. Verify permissions against your organization's role policy.

## Inputs and files

Complete the [base installation](../install.md) and [existing-version check](upgrading.md#before-upgrading). Run Kubernetes and Helm commands from the installation's working directory on its administration workstation, outside this checkout. Use your existing Datadog Terraform project. Replace placeholders first; agents must ask for missing inputs.

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_KUBE_CONTEXT` | Cluster context from `kubectl config get-contexts` | Cluster commands |
| `REPLACE_WITH_SECRET_DIRECTORY` | Protected directory chosen during base installation | Secret files and Terraform plan |
| `REPLACE_WITH_MCP_HOSTNAME` | Public HTTPS host from the completed [ingress setup](public-mcp-ingress.md) | Datadog deliveries |
| `REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY` | Existing Terraform project with your Datadog provider and credentials | Provider setup below |
| `REPLACE_WITH_DATADOG_WEBHOOK_TOKEN` | Generated token from step 1, also copied into the protected Terraform variable file | Both ends of webhook authentication |

Keep `tokonoma-values.yaml`, `runner-values.yaml`, `runner-datadog-values.yaml` and every existing overlay in the customer working directory. Step 1 creates `datadog-webhook-token.txt` in the protected directory; the license remains in `license.txt`. Step 3 adds `tokonoma.tf` in your Datadog Terraform project and `tokonoma-datadog.tfvars` plus `tokonoma-datadog.tfplan` in the protected directory. Retain all credentials already used by the installation.

## What is exposed

| Request | Destination |
|---|---|
| Datadog monitor notification | Notification rule, then the `tokonoma` webhook with the configured bearer token |
| HTTPS `POST /webhooks/datadog` | MCP Ingress routes the exact path to `toko-runner:8080` |
| Other MCP paths | MCP Ingress routes to `toko-mcp:8000`, using MCP authentication |
| Runner `/health` and `/metrics` | Cluster-only Service |

The selected `POST /webhooks/datadog` path checks the token before reading the body and rejects unauthenticated requests with `401`. Its body limit is 64 KiB. Other runner paths on the public host fall through to MCP.

Sharing MCP Ingress reuses its host, certificate, and DNS. With the default Application Load Balancer (ALB) configuration, a separate Ingress creates another load balancer needing its own host and certificate. For a path-specific IP allowlist, use a web application firewall (WAF); see [network options](#stricter-network-options).

MCP Ingress authentication, allowlist, and rewrite annotations also affect Datadog. Check nginx `auth-url`, `whitelist-source-range`, and `rewrite-target`, or ALB `auth-type` and `inbound-cidrs` for blocked or rewritten deliveries.

> **GKE:** Set `runner.service.annotations` to include `cloud.google.com/neg: '{"ingress": true}'`, as in the [GKE Ingress guide](public-mcp-ingress.md#gke-gce). Health checks use the `/health` readiness probe; an optional `BackendConfig` can set them explicitly through the same annotation mechanism. `pathType: Exact` on GCE remains unverified.

## 1. Create the token

The runner's Kubernetes Secret and Datadog custom variable must contain the same token. Generate it in the protected directory for first setup only. Preserve existing tokens on upgrades; use [rotation](#rotating-the-token) to change one:

```sh
umask 077
openssl rand -hex 32 | tr -d '\n' > "REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt"
```

Use all 32 bytes for this public route; shorter tokens cause a startup warning.

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT create secret generic toko-runner-datadog-webhook -n tokonoma \
  --from-file=token="REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt"
```

Expected output from Kubernetes: `secret/toko-runner-datadog-webhook created`. This command requires the `tokonoma` namespace from base installation.

## 2. Configure the runner

Save this as `runner-datadog-values.yaml` in the customer working directory. If your existing runner already exposes Alertmanager, retain it with `webhookPaths: [/webhooks/datadog, /webhooks/alertmanager]` before applying this overlay.

```yaml
# runner-datadog-values.yaml
mcp:
  image:
    tag: "0.68.0"
  ingress:
    enabled: true
  auth:
    enabled: true
runner:
  ingress:
    enabled: true
    webhookPaths: [/webhooks/datadog]
  sources:
    datadog:
      tokenSecretRef:
        name: toko-runner-datadog-webhook
        key: token
```

**Adding Datadog to a runner you already run:** add this overlay after the complete existing values, preserving the source tokens and other credentials used by that installation:

```sh
helm upgrade tokonoma --kube-context REPLACE_WITH_KUBE_CONTEXT oci://public.ecr.aws/tokonoma/charts/tokonoma \
  --version 0.37.0 -n tokonoma \
  --reset-then-reuse-values --values tokonoma-values.yaml \
  --values runner-values.yaml --values runner-datadog-values.yaml \
  --set-file mcp.license="REPLACE_WITH_SECRET_DIRECTORY/license.txt" \
  --wait --timeout 10m
```

Expected result: Helm reports release `tokonoma` as `deployed`. Include every existing overlay and credential input, including the runner model and Slack credentials, in the command above.

**First runner install, Datadog only:** create the Datadog token Secret first. Follow the [runner install](alert-investigations.md#install) and OAuth client setup, omit `--set-file credentials.alertmanagerToken=...`, and append `--values runner-datadog-values.yaml`. Base values must include working HTTPS ingress and an MCP identity provider. The Datadog overlay re-enables ingress after the private runner values.

Do this in one upgrade: missing source tokens prevent rendering, and missing referenced Secrets cause `CreateContainerConfigError`.

The Secret registers `/webhooks/datadog`; ingress routes it. `webhookPaths` replaces earlier lists and defaults to `[]`. Use absolute paths served by the runner with `Exact` matching. To retain [Alertmanager exposure](alert-investigations.md#external-alertmanager-or-grafana-alerting), include both paths and its token. Routing requires the runner, runner ingress, and MCP Ingress to be enabled. It does not create receivers or change authentication. Health and metrics remain private.

The defaults for the source:

| Value | Default | What it does |
|---|---|---|
| `runner.sources.datadog.delaySeconds` | `60` | Wait before investigating, so a monitor that recovers inside the minute never spawns a run; one that stays triggered a few minutes is investigated. Raise it to skip those too |
| `runner.sources.datadog.filters.severities` | `[critical, warning]` | Datadog `error` alerts are `critical`, `warning` alerts are `warning`. Empty means all. |
| `runner.sources.datadog.serviceLabels` | `[service, task_family, kube_deployment, kube_stateful_set, kube_daemon_set, kube_service]` | Which tag names the service, first non-empty wins: the unified `service` tag, then the ECS task family, then the Kubernetes workload tags. Names the service; an alert without a service is still investigated. |

There is no namespaces filter on this source. Which alerts arrive at all is the notification
rule's scope, below, which reads every tag on the notification.

## 3. Configure Datadog

See the provider’s [3.83.0 release notes](https://github.com/DataDog/terraform-provider-datadog/releases/tag/v3.83.0) for notification-rule scope support.


Check that resources named `tokonoma` below do not already exist in your Terraform project or Datadog organization. Retain managed resources instead of declaring duplicates.

Save the following as `tokonoma.tf` in `REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY`. Merge the provider requirement into the existing `terraform` block rather than duplicating it. Retain your existing provider credentials and site settings.

The runner does not accept Datadog's default payload, which lacks the alert's scope and cycle key. Paste the payload exactly. `$ID`, `$ALERT_ID`, `$TOKONOMA_TOKEN` and the other `$...` names are Datadog template variables evaluated by Datadog. They are not shell variables; do not export or replace them.

```hcl
terraform {
  required_providers {
    datadog = {
      source  = "DataDog/datadog"
      version = ">= 3.83.0"   # datadog_monitor_notification_rule filter.scope
    }
  }
}

variable "tokonoma_webhook_token" {
  type      = string
  sensitive = true   # Use the same protected token value as the runner Secret.
}

resource "datadog_webhook_custom_variable" "tokonoma_token" {
  name      = "TOKONOMA_TOKEN"
  value     = var.tokonoma_webhook_token
  is_secret = true
}

resource "datadog_webhook" "tokonoma" {
  name           = "tokonoma"
  url            = "https://REPLACE_WITH_MCP_HOSTNAME/webhooks/datadog"
  encode_as      = "json"
  custom_headers = jsonencode({ Authorization = "Bearer $TOKONOMA_TOKEN" })
  payload        = <<-EOT
    {"schema":"tokonoma/datadog-v1","event_id":"$ID","monitor_id":"$ALERT_ID",
     "cycle_key":"$ALERT_CYCLE_KEY","transition":"$ALERT_TRANSITION","alert_type":"$ALERT_TYPE",
     "priority":"$ALERT_PRIORITY","title":"$ALERT_TITLE","scope":"$ALERT_SCOPE","tags":"$TAGS",
     "date":"$DATE","link":"$LINK","query":"$ALERT_QUERY","status":"$ALERT_STATUS",
     "message":"$TEXT_ONLY_MSG"}
  EOT
  depends_on     = [datadog_webhook_custom_variable.tokonoma_token]
}

resource "datadog_monitor_notification_rule" "tokonoma" {
  name       = "Tokonoma investigations"
  recipients = ["webhook-tokonoma"]   # the webhook's name, prefixed webhook-; no leading @
  filter {
    scope = "tokonoma:investigate"
  }
}
```

Replace `REPLACE_WITH_MCP_HOSTNAME` with your MCP hostname. Every payload value is quoted, so this depends on Datadog's substitution and escaping. Verify a real delivery with your monitor text before using it broadly; `schema` identifies the payload format.

Save the following as `REPLACE_WITH_SECRET_DIRECTORY/tokonoma-datadog.tfvars`. Replace its value with the exact contents of `datadog-webhook-token.txt`. Keep the file out of source control:

```hcl
tokonoma_webhook_token = "REPLACE_WITH_DATADOG_WEBHOOK_TOKEN"
```

On the administration workstation, initialize the existing Terraform project and inspect the plan:

```sh
chmod 600 "REPLACE_WITH_SECRET_DIRECTORY/tokonoma-datadog.tfvars"
terraform -chdir="REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY" init
terraform -chdir="REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY" plan \
  -var-file="REPLACE_WITH_SECRET_DIRECTORY/tokonoma-datadog.tfvars" \
  -out="REPLACE_WITH_SECRET_DIRECTORY/tokonoma-datadog.tfplan"
```

The plan should add or update the Tokonoma webhook, custom variable and notification rule. It must preserve existing alert destinations. After reviewing the changes, apply that saved plan:

```sh
terraform -chdir="REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY" apply "REPLACE_WITH_SECRET_DIRECTORY/tokonoma-datadog.tfplan"
```

Expected result: `Apply complete!`. Terraform state and saved plans contain the token. Restrict access to them as you do the Kubernetes Secret.

### Leave out recoveries

The default rule sends every transition. Recovery and no-data notifications are not investigated, but each produces a Slack announcement and a *"resolved notification, nothing to investigate"* reply.

To send only alert and warning transitions, use conditional recipients without a fallback. This removes recovery posts, but also prevents recoveries from cancelling delayed or queued investigations as `resolved`. Such alerts can then be investigated after recovery.

```hcl
resource "datadog_monitor_notification_rule" "tokonoma" {
  name = "Tokonoma investigations"
  filter {
    scope = "tokonoma:investigate"
  }
  conditional_recipients {
    conditions {
      scope      = "transition_type:is_alert"
      recipients = ["webhook-tokonoma"]
    }
    conditions {
      scope      = "transition_type:is_warning"
      recipients = ["webhook-tokonoma"]
    }
    # No fallback_recipients: recoveries and no-data notifications are not sent.
  }
}
```

`conditional_recipients` replaces `recipients`; do not use both. Whether `Re-Triggered` counts as `is_alert` is unverified; the runner skips episodes already investigated. Test both firing and recovery transitions.

### Choosing monitors

The rule matches the notification's tagset: the monitor's tags plus the firing group's tags.

**Opt-in tag (recommended).** Append `tokonoma:investigate` to each selected monitor's tags. This satisfies the monitor-update requirement below. Preserve all other tags, queries, thresholds, and destinations. This fragment shows only the tag change:

```hcl
resource "datadog_monitor" "payments_errors" {
  # ...
  tags = ["env:prod", "team:payments", "tokonoma:investigate"]
}
```

**Existing tags.** Scope the rule on existing tags such as `env:prod AND team:payments`
or a group tag such as `kube_namespace:checkout`. Keyless tags and partial
wildcards are not supported in a rule scope.

**ECS and Kubernetes.** Scope on shared tags such as `env:`, `team:`, and `service:`, or combine platform tags: `kube_namespace:checkout OR ecs_cluster_name:prod-checkout`. A Kubernetes-only scope excludes ECS. Set `service:` on both platforms for consistent service names; ECS otherwise falls back to `task_family`.

> The ECS tag names here (`task_family`, `ecs_cluster_name`) come from the Datadog Agent's ECS
> documentation and have not been verified against a real ECS notification. Check one of your
> ECS monitors' `$TAGS` before relying on them.

### Caveats

- **Pre-existing monitors.** Save the notification rule before creating or updating the monitors it should match. Adding the opt-in tag is one way to make that update. Validate a real transition before relying on the rule.
- **The token is in Terraform state** in plain text, as the custom variable's value. Treat the
  state as you would the Secret.
- **New groups wait.** A new group of a multi-alert monitor notifies after the monitor's
  `new_group_delay` (60 s by default), on top of Datadog's own delivery latency of about a minute.
- **A rejected delivery is lost.** Datadog retries a 5xx or a timeout; it never retries a 4xx.
  The runner answers 400 only when the body is not a JSON object or lacks `monitor_id`,
  `cycle_key` or `transition`, and takes a default for anything else. The template supplies
  those keys. A test notification with empty values is rejected with 400; use a controlled real monitor transition if that occurs.
- **Titles can be long.** Use each group variable in a multi-alert monitor’s name to avoid Datadog appending a long group description. The runner identifies the alert by monitor and group, not its display title.

The rule's `recipients` entry is `webhook-REPLACE_WITH_WEBHOOK_NAME`, unlike the `@webhook-REPLACE_WITH_WEBHOOK_NAME` mention in a monitor message. The supplied example uses `tokonoma` as that name.

## 4. Verify

On the administration workstation, keep terminal 1 running:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/toko-runner 8080:8080
```

Expected output includes `Forwarding from 127.0.0.1:8080`. In terminal 2 on the same workstation, record the current counters:

```sh
curl --fail --show-error --silent http://localhost:8080/metrics | grep runner_
```

Use one operator-approved test monitor that matches the notification rule. It must be allowed to make model calls and post to the investigations channel. Keep production monitor thresholds and destinations intact.

1. In Datadog, open the test monitor and use **Test Notifications**. Select its alert transition and group, then **Run Test**. Datadog documents this [monitor test facility](https://docs.datadoghq.com/monitors/notify/#test-notifications).
2. Repeat the metrics command. `runner_deliveries_total{source="datadog",outcome="accepted"}` should increase. A simulated notification with an empty monitor ID, cycle key or transition is rejected as `malformed`; if so, use a controlled real transition on the approved test monitor.
3. Wait for the configured `delaySeconds` and any queue wait. Check `runner_run_total` for completion. A skipped alert appears in `runner_intake_skipped_total` with its reason.
4. Find the test alert's announcement and result thread in the configured Slack investigations channel. Confirm the summary and linked memory record correspond to the test. Accepted delivery alone does not prove completion.
5. Return the test monitor to its normal state and verify the recovery path you selected. Stop the port-forward with Ctrl-C.

`unauthorized`, `too_large`, `malformed` and `intake_error` count rejected deliveries. The runner logs rejections, but no line for accepted deliveries, so metrics are the intake check. `@Tokonoma setup` also shows the last Datadog delivery and its rejection reason, if any.

## Rotating the token

The runner accepts comma-separated tokens. Keep old and new tokens active during the sender change:

1. Update `datadog-webhook-token.txt` to contain the old token, a comma and the new token, with no spaces or trailing newline. Update the Secret with the command below and restart the runner.
2. Put only the new token in `tokonoma-datadog.tfvars`. Repeat the Terraform plan and apply steps, then verify a delivery.
3. Put only the new token in `datadog-webhook-token.txt`. Repeat the Secret update and restart commands.

Run this on the administration workstation after each token-file edit:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-runner-datadog-webhook \
  --from-file=token="REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt" \
  --dry-run=client -o yaml | kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma apply -f -
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout restart deployment/toko-runner
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deployment/toko-runner
```

Expected result: the Secret is configured and the runner Deployment successfully rolls out.

The Datadog token is separate from the Alertmanager one, so rotating or revoking either leaves the
other untouched.

## Stricter network options

Datadog uses bearer tokens, not webhook signatures. To restrict source networks, configure one of these outside the chart:

- **A WAF rule on the shared load balancer:** admit `/webhooks/datadog` only from the `webhooks` ranges in `https://ip-ranges.REPLACE_WITH_DATADOG_SITE`, for example `https://ip-ranges.datadoghq.com`. This retains one Ingress.
- **A separate Ingress for `toko-runner`:** supply its hostname, certificate, and inbound CIDR restriction (`alb.ingress.kubernetes.io/inbound-cidrs` on ALB). Set `runner.ingress.enabled: false` and use that hostname in the webhook URL.

Do not put `inbound-cidrs` on the MCP Ingress itself: it applies to every path, so it would lock
your users out of the MCP.

## Troubleshooting

The runner answers each rejected delivery with a status code and counts it in
`runner_deliveries_total{source="datadog"}`; `@Tokonoma setup` shows the last rejection's reason.

| Symptom | Cause |
|---|---|
| `401`, `outcome="unauthorized"` | The webhook's `Authorization` header does not match the runner's token. Check the custom variable's value against the Secret, and that the header is `Bearer $TOKONOMA_TOKEN`. |
| `404`, nothing counted | Nothing reached the runner's Datadog route. The image may predate 0.64.0; the URL may not match the `Exact` path (for example, a trailing slash); or runner ingress is disabled or `webhookPaths` omits `/webhooks/datadog`, so the MCP answered instead. |
| `502` or `503` | The Ingress reached the runner Service and found no ready pod: the runner is starting, is in `CreateContainerConfigError` because a named Secret does not exist, or is in CrashLoopBackOff because it cannot reach Postgres. `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods -l app.kubernetes.io/component=runner` says which. |
| `413`, `outcome="too_large"` | The body is over 64 KiB. Observed deliveries are about 3.5 KB; a monitor message long enough to hit this needs shortening. Datadog does not retry it. |
| `400`, `outcome="malformed"` | The payload differs from the template above, often Datadog's default payload, which lacks `cycle_key`. Not retried; fix the template and the next transition delivers. |
| Accepted, no investigation | Expected within `delaySeconds`, for a monitor that recovers inside it, and for up to `maxWaitSeconds` more while every slot is busy. Otherwise `runner_intake_skipped_total` names the reason: severity filter, dedup, prior art, a cap, a recovery that arrived while the alert was still waiting, or an alert found too old to run after a restart. |
| Ingress rejected on upgrade | Check the Kubernetes or ingress-controller error and use valid [Kubernetes Ingress paths](https://kubernetes.io/docs/concepts/services-networking/ingress/#path-types). A nonempty runner selection also needs MCP Ingress enabled. |

Return to [alert investigations](alert-investigations.md) or [integrations](../integrations.md).
