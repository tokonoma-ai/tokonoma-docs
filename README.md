# Install and use Tokonoma

This revision requires the application and chart releases described in [native machine authentication](references/upgrading.md#native-machine-authentication-release-prerequisite). Keep using the released installation guide until those releases are available.

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

## 2. Install Tokonoma

Follow these steps yourself, or [give the instructions below to your agent](#3-give-these-instructions-to-your-agent). Start with monitoring and investigations. Shared team access comes afterward.

### Phase 1: installation

MCP stays inside your cluster during this phase. Use a local port-forward for operator access.

#### 1. Choose the cluster and prepare your keys

Choose the Kubernetes context, release name, and installation namespace with your platform team. The release and namespace default to `tokonoma`. Check [permissions, storage, capacity, and network access](references/install.md#1-check-prerequisites).

Get your Tokonoma license and Anthropic API key using the [credential guide](references/credentials.md). The same API key serves the runner and memory analysis. Review the [external data flows](references/data-flows.md#model-and-integration-connections) for your selected connections.

#### 2. Connect the runner and Slack

The installer creates and connects the [runner's private machine login](references/alert-investigations.md#prepare-runner-credentials-when-mcp-authentication-is-enabled), also used by the local UI. You do not need a Cognito pool or a separate client ID and secret for this step. Human sign-in comes in phase 2.

Create the [Slack app](references/slack-app.md#create-the-app) from our [manifest](examples/slack-app-manifest.yaml). Obtain its bot token and app-level token with `connections:write`, then invite `@Tokonoma` to your investigations channel.

#### 3. Configure monitoring and alert inputs

For each connected system's MCP, configure its endpoint, authentication, source identifiers, and permitted read-only tools using the [integration guide](references/integrations.md#mcp-connections). With the [bundled Grafana adapter](references/alert-investigations.md#install-with-oss-grafana-mcp), supply your Grafana URL and Viewer service-account token.

Choose the **cluster name you want Tokonoma to monitor**, using its name in your telemetry. Optionally restrict monitoring to a namespace; otherwise confirm all namespaces, including system ones. Follow [monitoring setup](references/agentic-monitoring.md#prepare-the-inputs).

Prepare the receiver token for [Alertmanager](references/alert-investigations.md#before-you-start) or [Datadog](references/datadog-alerts.md) before installing. Identify the alert-routing owner and existing destinations to preserve. If there is no alert sender, record **none configured**; the current chart still needs an unused receiver token. Report this separately from a selected sender whose connection is pending.

Confirm your deployment system, event source, repository/workflow, and read access with Tokonoma. Axiom annotations need annotation read access. Code access alone does not deliver deployment events.

You can also add [code access](references/integrations.md#github-example), [runbooks and past incidents](references/coding-agents.md#3-onboard-your-coding-agent), or optional [cloud telemetry storage](references/integrations.md). Typesafe/Jev classification is optional and needs [data-sharing approval](references/data-flows.md#model-and-integration-connections), even with a Tokonoma-supplied key; Anthropic is the default.

#### 4. Install the services and connect alert senders

Run the [installation command](references/install.md#3-install) with your saved configuration and credentials. It installs the required services, including bundled PostgreSQL. Keep existing configuration and credentials when updating a release.

After the [deployment health checks](references/install.md#4-verify) pass, connect your alert senders without changing existing paging destinations. In-cluster senders use the private runner service. External senders need a [separate webhook route](references/private-access.md#slack-and-webhooks) that keeps MCP private.

#### 5. Confirm monitoring and investigations are working

Follow the [installation checks](references/install.md#check-monitoring-and-integrations). You should see detectors actively checking your services and an approved test alert producing a completed investigation, a saved record, and a result in Slack.

### Phase 2: shared engineer access

Choose the engineers and coding agents that will connect. Set up the shared HTTPS hostname, routing, and employee sign-in using [team access](references/private-access.md). Reuse the runner's phase 1 login.

## 3. Give these instructions to your agent

Give your agent this request, along with any values files or supporting files you have already prepared or received:

> Fetch the complete repository from https://github.com/tokonoma-ai/tokonoma-docs into your workspace, keeping SKILL.md, references/, and examples/ together. Read SKILL.md and the guides linked from the README's installation walkthrough. Reuse supplied files and existing configuration, then ask for all remaining phase 1 inputs, conflicts, setup choices, and test-alert approval in one batch. Install the standard setup with Agentic Monitoring, automatic investigations, Slack, and the runner's machine login. Keep MCP private. Complete phase 1 only after deployment health passes, detector setup completes and checks are running, and connected alerts produce completed automatic investigations with saved results and Slack delivery. Report incomplete checks and customer-selected opt-outs. Then configure shared hostname, routing, and human sign-in for phase 2 if requested. Merge supplied values and preserve existing choices, including authentication. Check for an existing installation and prepare required access before changing the cluster. Record any deployment-event connection that still needs follow-up.

Use an authorized workstation and handle sign-ins, credentials, and administrator-only actions when the agent asks. Replace secret placeholders and run those commands locally, or use existing Kubernetes Secret references. Never paste secrets or filled commands into chat.

To add a capability later, use the [configuration update guide](references/upgrading.md#before-changing-configuration) and the relevant integration guide. Configure authentication before sharing an endpoint.

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
