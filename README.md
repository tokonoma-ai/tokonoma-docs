# Install and use Tokonoma

Tokonoma monitors your services, detects significant changes, and automatically investigates findings and alerts using your observability tools. Engineers can collaborate through Slack and coding agents. Saved findings and procedures help each investigation build on what your team has learned.

You choose which services to monitor, which alerts to investigate, and which tools and Slack channels Tokonoma can use. Agentic monitoring and automatic investigations are enabled in the installation example.

```mermaid
flowchart LR
  accTitle: Tokonoma in your environment
  accDescr: Coding agents connect to Tokonoma, and selected alerts reach the required Tokonoma runner. Tokonoma and its runner run in your Kubernetes cluster. Tokonoma connects to Slack and its model provider for required analysis. The runner monitors configured telemetry and automatically investigates findings and alerts using its model provider and permitted integrations. Arrows show who opens each connection. This is a capability overview, not a map of internal services.
  subgraph Inputs["Your team and alerts"]
    Agents["Coding agents"]
    Alerts["Selected alerts"]
  end
  subgraph Cluster["Your Kubernetes cluster"]
    Tokonoma["Tokonoma<br/>Investigation tools and memory"]
    Runner["Tokonoma runner<br/>Monitoring and investigations"]
  end
  subgraph Connections["Services you configure"]
    Slack["Slack"]
    Models["Model providers"]
    Tools["Integrations<br/>(Telemetry, Alerting, Code)"]
  end
  Agents --> Tokonoma
  Alerts --> Runner
  Tokonoma -->|"Messages"| Slack
  Tokonoma -->|"Analysis"| Models
  Runner -->|"Model calls"| Models
  Runner -->|"Query"| Tools

  classDef service fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e,stroke-width:2px
  classDef external fill:#fff,stroke:#64748b,color:#0f172a
  class Tokonoma,Runner service
  class Agents,Alerts,Slack,Tools,Models external
  style Cluster fill:#eff6ff,stroke:#0369a1,color:#0c4a6e
  style Inputs fill:#f8fafc,stroke:#cbd5e1,color:#334155
  style Connections fill:#f8fafc,stroke:#cbd5e1,color:#334155
```

Arrows show who opens each connection; responses and Slack events return over it.

## What you will install

Your agent connects through the Model Context Protocol (MCP). The installation includes the Tokonoma MCP service, the required runner and its dedicated MCP instance, PostgreSQL for records and state, and Ollama for local search embeddings (numeric representations of text). PostgreSQL is bundled unless you configure an external database.

The [installation guide](references/install.md) uses the published Helm chart and one `values.yaml` for these services and your [selected integrations](references/integrations.md). Connect Datadog, Axiom, or other compatible MCP tools for telemetry and code access. The guide uses the chart's image defaults without requiring a specific release version or access to the application source.

Model providers can receive investigation context. A hosted coding agent can also send retrieved records to its own provider. See [data flows](references/data-flows.md) for callers, destinations, and network requirements.

| Optional capability | What it adds | Start here |
| --- | --- | --- |
| Slack | Use `@Tokonoma` in invited channels and receive investigation results | [Slack setup](references/slack-app.md) |
| Shared team access | A stable endpoint with network access and user authentication | [Private and team access](references/private-access.md) |
| Telemetry storage | Store and query telemetry in your own cloud infrastructure | [AWS](references/cloud-providers/aws.md), [Google Cloud](references/cloud-providers/google-cloud.md) |

## Before you start

You need an existing Kubernetes cluster, workload and storage permissions, and a Tokonoma license. Cloud preparation guides cover AWS and Google Cloud. Required memory analysis uses an Anthropic credential. The runner needs model credentials, an alert-source token, and telemetry query access to your selected cluster and namespaces. See the [prerequisite checks](references/install.md#before-installing).

The walkthrough uses bundled PostgreSQL, a temporary local connection, and Slack for runner results. You need permission to install the Slack app and obtain its tokens. If you want an external database or a shared endpoint, prepare it before installing. Changing a database address does not move data.

## Choose how to install

**With an agent:** download the whole repository, open it in your agent's workspace, and add your known cluster and features to this request:

> Read SKILL.md and help me install Tokonoma with agentic monitoring and automatic investigations enabled. Identify the intended cluster and whether an installation already exists. Check my saved integration and monitoring settings, then ask for missing inputs before making changes. Finish once the deployment is running and health checks pass; leave monitoring setup and investigations running in the background.

Keep `references/` and `examples/` with `SKILL.md`. The skill tells the agent how to use these files; opening it does not install anything.

**By hand:** follow [Install Tokonoma](references/install.md). Read the comments in `values.yaml`, replace `REPLACE_WITH_...` inputs, and run the guide's Helm and Kubernetes commands.

Use an authorized workstation. You handle login, credentials, and administrator-only actions; an agent asks for missing inputs. Supply credentials through protected files or Kubernetes Secret references, never chat.

## Read the documentation

[`examples/values.yaml`](examples/values.yaml) contains required settings and commented integration sections. Humans and agents use the same setup and operation guides in `references/`.

| Your task | Documentation |
| --- | --- |
| Understand and prepare | [Data flows](references/data-flows.md), [credentials and license](references/credentials.md), [input conventions](references/placeholder-examples.md) |
| Install and connect | [Installation](references/install.md), [coding agents](references/coding-agents.md), [external PostgreSQL](references/external-postgres.md) |
| Configure monitoring, investigations, or access | [Agentic monitoring](references/agentic-monitoring.md), [automatic investigations](references/alert-investigations.md), [integrations](references/integrations.md), [team access](references/private-access.md) |
| Look up configuration | [values.yaml](examples/values.yaml), [endpoints](references/endpoints.md), [version choices](references/upgrading.md#before-changing-configuration) |
| Operate the installation | [Upgrade](references/upgrading.md), [troubleshoot](references/troubleshooting.md), [remove Tokonoma](references/uninstall.md) |

Use your Tokonoma contact for a license or deployment help. Keep credentials, issued licenses, customer data, and unredacted diagnostics out of this repository and public issues.
