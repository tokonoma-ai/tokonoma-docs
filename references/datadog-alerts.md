# Datadog alerts

The recipe below sends notifications from all Datadog monitors to `toko-runner`. The runner investigates eligible notifications and saves its findings. With Slack configured, it also posts results there. Delay, severity filters, duplicate detection and the shared [runner guardrails](alert-investigations.md#guardrails) still apply; receiving a notification does not guarantee an investigation.

Datadog needs a public HTTPS webhook. Choose a separate webhook route to keep MCP private, or share an existing authenticated MCP Ingress.

When Datadog alert investigations are enabled, connect this route and Datadog notifications during phase 1. Verify a completed automatic investigation, saved record, and configured result delivery before the [phase 1 checkpoint](install.md#check-monitoring-and-integrations) is complete.

## Before you start

- Prepare the [runner configuration](alert-investigations.md), including its model credential, telemetry query access, and OAuth client when MCP authentication is enabled. Configure Slack if wanted. Datadog-only installations need no Alertmanager token, but at least one source token is required.
- Choose a hostname, certificate and ingress controller with your platform team. The webhook must serve HTTPS only before Datadog deliveries begin. Preserve the request path and `Authorization` header; the bearer token travels in that header.
- Use Datadog Terraform provider 3.83.0 or later for notification-rule `filter.scope` support. Add the three resources below to your existing project. Outside US1, set your site's API in `provider "datadog"`, for example `api_url = "https://api.us3.datadoghq.com/"`.
- Use credentials with read and write access to webhooks, custom variables, and notification rules. Terraform reads resources after creation and during refresh, so write-only keys fail. Verify permissions against your organization's role policy.

## Inputs and files

Prepare the token and settings before [installation](install.md#3-install). Use your existing Datadog Terraform project and the [installation inputs](install.md#inputs-and-placeholders).

| Input | Meaning and source | Required when |
|---|---|---|
| `REPLACE_WITH_WEBHOOK_HOSTNAME` | Dedicated webhook hostname, or the existing public MCP hostname | Datadog deliveries |
| `REPLACE_WITH_ISSUED_ACM_CERTIFICATE_ARN` | Issued AWS Certificate Manager certificate covering the webhook hostname | Separate AWS ALB route below |
| `REPLACE_WITH_DATADOG_TERRAFORM_DIRECTORY` | Existing Terraform project with your Datadog provider and credentials | Provider setup below |
| `REPLACE_WITH_DATADOG_WEBHOOK_TOKEN` | Generated token from step 1, also copied into the protected Terraform variable file | Both ends of webhook authentication |

Step 1 creates the protected token file. Step 3 creates `tokonoma.tf` in your Terraform project and variable and plan files in your [protected credential directory](credentials.md#supply-tokens-from-files).

## What is exposed

| Request | Destination |
|---|---|
| Datadog monitor notification | Notification rule, then the `tokonoma` webhook with the configured bearer token |
| HTTPS `POST /webhooks/datadog` | Either route sends the exact path to `toko-runner:8080` |
| Other paths on a separate webhook host | No route; MCP stays private |
| Other paths on shared MCP Ingress | Route to `toko-mcp:8000`, using MCP authentication |
| Runner `/health` and `/metrics` | Cluster-only Service |

The selected `POST /webhooks/datadog` path checks the token before reading the body and rejects unauthenticated requests with `401`. Its body limit is 64 KiB. The webhook token is separate from MCP authentication.

Sharing MCP Ingress reuses its host, certificate, and DNS. With the default Application Load Balancer (ALB) configuration, a separate Ingress creates another load balancer needing its own host and certificate. For a path-specific IP allowlist on a shared route, use a web application firewall (WAF); see [network options](#stricter-network-options).

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

In `values.yaml`, uncomment the Datadog source in the [example](../examples/values.yaml). Set `runner.sources.datadog.tokenSecretRef.name` to `toko-runner-datadog-webhook` and `.key` to `token`. Datadog-only installations omit the Alertmanager credential; retain any source credentials already in use.

Choose one route below before applying the values. A separate webhook does not require MCP OAuth. If MCP authentication is enabled, either route still needs the runner's [OAuth client](alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled).

Configure telemetry query access separately using the [general MCP guide and Datadog example](integrations.md#datadog-example), or another selected telemetry integration. The Datadog webhook token only authenticates notifications; it does not grant query access.

After all selected integrations are prepared, use the [installation command](install.md#3-install). For an existing deployment, [apply the configuration change](upgrading.md#before-changing-configuration).

Missing source tokens prevent rendering, and missing referenced Secrets cause `CreateContainerConfigError`. Verify the HTTPS endpoint before enabling Datadog deliveries in step 3.

### Separate webhook route, private MCP

Keep `mcp.ingress.enabled: false` and `runner.ingress.enabled: false` in `values.yaml`. These switches control the chart's shared ingress; the separate resource below routes directly to the runner Service. MCP may use `mcp.auth.enabled: false` only while its reachable clients are trusted and access is deliberately restricted, as described in [private access](private-access.md).

For an existing AWS Load Balancer Controller, confirm the `alb` class, replace the hostname and certificate ARN, and apply this route after the workloads are ready:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT get ingressclass alb
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma apply -f - <<'YAML'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tokonoma-datadog-webhook
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: REPLACE_WITH_ISSUED_ACM_CERTIFICATE_ARN
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  ingressClassName: alb
  rules:
    - host: REPLACE_WITH_WEBHOOK_HOSTNAME
      http:
        paths:
          - path: /webhooks/datadog
            pathType: Exact
            backend:
              service:
                name: toko-runner
                port:
                  number: 8080
YAML
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get ingress tokonoma-datadog-webhook
```

Point the hostname's DNS record at the reported load balancer. The issued certificate must cover that hostname. For another controller, have the platform team provide an equivalent HTTPS-only exact-path route. Keep `/`, `/mcp` and `/mcp/` off this host.

From outside the cluster, check the certificate and path restrictions without sending a token:

```sh
curl -sS -X POST -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_WEBHOOK_HOSTNAME/webhooks/datadog
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_WEBHOOK_HOSTNAME/mcp
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_WEBHOOK_HOSTNAME/mcp/
```

Expect `401`, `404` and `404`, respectively. Do not connect Datadog if these checks fail. The manifest creates only an HTTPS listener; confirm the public host has no HTTP route that accepts deliveries.

### Shared authenticated MCP Ingress

Use [Public MCP Ingress](public-mcp-ingress.md) to configure the hostname, TLS and identity provider. Keep `mcp.auth.enabled: true` and configure the runner's OAuth client. Set `runner.ingress.enabled: true` and `runner.ingress.webhookPaths: [/webhooks/datadog]`. The token enables the receiver; this path selection publishes it.

`webhookPaths` replaces earlier lists and defaults to `[]`. Include both paths and tokens to retain [Alertmanager exposure](alert-investigations.md#external-alertmanager-or-grafana-alerting). Other paths fall through to MCP. Runner health and metrics remain private.

The chart cannot enforce HTTPS terminated through provider annotations. GKE's GCE controller initially serves HTTP too. Once its certificate and load balancer are active, add `kubernetes.io/ingress.allow-http: "false"` to `mcp.ingress.annotations`, [apply the change](upgrading.md#before-changing-configuration), and verify HTTPS-only access.

Before connecting Datadog, use the first `curl` command above and expect `401`. Also confirm unauthenticated `/mcp` requests receive `401` using the [MCP Ingress checks](public-mcp-ingress.md). Unlike the separate route, this host intentionally serves authenticated MCP clients.

### Source defaults

| Value | Default | What it does |
|---|---|---|
| `runner.sources.datadog.delaySeconds` | `60` | Wait before investigating; a received recovery cancels an alert during the wait |
| `runner.sources.datadog.filters.severities` | `[critical, warning]` | Datadog `error` alerts are `critical`, `warning` alerts are `warning`. Empty means all. |
| `runner.sources.datadog.serviceLabels` | `[service, task_family, kube_deployment, kube_stateful_set, kube_daemon_set, kube_service]` | Ordered tags used to identify the service. A missing service name does not prevent investigation. |

This source has no namespace filter. The notification rule below includes every monitor, across Kubernetes, ECS and other environments.

## 3. Configure Datadog

Check that resources named `tokonoma` below do not already exist in your Terraform project or Datadog organization. Retain managed resources instead of declaring duplicates.

This rule adds Tokonoma as a recipient across all monitors. Preserve existing monitor queries, thresholds, tags, messages and paging destinations. Datadog combines recipients from matching rules; do not replace the rules already in use.

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
  url            = "https://REPLACE_WITH_WEBHOOK_HOSTNAME/webhooks/datadog"
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
  recipients = ["webhook-tokonoma"]
  filter {
    # Match notifications with or without an env tag, including untagged monitors.
    scope = "env:* OR NOT env:*"
  }
  depends_on = [datadog_webhook.tokonoma]
}
```

Replace `REPLACE_WITH_WEBHOOK_HOSTNAME` with the hostname for your selected route. Verify a real delivery with your monitor text before using it broadly; Datadog must substitute and escape every payload value correctly.

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

### All-monitor coverage

`env:* OR NOT env:*` matches notifications whether or not they contain an `env` tag. It needs no opt-in tag and includes untagged monitors. It uses Datadog's supported [`key:*`, `OR` and `NOT` scope syntax](https://docs.datadoghq.com/monitors/notify/notification_rules/#rule-scope-syntax).

After saving the rule, check its **Coverage** and monitor **Recipient Summary** in Datadog. Datadog documents rule application when monitors are created or updated after the rule is saved. If existing monitors are missing, save them through their existing management workflow, preserving their settings. Confirm coverage includes the full monitor inventory before claiming all-monitor routing is active. See [Datadog's notification-rule guide](https://docs.datadoghq.com/monitors/notify/notification_rules/).

### Recovery notifications

The rule sends every transition. Received recoveries can cancel delayed or queued investigations. Recovery and no-data notifications do not start investigations. The runner also skips episodes already investigated. Test both firing and recovery transitions.

### Caveats

- Validate a real alert or warning transition after confirming all-monitor coverage. A successful test on one monitor does not prove coverage of the others.
- A new group in a multi-alert monitor notifies after the monitor's
  `new_group_delay` (60 s by default), on top of Datadog's own delivery latency of about a minute.
- Datadog retries a 5xx or timeout, but not a 4xx. A test notification with an empty `monitor_id`, `cycle_key`, or `transition` is rejected with 400; use a controlled real monitor transition if that occurs.
- Use each group variable in a multi-alert monitor’s name to avoid Datadog appending a long group description. The runner identifies the alert by monitor and group, not its display title.

The rule's `recipients` entry is `webhook-REPLACE_WITH_WEBHOOK_NAME`, unlike the `@webhook-REPLACE_WITH_WEBHOOK_NAME` mention in a monitor message. The supplied example uses `tokonoma` as that name.

## 4. Verify

Complete these checks during phase 1 when Datadog alert investigations are enabled. Follow the [runner deployment check](alert-investigations.md#check-the-deployment) to open a port-forward and record the current metrics. Keep that connection open for the test below.

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
- Use the [separate webhook route](#separate-webhook-route-private-mcp) with its hostname, certificate, and inbound CIDR restriction (`alb.ingress.kubernetes.io/inbound-cidrs` on ALB).

Do not put `inbound-cidrs` on the MCP Ingress itself: it applies to every path, so it would lock
your users out of the MCP.

## Troubleshooting

The runner answers each rejected delivery with a status code and counts it in
`runner_deliveries_total{source="datadog"}`; `@Tokonoma setup` shows the last rejection's reason.

| Symptom | Cause |
|---|---|
| `401`, `outcome="unauthorized"` | The webhook's `Authorization` header does not match the runner's token. Check the custom variable's value against the Secret, and that the header is `Bearer $TOKONOMA_TOKEN`. |
| `404`, nothing counted | Confirm the image supports Datadog and the URL is exactly `/webhooks/datadog`, without a trailing slash. For a separate route, check its host and `toko-runner:8080` backend. For shared ingress, check `runner.ingress.enabled` and `webhookPaths`. |
| `502` or `503` | The Ingress reached the runner Service and found no ready pod: the runner is starting, is in `CreateContainerConfigError` because a named Secret does not exist, or is in CrashLoopBackOff because it cannot reach Postgres. `kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma get pods -l app.kubernetes.io/component=runner` says which. |
| `413`, `outcome="too_large"` | The body is over 64 KiB. Shorten the monitor message. Datadog does not retry it. |
| `400`, `outcome="malformed"` | The payload differs from the template above, often Datadog's default payload, which lacks `cycle_key`. Not retried; fix the template and the next transition delivers. |
| Accepted, no investigation | Expected within `delaySeconds`, for a monitor that recovers inside it, and for up to `maxWaitSeconds` more while every slot is busy. Otherwise `runner_intake_skipped_total` names the reason: severity filter, dedup, prior art, a cap, a recovery that arrived while the alert was still waiting, or an alert found too old to run after a restart. |
| Ingress rejected on upgrade | Check the Kubernetes or ingress-controller error and use valid [Kubernetes Ingress paths](https://kubernetes.io/docs/concepts/services-networking/ingress/#path-types). The chart's shared runner ingress needs MCP Ingress enabled; a separate route keeps both chart ingress switches disabled. |

Return to [alert investigations](alert-investigations.md) or [integrations](integrations.md).
