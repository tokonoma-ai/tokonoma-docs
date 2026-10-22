# Install and use Tokonoma

## 1. Overview

Tokonoma monitors your services, detects significant changes, and automatically investigates findings and alerts using your observability tools. Engineers can work with it through Slack and coding agents, using saved findings and procedures to build on what the team has learned.

Agentic Monitoring checks telemetry without waiting for an alert, while automatic investigations use the full alert stream from connected sources. Both are enabled by default in this installation, and your agent will ask whether you want to turn either off for a phased setup. You choose which integrations Tokonoma can access and where it posts in Slack.

```mermaid
flowchart LR
  accTitle: Tokonoma in your environment
  accDescr: Coding agents connect to Tokonoma. All customer alerts from connected sources reach the required Tokonoma runner for automatic investigations. The runner also queries integrations for Agentic Monitoring independently of incoming alerts. Tokonoma runs on Kubernetes; monitored services can run elsewhere. Tokonoma connects to Slack and the Anthropic API. The runner connects to the Anthropic API and permitted integrations. Arrows show who opens each external connection.
  subgraph Inputs["Incoming connections"]
    Agents["Coding agents"]
    Alerts["Incoming alerts<br/>All customer alerts"]
  end
  subgraph Cluster["Tokonoma installation (Kubernetes)"]
    Tokonoma["Tokonoma<br/>Investigation tools and memory"]
    Runner["Tokonoma runner<br/>Agentic Monitoring<br/>Automatic investigations"]
  end
  subgraph Connections["Services you configure"]
    Slack["Slack"]
    Models["Anthropic API"]
    Tools["Integrations<br/>(Telemetry, Alerting, Code)"]
  end
  Agents --> Tokonoma
  Alerts --> Runner
  Tokonoma -->|"Messages"| Slack
  Tokonoma -->|"Analysis"| Models
  Runner -->|"Model calls"| Models
  Runner -->|"Monitor and investigate"| Tools

  classDef service fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e,stroke-width:2px
  classDef external fill:#fff,stroke:#64748b,color:#0f172a
  class Tokonoma,Runner service
  class Agents,Alerts,Slack,Tools,Models external
  style Cluster fill:#eff6ff,stroke:#0369a1,color:#0c4a6e
  style Inputs fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style Connections fill:#f8fafc,stroke:#cbd5e1,color:#334155
```

The installation includes Tokonoma's Model Context Protocol (MCP) service, the required runner and its dedicated MCP instance, bundled PostgreSQL for records and state, and Ollama for local search embeddings (numeric representations of text).

Your agent follows the [installation guide](references/install.md) to configure these services and your [selected integrations](references/integrations.md) through the published Helm chart and one `values.yaml`. Compatible MCP tools provide telemetry and code access, while the chart supplies application image defaults without requiring a specific release version or access to the application source.

The Anthropic API receives investigation context; the [data flows guide](references/data-flows.md) explains which services make external calls, where they connect, and what network access they need.

## 2. Before you start

Gather these inputs for phase 1. Your agent reuses existing configuration and asks for missing inputs in one batch. For credentials already stored in Kubernetes, provide Secret names and keys.

### Phase 1: installation

Install the bundled services, monitoring, automatic investigations, Slack, and the runner's machine login. MCP stays inside the cluster, with a local port-forward for operator access. The shared hostname and human sign-in can wait until phase 2.

**What you'll have:** Tokonoma running in your cluster, detectors monitoring your services, and connected alerts being investigated automatically, with results saved and posted to Slack. Your agent will [check that everything is working](references/install.md#check-monitoring-and-integrations) before you move on to team access.

#### Required: deployment and access

| What | Why |
| --- | --- |
| Cloud provider and Kubernetes context | Choose where to install Tokonoma. |
| Release name and installation namespace | Name the installation; both default to `tokonoma`. |
| Installer, platform contact, and identity administrator | Arrange [cluster access](references/install.md#1-check-prerequisites) and runner login. |
| Tokonoma license | Read complete saved records. |
| Anthropic API key | Power monitoring, investigations, and memory analysis. |
| [Cognito machine-to-machine Client ID](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled) with `toko-mcp/query` access | Identify the runner's machine login. |
| Cognito Client Secret | Authenticate the runner. |
| Cognito user pool ID, region, and domain prefix | Locate the [credential provider](references/oauth.md#1-prepare-the-provider). |
| [Slack Bot Token](references/slack-app.md#create-the-app) (`xoxb-`) | Post answers and investigation results. |
| Slack App Token (`xapp-`) with `connections:write` | Receive Slack messages without a public endpoint. |
| Slack workspace, app owner, and channel with `@Tokonoma` invited | Install the app from our [manifest](examples/slack-app-manifest.yaml). |
| Approval for selected [external data flows](references/data-flows.md#model-and-integration-connections) | Control which context reaches external services. |

For existing legacy Google Identity Platform/Firebase, runner account email, password, and project API key replace the Cognito inputs.

#### Required: monitoring and investigations

| What | Why |
| --- | --- |
| [Cluster name from your telemetry](references/agentic-monitoring.md#prepare-the-inputs) | Tell Tokonoma which cluster to monitor. |
| [Each connected system's MCP endpoint URL](references/integrations.md#mcp-connections) | Access available logs, metrics, traces, alerts, and Kubernetes data. |
| MCP authentication method and credentials | Authenticate telemetry queries. |
| MCP region/site, organization, and dataset IDs, where applicable | Select the correct source data. |
| Allowed read-only MCP tool names | Restrict Tokonoma to approved queries. |
| Grafana URL and Viewer service-account token, if using the [bundled adapter](references/alert-investigations.md#install-with-oss-grafana-mcp) | Read existing Grafana data sources. |
| Alert provider, routing configuration, owner, and current destinations | Connect alerts and preserve paging routes. |
| [Alertmanager](references/alert-investigations.md#before-you-start) or [Datadog](references/datadog-alerts.md) receiver token | Authenticate incoming alerts. |
| External alert webhook hostname and route, if needed | [Receive external alerts](references/private-access.md#slack-and-webhooks) while MCP stays private. |
| Approval for a source-side test alert | Verify automatic investigation and Slack delivery. |
| Deployment system, event source, repository/workflow, and read access | Watch releases and related issues. |

No existing alerts: say **none**; a receiver token is still needed. Confirm deployment-event support with Tokonoma. Axiom annotations need read access; code access alone does not deliver events.

#### Optional additions

| What | Why |
| --- | --- |
| Namespace to monitor | Limit monitoring; otherwise all namespaces, including system ones, are watched. |
| [GitHub token](references/integrations.md#github-example), approved repositories, and directory paths | Read relevant code and history during investigations. |
| Runbooks, investigation skills, past incidents, and expected behavior | Add your [operational context](references/coding-agents.md#3-onboard-your-coding-agent). |
| Typesafe/Jev API key, yours or Tokonoma's, and [data-sharing approval](references/data-flows.md#model-and-integration-connections) | Use Jev classification; Anthropic is the default. |
| [AWS](references/cloud-providers/aws.md) or [Google Cloud](references/cloud-providers/google-cloud.md) storage and identity settings | Enable optional telemetry storage. |

### Phase 2: shared engineer access

After phase 1, gather these for [team access](references/private-access.md). The runner keeps its existing login.

| What | Why |
| --- | --- |
| Intended users and coding agents | Choose who can connect. |
| HTTPS hostname, route, and DNS/certificate owner | Give the team a shared endpoint. |
| Employee sign-in provider and administrator | Authenticate engineers with company sign-in. |

## 3. Give these instructions to your agent

Give your agent this request, along with any values files or supporting files you have already prepared or received:

> Fetch the complete repository from https://github.com/tokonoma-ai/tokonoma-docs into your workspace, keeping SKILL.md, references/, and examples/ together. Read SKILL.md and complete the README's Before you start checklist for phase 1 using supplied files and existing configuration. Ask for all remaining inputs, conflicts, setup choices, and test-alert approval in one batch. Install the standard setup with Agentic Monitoring, automatic investigations, Slack, and the runner's machine login. Keep MCP private. Complete phase 1 only after deployment health passes, detector setup completes and checks are running, and connected alerts produce completed automatic investigations with saved results and Slack delivery. Report incomplete checks and customer-selected opt-outs. Then configure shared hostname, routing, and human sign-in for phase 2 if requested. Merge supplied values and preserve existing choices, including authentication. Check for an existing installation and prepare required access before changing the cluster. Record any deployment-event connection that still needs follow-up.

Use an authorized workstation and handle sign-ins, credentials, and administrator-only actions when the agent asks. Replace secret placeholders and run those commands locally, or use existing Kubernetes Secret references. Never paste secrets or filled commands into chat.

To add a capability later, use the [configuration update guide](references/upgrading.md#before-changing-configuration) with the same checklist. Configure authentication before sharing an endpoint.

## Read the documentation

You can read the guides below to understand what the agent will do and review its choices. [`examples/values.yaml`](examples/values.yaml) explains required settings and integration options through comments, while `references/` contains the setup and operation guides used by both you and your agent.

| Your task | Documentation |
| --- | --- |
| Understand and prepare | [Data flows](references/data-flows.md), [credentials and license](references/credentials.md), [input conventions](references/install.md#inputs-and-placeholders) |
| Install and connect | [Installation](references/install.md), [coding agents](references/coding-agents.md) |
| Configure monitoring, investigations, or access | [Agentic monitoring](references/agentic-monitoring.md), [automatic investigations](references/alert-investigations.md), [integrations](references/integrations.md), [team access](references/private-access.md) |
| Look up configuration | [values.yaml](examples/values.yaml), [endpoints](references/endpoints.md), [version choices](references/upgrading.md#before-changing-configuration) |
| Operate the installation | [Upgrade](references/upgrading.md), [troubleshoot](references/troubleshooting.md), [remove Tokonoma](references/uninstall.md) |

Use your Tokonoma contact for a license or deployment help. Keep credentials, issued licenses, customer data, and unredacted diagnostics out of this repository and public issues.
