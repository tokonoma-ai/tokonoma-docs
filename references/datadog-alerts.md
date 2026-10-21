# Datadog alerts

`toko-runner` investigates eligible Datadog notifications and saves its findings. With Slack configured, it also posts results there. The shared [runner guardrails](alert-investigations.md#guardrails) apply; Datadog has its own delay, severity filter, and token.

Datadog needs a public HTTPS webhook. The chart routes it through MCP Ingress.

## Before you start

- Prepare the [runner configuration](alert-investigations.md), including its model credential, telemetry query access, and OAuth client when MCP authentication is enabled. Configure Slack if wanted. Datadog-only installations need no Alertmanager token, but at least one source token is required.
- MCP Ingress must serve HTTPS only before Datadog deliveries begin. Prepare its settings with [Public MCP Ingress](public-mcp-ingress.md). The bearer token travels in a header; the chart cannot enforce HTTPS terminated through provider annotations. GKE's GCE controller initially serves HTTP too. Once its certificate and load balancer are active, add `kubernetes.io/ingress.allow-http: "false"` to `mcp.ingress.annotations`, upgrade, and verify HTTPS-only access before enabling deliveries.
- Use Datadog Terraform provider 3.83.0 or later for notification-rule `filter.scope` support. Add the three resources below to your existing project. Outside US1, set your site's API in `provider "datadog"`, for example `api_url = "https://api.us3.datadoghq.com/"`.
- Use credentials with read and write access to webhooks, custom variables, and notification rules. Terraform reads resources after creation and during refresh, so write-only keys fail. Verify permissions against your organization's role policy.

## Inputs and files

Prepare the token and settings before [installation](install.md#3-install). Use your existing Datadog Terraform project and the [installation inputs](install.md#inputs-and-placeholders).

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_MCP_HOSTNAME` | Public HTTPS host selected in [ingress setup](public-mcp-ingress.md) | Datadog deliveries |
| `REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY` | Existing Terraform project with your Datadog provider and credentials | Provider setup below |
| `REPLACE_WITH_DATADOG_WEBHOOK_TOKEN` | Generated token from step 1, also copied into the protected Terraform variable file | Both ends of webhook authentication |

Step 1 creates the protected token file. Step 3 creates `tokonoma.tf` in your Terraform project and variable and plan files in your [protected credential directory](credentials.md#supply-tokens-from-files).

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

> On GKE, set `runner.service.annotations` to include `cloud.google.com/neg: '{"ingress": true}'`, as in the [GKE Ingress guide](public-mcp-ingress.md#gke-gce). Health checks use the `/health` readiness probe; an optional `BackendConfig` can set them explicitly through the same annotation mechanism. `pathType: Exact` on GCE remains unverified.

## 1. Create the token

The runner's Kubernetes Secret and Datadog custom variable must contain the same token. Generate it in the protected directory for first setup only. Preserve existing tokens on upgrades; use [rotation](#rotating-the-token) to change one:

```sh
umask 077
openssl rand -hex 32 | tr -d '\n' > "REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt"
```

Use all 32 bytes for this public route; shorter tokens cause a startup warning.

[Prepare the release namespace](credentials.md#prepare-the-namespace-for-secrets), then create the token Secret:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT create secret generic toko-runner-datadog-webhook -n tokonoma \
  --from-file=token="REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt"
```

Expected output: `secret/toko-runner-datadog-webhook created`. If it already exists, preserve it and confirm its owner and token through your secret-management workflow. Use [rotation](#rotating-the-token) for an intended token change.

## 2. Configure the runner

In `values.yaml`, uncomment the Datadog source and public webhook settings in the [example](../examples/values.yaml). Set `runner.sources.datadog.tokenSecretRef.name` to `toko-runner-datadog-webhook` and `.key` to `token`. Set `runner.ingress.webhookPaths` to `[/webhooks/datadog]`, or keep both paths if you also receive Alertmanager alerts.

Keep `mcp.auth.enabled: true`, the identity-provider settings, and HTTPS ingress in the same file. Configure the runner's OAuth client with the [runner guide](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled). Datadog-only installations omit the Alertmanager credential; retain any source credentials already in use.

Configure telemetry query access separately using the [general MCP guide and Datadog example](integrations.md#datadog-example), or another selected telemetry integration. The Datadog webhook token only authenticates notifications; it does not grant query access.

After all selected integrations are prepared, use the [installation command](install.md#3-install). For an existing deployment, [apply the configuration change](upgrading.md#before-changing-configuration).

Missing source tokens prevent rendering, and missing referenced Secrets cause `CreateContainerConfigError`. Verify the HTTPS endpoint before enabling Datadog deliveries in step 3.

The token configuration enables the receiver; ingress publishes it. `webhookPaths` replaces earlier lists and defaults to `[]`. Include both paths and tokens to retain [Alertmanager exposure](alert-investigations.md#external-alertmanager-or-grafana-alerting). Health and metrics remain private.

Datadog source defaults:

| Value | Default | What it does |
|---|---|---|
| `runner.sources.datadog.delaySeconds` | `60` | Wait before investigating; alerts that recover during the wait are skipped |
| `runner.sources.datadog.filters.severities` | `[critical, warning]` | Datadog `error` alerts are `critical`, `warning` alerts are `warning`. Empty means all. |
| `runner.sources.datadog.serviceLabels` | `[service, task_family, kube_deployment, kube_stateful_set, kube_daemon_set, kube_service]` | Ordered tags used to identify the service. A missing service name does not prevent investigation. |

This source has no namespace filter. The notification rule's scope below controls which alerts arrive, using all tags on the notification.

## 3. Configure Datadog

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

Replace `REPLACE_WITH_MCP_HOSTNAME` with your MCP hostname. Verify a real delivery with your monitor text before using it broadly; Datadog must substitute and escape every payload value correctly.

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

The default rule sends every transition. Recovery and no-data notifications are not investigated. With Slack delivery enabled, they produce an announcement and a *"resolved notification, nothing to investigate"* reply.

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

Append `tokonoma:investigate` to each selected monitor's tags after saving the notification rule. Preserve all other tags, queries, thresholds, and destinations:

```hcl
resource "datadog_monitor" "payments_errors" {
  # ...
  tags = ["env:prod", "team:payments", "tokonoma:investigate"]
}
```

You can also scope the rule on existing tags such as `env:prod AND team:payments`
or a group tag such as `kube_namespace:checkout`. Keyless tags and partial
wildcards are not supported in a rule scope.

For ECS and Kubernetes together, scope on shared tags such as `env:`, `team:`, and `service:`, or combine platform tags: `kube_namespace:checkout OR ecs_cluster_name:prod-checkout`. A Kubernetes-only scope excludes ECS. Set `service:` on both platforms for consistent service names; ECS otherwise falls back to `task_family`.

> The ECS tag names here (`task_family`, `ecs_cluster_name`) come from the Datadog Agent's ECS
> documentation and have not been verified against a real ECS notification. Check one of your
> ECS monitors' `$TAGS` before relying on them.

### Caveats

- For existing monitors, save the notification rule before creating or updating the monitors it should match. Adding the opt-in tag is one way to make that update. Validate a real transition before relying on the rule.
- A new group in a multi-alert monitor notifies after the monitor's
  `new_group_delay` (60 s by default), on top of Datadog's own delivery latency of about a minute.
- Datadog retries a 5xx or timeout, but not a 4xx. A test notification with an empty `monitor_id`, `cycle_key`, or `transition` is rejected with 400; use a controlled real monitor transition if that occurs.
- Use each group variable in a multi-alert monitor’s name to avoid Datadog appending a long group description. The runner identifies the alert by monitor and group, not its display title.

The rule's `recipients` entry is `webhook-REPLACE_WITH_WEBHOOK_NAME`, unlike the `@webhook-REPLACE_WITH_WEBHOOK_NAME` mention in a monitor message. The supplied example uses `tokonoma` as that name.

## 4. Verify

These optional checks run after installation. Follow the [runner deployment check](alert-investigations.md#check-the-deployment) to open a port-forward and record the current metrics. Keep that connection open for the test below.

Use one operator-approved test monitor that matches the notification rule. It must be allowed to make model calls and post to any configured destination. Keep production monitor thresholds and destinations intact.

1. In Datadog, open the test monitor and use **Test Notifications**. Select its alert transition and group, then **Run Test**. Datadog documents this [monitor test facility](https://docs.datadoghq.com/monitors/notify/#test-notifications).
2. Repeat the metrics command. `runner_deliveries_total{source="datadog",outcome="accepted"}` should increase. A simulated notification with an empty monitor ID, cycle key or transition is rejected as `malformed`; if so, use a controlled real transition on the approved test monitor.
3. Wait for the configured `delaySeconds` and any queue wait. Check `runner_run_total` for completion. A skipped alert appears in `runner_intake_skipped_total` with its reason.
4. With Slack configured, find the test alert's announcement and result thread. Confirm the summary and linked memory record correspond to the test. Without Slack, find the saved investigation through your connected coding agent as described in [runner verification](alert-investigations.md#send-one-controlled-alert-and-verify-its-result). Accepted delivery alone does not prove completion.
5. Return the test monitor to its normal state and verify the recovery path you selected. Stop the port-forward with Ctrl-C.

`unauthorized`, `too_large`, `malformed` and `intake_error` count rejected deliveries. The runner logs rejected deliveries only. Use metrics to check accepted deliveries. `@Tokonoma setup` also shows the last Datadog delivery and its rejection reason, if any.

## Rotating the token

The runner accepts comma-separated tokens. Keep old and new tokens active during the sender change:

1. Update `datadog-webhook-token.txt` to contain the old token, a comma and the new token, with no spaces or trailing newline. Update the Secret with the command below and [restart the runner](credentials.md#renew-and-rotate).
2. Put only the new token in `tokonoma-datadog.tfvars`. Repeat the Terraform plan and apply steps, then verify a delivery.
3. Put only the new token in `datadog-webhook-token.txt`. Repeat the Secret update and runner restart.

Run this on the administration workstation after each token-file edit:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-runner-datadog-webhook \
  --from-file=token="REPLACE_WITH_SECRET_DIRECTORY/datadog-webhook-token.txt" \
  --dry-run=client -o yaml | kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma apply -f -
```

Expected result: the Secret is configured. Complete the runner restart before continuing to the next step.

Datadog and Alertmanager use separate tokens. Rotating or revoking one leaves the other unchanged.

## Stricter network options

Datadog uses bearer tokens, not webhook signatures. To restrict source networks, configure one of these outside the chart:

- Add a WAF rule on the shared load balancer to admit `/webhooks/datadog` only from the `webhooks` ranges in `https://ip-ranges.REPLACE_WITH_DATADOG_SITE`, for example `https://ip-ranges.datadoghq.com`. This retains one Ingress.
- Create a separate Ingress for `toko-runner` with its hostname, certificate, and inbound CIDR restriction (`alb.ingress.kubernetes.io/inbound-cidrs` on ALB). Set `runner.ingress.enabled: false` and use that hostname in the webhook URL.

Do not put `inbound-cidrs` on the MCP Ingress itself: it applies to every path, so it would lock
your users out of the MCP.

## Troubleshooting

The runner answers each rejected delivery with a status code and counts it in
`runner_deliveries_total{source="datadog"}`; `@Tokonoma setup` shows the last rejection's reason.

| Symptom | Cause |
|---|---|
| `401`, `outcome="unauthorized"` | The webhook's `Authorization` header does not match the runner's token. Check the custom variable's value against the Secret, and that the header is `Bearer $TOKONOMA_TOKEN`. |
| `404`, nothing counted | Confirm that the image supports Datadog, runner ingress is enabled, and `webhookPaths` includes `/webhooks/datadog`. The URL must match the exact path without a trailing slash. |
| `502` or `503` | The Ingress reached the runner Service and found no ready pod: the runner is starting, is in `CreateContainerConfigError` because a named Secret does not exist, or is in CrashLoopBackOff because it cannot reach Postgres. `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods -l app.kubernetes.io/component=runner` says which. |
| `413`, `outcome="too_large"` | The body is over 64 KiB. Shorten the monitor message. Datadog does not retry it. |
| `400`, `outcome="malformed"` | The payload differs from the template above, often Datadog's default payload, which lacks `cycle_key`. Not retried; fix the template and the next transition delivers. |
| Accepted, no investigation | Expected within `delaySeconds`, for a monitor that recovers inside it, and for up to `maxWaitSeconds` more while every slot is busy. Otherwise `runner_intake_skipped_total` names the reason: severity filter, dedup, prior art, a cap, a recovery that arrived while the alert was still waiting, or an alert found too old to run after a restart. |
| Ingress rejected on upgrade | Check the Kubernetes or ingress-controller error and use valid [Kubernetes Ingress paths](https://kubernetes.io/docs/concepts/services-networking/ingress/#path-types). A nonempty runner selection also needs MCP Ingress enabled. |

Return to [alert investigations](alert-investigations.md) or [integrations](integrations.md).
