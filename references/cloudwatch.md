# Connect Amazon CloudWatch

Tokonoma queries CloudWatch metrics, alarms, and Logs Insights through the [AWS Labs CloudWatch MCP server](https://awslabs.github.io/mcp/servers/cloudwatch-mcp-server). That server runs only as a local `stdio` process, and the runner connects only to remote Streamable HTTP servers. This guide runs it in the release namespace behind [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy), which serves it over HTTP and requires a bearer token. You build and operate this image; it is not part of the Tokonoma chart.

Use the shared [MCP connection rules](integrations.md#mcp-connections) for names, tools, and credentials. This connection supplies telemetry query access for [Agentic Monitoring](agentic-monitoring.md) and [automatic investigations](alert-investigations.md). It does not deliver CloudWatch alarms to the runner.

## Before you start

Collect these with the AWS account owner:

| Input | Notes |
| --- | --- |
| AWS account and region | The region holding the cluster's CloudWatch data. One server queries one region. |
| Monitored cluster name | The `ClusterName` value in Container Insights. This becomes `runner.detection.scope.cluster`. |
| Kubernetes identity for AWS | EKS Pod Identity (the `eks-pod-identity-agent` add-on) or IAM roles for service accounts (IRSA). |
| Container registry | Where you push the image built below, reachable from the cluster's nodes. |

Kubernetes monitoring needs Container Insights data: the `ContainerInsights` metric namespace and the `/aws/containerinsights/REPLACE_WITH_CLUSTER_NAME/` log groups. Without it, CloudWatch holds AWS service metrics but no pod or namespace data. Check what already exists before changing anything:

```sh
aws cloudwatch list-metrics --region REPLACE_WITH_REGION --namespace ContainerInsights \
  --dimensions Name=ClusterName,Value=REPLACE_WITH_CLUSTER_NAME --max-items 5
aws logs describe-log-groups --region REPLACE_WITH_REGION \
  --log-group-name-prefix /aws/containerinsights/REPLACE_WITH_CLUSTER_NAME
```

If both return nothing, Container Insights must be enabled before monitoring can cover the cluster; ask the customer before adding it. On EKS this is the `amazon-cloudwatch-observability` add-on. That add-on enables Application Signals by default, which injects auto-instrumentation into every pod as it restarts. Unless the customer wants Application Signals, set this configuration when installing the add-on:

```json
{"applicationSignals":{"enabled":false},"manager":{"applicationSignals":{"autoMonitor":{"monitorAllServices":false}}}}
```

Fluent Bit creates the Container Insights log groups without retention. Agree a retention period with the customer.

### Query costs

Monitoring evaluates every check about every five minutes. A check on Logs Insights scans the matching log data on each evaluation, and Logs Insights is billed per GB scanned. A check on metrics reads through `GetMetricData`, which costs far less for the same quantity. Setup plans a quantity on metrics where CloudWatch has it both ways, and keeps log-only signals, such as error lines and patterns, on Logs Insights. Review the [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) with the account owner.

## 1. Build the image

Pin both packages. `--exclude-newer` also pins every dependency resolved at build time:

```dockerfile
FROM ghcr.io/astral-sh/uv:0.8.22-python3.12-bookworm-slim
ENV UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_PREFERENCE=only-system \
    UV_NO_CACHE=1
RUN uv tool install --exclude-newer 2026-11-10 mcp-proxy==0.15.0 \
 && uv tool install --exclude-newer 2026-11-10 awslabs.cloudwatch-mcp-server==0.3.1
USER 65532:65532
ENTRYPOINT ["mcp-proxy"]
```

Inbound bearer authentication requires mcp-proxy 0.15.0 or later. Build for the nodes' architecture and push to your registry:

```sh
docker build --platform linux/amd64 -t REPLACE_WITH_REGISTRY/cloudwatch-mcp:0.3.1 .
docker push REPLACE_WITH_REGISTRY/cloudwatch-mcp:0.3.1
```

## 2. Create a read-only AWS role

Grant read access only. These are the actions the permitted tools use:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "cloudwatch:GetMetricData", "cloudwatch:ListMetrics",
      "cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmHistory",
      "logs:DescribeLogGroups", "logs:DescribeQueryDefinitions",
      "logs:ListLogAnomalyDetectors", "logs:ListAnomalies", "logs:GetLogGroupFields",
      "logs:StartQuery", "logs:GetQueryResults", "logs:StopQuery"
    ],
    "Resource": "*"
  }]
}
```

`logs:StopQuery` cancels the server's own queries. To restrict logs access, replace `Resource` for the `logs:` actions with the cluster's log group ARNs.

With EKS Pod Identity, save the policy as `cloudwatch-read.json` and this trust policy as `pod-identity-trust.json`:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"pods.eks.amazonaws.com"},"Action":["sts:AssumeRole","sts:TagSession"]}]}
```

Then create the role and associate it with the server's service account:

```sh
aws iam create-role --role-name REPLACE_WITH_ROLE_NAME \
  --assume-role-policy-document file://pod-identity-trust.json
aws iam put-role-policy --role-name REPLACE_WITH_ROLE_NAME \
  --policy-name cloudwatch-read --policy-document file://cloudwatch-read.json
aws eks create-pod-identity-association --region REPLACE_WITH_REGION \
  --cluster-name REPLACE_WITH_HOSTING_CLUSTER_NAME --namespace tokonoma \
  --service-account cloudwatch-mcp --role-arn arn:aws:iam::REPLACE_WITH_ACCOUNT_ID:role/REPLACE_WITH_ROLE_NAME
```

The hosting cluster is the one running Tokonoma; it can differ from the monitored cluster. With IRSA, use the cluster's OIDC trust policy instead and annotate the service account below with `eks.amazonaws.com/role-arn`. For CloudWatch data in another account, grant the role access there and confirm the setup with the account owner.

## 3. Create the caller token

The proxy and the runner share one random token. Generate it locally into a Secret; nobody needs to see its value:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma create secret generic toko-cloudwatch-mcp \
  --from-literal=token="$(openssl rand -hex 32)"
```

## 4. Deploy the server

Save this as `cloudwatch-mcp.yaml`, replace the placeholders, and apply it:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cloudwatch-mcp
  namespace: tokonoma
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudwatch-mcp
  namespace: tokonoma
  labels: {app: cloudwatch-mcp}
spec:
  replicas: 1
  selector:
    matchLabels: {app: cloudwatch-mcp}
  template:
    metadata:
      labels: {app: cloudwatch-mcp}
    spec:
      serviceAccountName: cloudwatch-mcp
      securityContext: {runAsNonRoot: true}
      containers:
        - name: cloudwatch-mcp
          image: REPLACE_WITH_REGISTRY/cloudwatch-mcp:0.3.1
          args:
            - --host=0.0.0.0
            - --port=8000
            # The Host the runner sends; requests with any other Host get 421.
            - --allowed-host=cloudwatch-mcp.tokonoma.svc:8000
            - --pass-environment
            - --
            - awslabs.cloudwatch-mcp-server
          env:
            # The server reads AWS_DEFAULT_REGION. With only AWS_REGION set,
            # every tool silently queries us-east-1.
            - {name: AWS_DEFAULT_REGION, value: REPLACE_WITH_REGION}
            - {name: AWS_REGION, value: REPLACE_WITH_REGION}
            - {name: FASTMCP_LOG_LEVEL, value: ERROR}
            - name: MCP_PROXY_AUTH_TOKEN
              valueFrom:
                secretKeyRef: {name: toko-cloudwatch-mcp, key: token}
          ports:
            - {name: http, containerPort: 8000}
          # HTTP health routes also require the token, so probe the socket.
          readinessProbe:
            tcpSocket: {port: http}
            periodSeconds: 10
          resources:
            requests: {cpu: 50m, memory: 256Mi}
            limits: {memory: 768Mi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: cloudwatch-mcp
  namespace: tokonoma
spec:
  selector: {app: cloudwatch-mcp}
  ports:
    - {name: http, port: 8000, targetPort: http}
```

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT apply -f cloudwatch-mcp.yaml
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma rollout status deploy/cloudwatch-mcp
```

Keep the Service private (`ClusterIP`). If the release uses another namespace, change it everywhere above, including `--allowed-host`.

## 5. Connect the runner

Add this entry to the existing `runner.mcpServers` list in your saved values file:

```yaml
runner:
  mcpServers:
    - name: cloudwatch
      kind: telemetry
      url: http://cloudwatch-mcp.tokonoma.svc:8000/mcp
      authSecretRef:
        name: toko-cloudwatch-mcp
        key: token
      expectedTools:
        - get_metric_data
        - get_metric_metadata
        - analyze_metric
        - get_active_alarms
        - get_alarm_history
        - describe_log_groups
        - analyze_log_group
        - execute_log_insights_query
        - get_logs_insight_query_results
        - cancel_logs_insight_query
```

These are read tools. Leave out `execute_cwl_insights_batch`, which can switch AWS profiles and regions; the PromQL tools, unless the account uses CloudWatch's Prometheus endpoint; and the index recommendation tools.

Set the monitoring scope to the Container Insights cluster name:

```yaml
runner:
  detection:
    scope:
      cluster: REPLACE_WITH_CLUSTER_NAME
      namespaces:
        - REPLACE_WITH_MONITORED_NAMESPACE
```

For a new deployment, use the [installation command](install.md#3-install). For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration).

## 6. Check access

Check that the server refuses callers without the token. In one terminal:

```sh
kubectl --context REPLACE_WITH_KUBE_CONTEXT -n tokonoma port-forward svc/cloudwatch-mcp 8000:8000
```

In another, expect `401`:

```sh
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8000/mcp
```

Then use the shared [access checks](integrations.md#4-check-access). `@Tokonoma admin status` should list `cloudwatch` with no missing tools. Follow [monitoring verification](agentic-monitoring.md#verify-monitoring): setup should report CloudWatch checks for the chosen cluster and namespaces. If setup reports no CloudWatch data while the commands in [Before you start](#before-you-start) return results, check `AWS_DEFAULT_REGION` and the role association first.

## What CloudWatch covers

- **Metrics:** Container Insights pod and container CPU, memory, limits, restarts, network, and running containers, read with Metrics Insights queries. These can look back two weeks.
- **Logs:** Logs Insights over the Container Insights application logs: log volume, error and warning lines, patterns, and request status or latency where services log them.
- **Alarms:** active alarms and alarm history.

Known gaps, reported as coverage gaps rather than healthy services:

- No Kubernetes inventory or events tools. Setup finds workloads from Container Insights dimensions; Kubernetes events are not available.
- Request rate, error rate, and latency only where services publish metrics or log them.
- No traces. X-Ray and Application Signals use a separate AWS Labs server that this guide does not cover.

## Rotate or remove

To rotate the token, replace the `toko-cloudwatch-mcp` Secret, then restart both `deploy/cloudwatch-mcp` and the runner. To upgrade the server, rebuild with new pinned versions and update the image tag.

To remove the connection, delete its `runner.mcpServers` entry and apply the configuration, then delete the manifest, the Secret, the pod identity association, and the role.
