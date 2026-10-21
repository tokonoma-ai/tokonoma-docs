# Public MCP Ingress

Keep the MCP endpoint private during initial setup. Before allowing shared or public access, prepare the identity provider and authentication values using [OAuth](oauth.md), [Google SAML](google-saml.md), or [Okta SAML](okta-saml.md). Without authentication, anyone who reaches the endpoint can use its tools, including memory writes.

You need Helm 3.14+, a working ingress controller, DNS control, and a valid TLS certificate. Start with `values.yaml` from the [installation guide](install.md#2-prepare-your-files). Merge authentication and ingress settings into that file before deploying.

Run commands beside `values.yaml` on a workstation with cluster access. Follow [input conventions](install.md#inputs-and-placeholders); keep secret contents out of chat.

| Input | Where to get it | When needed |
| --- | --- | --- |
| `REPLACE_WITH_KUBE_CONTEXT`, installation values and license file | Your installation record and protected secret directory | Before cluster commands |
| `REPLACE_WITH_MCP_HOSTNAME` and DNS access | Your DNS owner | Before preparing routing values |
| Ingress controller and its class | Your platform team | Before selecting one controller example |
| Certificate and issuer or ACM certificate ARN | Your certificate administrator or cloud console | Before deployment |
| Complete authentication settings in `values.yaml` with `mcp.auth.enabled: true` | The selected authentication guide above | Before exposing the endpoint |

Complete the [cluster checks](install.md#1-check-prerequisites), then set these keys in `values.yaml`, preserving the other `mcp` settings:

```yaml
domain: REPLACE_WITH_MCP_HOSTNAME
mcp:
  auth:
    enabled: true
```

## 1. Save the values for your controller

Merge one controller block into `values.yaml` under the existing `mcp` key.

### nginx

```yaml
mcp:
  ingress:
    enabled: true
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: REPLACE_WITH_CLUSTER_ISSUER
      nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    tls:
      enabled: true
      secretName: toko-mcp-tls
```

Point DNS at the ingress-nginx load balancer. The named cert-manager `ClusterIssuer` must already exist.

### AWS ALB on EKS

```yaml
mcp:
  ingress:
    enabled: true
    className: alb
    annotations:
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
      alb.ingress.kubernetes.io/certificate-arn: REPLACE_WITH_ACM_CERTIFICATE_ARN
      alb.ingress.kubernetes.io/healthcheck-path: /health
    tls:
      enabled: false
```

Request the ACM certificate first, then point Route 53 or your DNS provider at the ALB hostname. ALB terminates TLS before forwarding to the Service.

### GKE GCE

[Prepare the namespace](credentials.md#prepare-the-namespace-for-secrets) before creating these resources.

Save the certificate and health check as `tokonoma-gke-prerequisites.yaml`:

```yaml
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: toko-mcp-cert
spec:
  domains:
    - REPLACE_WITH_MCP_HOSTNAME
---
apiVersion: cloud.google.com/v1
kind: BackendConfig
metadata:
  name: toko-mcp
spec:
  healthCheck:
    type: HTTP
    port: 8000
    requestPath: /health
```

Apply the file:

```sh
kubectl --context "REPLACE_WITH_KUBE_CONTEXT" -n tokonoma apply -f tokonoma-gke-prerequisites.yaml
```

```yaml
mcp:
  service:
    annotations:
      cloud.google.com/neg: '{"ingress":true}'
      cloud.google.com/backend-config: '{"default":"toko-mcp"}'
  ingress:
    enabled: true
    className: gce
    annotations:
      networking.gke.io/managed-certificates: toko-mcp-cert
    tls:
      enabled: false
```

The chart renders `className: gce` as the annotation required by the GKE controller. Point DNS at the Ingress IP after GKE allocates it. Follow Google's [HTTPS Ingress documentation](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/secure-traffic-management#disabling_http) for certificate provisioning. Once the certificate and load balancer are active, add `kubernetes.io/ingress.allow-http: "false"` to `mcp.ingress.annotations` and upgrade again. Keep webhook senders disabled until you verify HTTPS-only access.

### Traefik

```yaml
mcp:
  ingress:
    enabled: true
    className: traefik
    annotations:
      cert-manager.io/cluster-issuer: REPLACE_WITH_CLUSTER_ISSUER
    tls:
      enabled: true
      secretName: toko-mcp-tls
```

Point DNS at the Traefik load balancer. The named cert-manager `ClusterIssuer` must already exist. Configure the controller to reject or redirect plain HTTP to HTTPS.

## 2. Deploy

For a first installation, [install Tokonoma](install.md#3-install) with the prepared file and credentials. For an existing release, [apply the configuration change](upgrading.md#before-changing-configuration), preserving required credential inputs and Secret references. After Helm reports `STATUS: deployed`, verify the route, certificate, and authentication below.

## 3. Verify and connect

```sh
curl -fsS https://REPLACE_WITH_MCP_HOSTNAME/health
```

Expect `ok`. Verify that the MCP endpoint requires authentication:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://REPLACE_WITH_MCP_HOSTNAME/mcp
```

Expect `401` before login. Also verify the plain HTTP URL is rejected or redirects to HTTPS before sending credentials or webhooks.

Follow [Connect a coding agent](coding-agents.md#use-a-public-endpoint) with
`https://REPLACE_WITH_MCP_HOSTNAME/mcp`, then complete the browser login in your agent.

Return to the [access choices](private-access.md) if the endpoint should stay private.
