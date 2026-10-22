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

Start with phase 1. Your agent reads supplied files and existing configuration, then asks for all missing inputs and choices in one batch. Keep confirmed answers with your saved configuration. Preserve existing choices and include any monitoring or investigation opt-outs in that batch.

### Phase 1: installation

Install the bundled services, monitoring, automatic investigations, Slack, and the runner's machine login. MCP stays inside the cluster, with a local port-forward for operator access. The shared hostname and human sign-in can wait until phase 2.

**Checkpoint:** Tokonoma is healthy, detector setup is complete and checks are running, and connected alerts trigger automatic investigations with saved results and Slack delivery. Complete the [monitoring and integration checks](references/install.md#check-monitoring-and-integrations) before phase 2. Report any incomplete checks or customer-selected opt-outs.

#### Required: deployment and access

- [ ] **Installation target:** cloud provider, authorized Kubernetes context, release name, installation namespace, and installer. Confirm workload, storage, capacity, and network access with the [prerequisite checks](references/install.md#1-check-prerequisites).
- [ ] **License and model API key:** issued Tokonoma license and Anthropic API key for both memory analysis and the runner. Configure an existing key Secret for both consumers. Approve the selected [external data flows](references/data-flows.md#model-and-integration-connections).
- [ ] **Runner machine login:** identity administrator, provider settings, and dedicated credentials: a Cognito machine-to-machine client ID and secret, or legacy Google Identity Platform/Firebase runner account credentials. Include `toko-mcp/query` access and the runner credential Secret reference. See [runner credentials](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled) for private MCP access. Human sign-in does not replace this login.
- [ ] **Slack:** app owner with creation/install permissions; app created from our [manifest](examples/slack-app-manifest.yaml); bot token; app-level token with `connections:write`; investigations channel with `@Tokonoma` invited. Follow [Slack setup](references/slack-app.md#create-the-app).

#### Required: monitoring and investigations

- [ ] **Monitoring scope:** provide the target **cluster name you want Tokonoma to monitor**, using the name recorded in your telemetry. Optionally restrict it to a namespace. Otherwise, confirm all namespaces, including system ones. See [monitoring inputs](references/agentic-monitoring.md#prepare-the-inputs).
- [ ] **Telemetry access:** for each connected system's MCP, provide its full endpoint, any applicable region/site, organization, or dataset identifiers, authentication and credentials, and exact permitted read-only tools. Include logs, metrics, traces, alert definitions, and Kubernetes events/entities where available. See the [provider examples](references/integrations.md#mcp-connections). For the bundled [Grafana MCP adapter](references/alert-investigations.md#install-with-oss-grafana-mcp), provide the Grafana URL and Viewer service-account credential with data-source access; the chart connects its MCP automatically.
- [ ] **Existing alert investigations:** alert provider, rules/routing location and owner, existing destinations to preserve, and Tokonoma's delivery route and authentication. Include approval for a source-side test alert to verify an investigation and result delivery. Say **none** if there are no existing alerts; the chart still needs a supported receiver token. In-cluster senders use the private runner service. External senders need a [separate webhook route](references/private-access.md#slack-and-webhooks) that keeps MCP private. See [Alertmanager](references/alert-investigations.md#before-you-start) or [Datadog](references/datadog-alerts.md).
- [ ] **Deployment watching:** deployment system, release-event source, relevant repository/workflow, and permitted access. Sources can include telemetry annotations, Kubernetes events, or a webhook. Axiom annotations need annotation read access. Confirm the supported connection with Tokonoma; GitHub MCP code access does not deliver deployment events.

#### Optional additions

- [ ] **Code access:** approved repositories, relevant directory paths, and permitted code/history access. See the [GitHub guide](references/integrations.md#github-example) for read-only access and organization approval.
- [ ] **Existing knowledge:** runbooks, investigation skills, past incidents, and examples of healthy or unhealthy behavior for [onboarding](references/coding-agents.md#3-onboard-your-coding-agent).
- [ ] **Typesafe/Jev classification:** approval to send monitoring context to Typesafe, even with a Tokonoma-supplied key, and whose key to use. Otherwise use the Anthropic default. Review the [additional data flow](references/data-flows.md#model-and-integration-connections).
- [ ] **Telemetry storage:** selected cloud storage and identity settings from [AWS](references/cloud-providers/aws.md) or [Google Cloud](references/cloud-providers/google-cloud.md).

### Phase 2: shared engineer access

After the phase 1 checkpoint, prepare these when you want engineers to connect their coding agents. Reuse the runner's phase 1 login. Follow [private and team access](references/private-access.md).

- [ ] **Users and clients:** intended users and coding agents in use.
- [ ] **Shared endpoint:** preferred HTTPS hostname, routing, and owner for DNS and TLS certificates.
- [ ] **Human sign-in:** employee sign-in provider and administrator contact.

## 3. Give these instructions to your agent

Give your agent this request, along with any values files or supporting files you have already prepared or received:

> Fetch the complete repository from https://github.com/tokonoma-ai/tokonoma-docs into your workspace, keeping SKILL.md, references/, and examples/ together. Read SKILL.md and complete the README's Before you start checklist for phase 1 using supplied files and existing configuration. Ask for all remaining inputs, conflicts, setup choices, and test-alert approval in one batch. Install the standard setup with Agentic Monitoring, automatic investigations, Slack, and the runner's machine login. Keep MCP private. Complete phase 1 only after deployment health passes, detector setup completes and checks are running, and connected alerts produce completed automatic investigations with saved results and Slack delivery. Report incomplete checks and customer-selected opt-outs. Then configure shared hostname, routing, and human sign-in for phase 2 if requested. Merge supplied values and preserve existing choices, including authentication. Check for an existing installation and prepare required access before changing the cluster. Record any deployment-event connection that still needs follow-up.

Use an authorized workstation and handle sign-ins, credentials, and administrator-only actions when the agent asks. Supply secrets through protected files or Kubernetes Secret references; never paste them into chat.

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
