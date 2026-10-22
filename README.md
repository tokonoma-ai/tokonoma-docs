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

Use this checklist for the requested phase. Your agent first reads supplied files and existing configuration, then asks for all missing inputs, choices, and conflicts in one batch. Keep confirmed answers with your saved configuration; phase 2 inputs can wait until you choose shared engineer access.

**Phase 1: private installation.** Install the bundled services, Agentic Monitoring, automatic investigations, Slack, and the runner's machine login. Keep MCP inside the cluster and use a local port-forward for operator access. This phase needs no shared MCP hostname, public MCP ingress, or human single sign-on. External alert senders can use a separate webhook route.

**Phase 2: shared engineer access.** When ready, add a stable HTTPS MCP hostname, routing, and human sign-in for coding agents. Reuse the runner's phase 1 credentials.

Include any automatic-feature opt-outs in the initial batch. Preserve choices already made in supplied or existing configuration.

| Phase / requirement | Item | What to prepare |
| --- | --- | --- |
| 1 / Required | Deployment target and owner | Cloud provider, authorized Kubernetes context, release name, installation namespace, and who will install. Confirm workload, storage, capacity, and network access using the [prerequisite checks](references/install.md#1-check-prerequisites). |
| 1 / Required | License and Anthropic API key | Your issued Tokonoma license and an Anthropic API key for both memory analysis and the runner. If using an existing key Secret, configure it for both consumers. Review and approve the selected [external data flows](references/data-flows.md#model-and-integration-connections). |
| 1 / Monitoring enabled | Monitoring scope | Provide the target **cluster name you want Tokonoma to monitor**, using the name recorded in your telemetry. Optionally specify a namespace restriction. Without a restriction, deliberately select all namespaces, including system ones. See [monitoring inputs](references/agentic-monitoring.md#prepare-the-inputs). |
| 1 / Monitoring or investigations enabled | Telemetry query access | For each connected system's MCP, provide its full endpoint, region/site or organization and dataset identifiers, authentication, credentials, and exact permitted read-only tools. Include logs, metrics, traces, existing alert definitions, and Kubernetes events/entities where available. See the [provider examples](references/integrations.md#mcp-connections). For the bundled [Grafana MCP adapter](references/alert-investigations.md#install-with-oss-grafana-mcp), supply the existing Grafana URL and Viewer service-account credential with data-source access; the chart connects its MCP automatically. |
| 1 / Standard setup | Slack | An app owner with creation/install permissions; app created from our [manifest](examples/slack-app-manifest.yaml); bot token and app-level token with `connections:write`; investigations channel with `@Tokonoma` invited. Follow [Slack setup](references/slack-app.md#create-the-app) before installing. |
| 1 / Required | Existing alert investigations | Alert provider, where rules/routing are configured, configuration owner, existing destinations to preserve, and Tokonoma's delivery route and authentication. If no existing alerts, say **none**; the chart still requires a supported receiver token. In-cluster senders use the private runner Service; external senders need a [separate webhook route](references/private-access.md#slack-and-webhooks) that keeps MCP private. See [Alertmanager](references/alert-investigations.md#before-you-start) or [Datadog](references/datadog-alerts.md). |
| 1 / Required | Deployment watching | Deployment system and release-event source, such as telemetry annotations, Kubernetes events, or a webhook; relevant repository/workflow and permitted access. For Axiom annotations, include annotation read access. Confirm the supported connection with Tokonoma; GitHub MCP code access does not configure deployment-event delivery. |
| 1 / Required | Internal runner login | Identity administrator and credential-provider settings, typically Cognito; dedicated machine-client ID and secret with `toko-mcp/query` access; runner credential Secret reference. Prepare [runner credentials](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled) now. The runner authenticates over the private Service; human SAML sign-in is a separate phase 2 task. |
| 1 / Optional | Code access | Approved repositories, relevant directory paths, and permitted code/history access. The [GitHub guide](references/integrations.md#github-example) covers read-only access and organization approval. |
| 1 / Optional | Existing knowledge and tuning context | Runbooks, investigation skills, past incidents, and examples of healthy or unhealthy application behavior for [onboarding](references/coding-agents.md#3-onboard-your-coding-agent). |
| 1 / Optional | Typesafe/Jev classification | Approval to send monitoring context to Typesafe, even when Tokonoma supplies the key, and whose key to use. Otherwise use the Anthropic default. Review the [additional data flow](references/data-flows.md#model-and-integration-connections) with Tokonoma. |
| 1 / Optional | Telemetry storage | Prepare the selected cloud storage and identity settings from [AWS](references/cloud-providers/aws.md) or [Google Cloud](references/cloud-providers/google-cloud.md). |
| 2 / Optional | Shared engineer access | Coding agents in use, intended users, preferred HTTPS hostname, DNS/TLS owner, employee sign-in provider, and administrator contact. Follow [private and team access](references/private-access.md), preserving the runner login from phase 1. |

## 3. Give these instructions to your agent

Give your agent this request, along with any values files or supporting files you have already prepared or received:

> Fetch the complete repository from https://github.com/tokonoma-ai/tokonoma-docs into your workspace, keeping SKILL.md, references/, and examples/ together. Read SKILL.md and complete the README's Before you start checklist for phase 1 using supplied files and existing configuration. Ask for all remaining inputs, conflicts, and setup choices in one batch. Install the standard private setup with Agentic Monitoring, automatic investigations, Slack, and the runner's machine login. Keep MCP private and defer shared hostname, routing, and human sign-in to phase 2 unless I request them now. Merge supplied values and preserve existing choices, including authentication. Check for an existing installation and prepare required access before changing the cluster. Finish when deployment health checks pass, leaving enabled monitoring setup and investigations running in the background. Record any alert-delivery or deployment-event connection that still needs follow-up.

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
