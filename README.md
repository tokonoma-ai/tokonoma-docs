# Install and use Tokonoma

## What to expect

Tokonoma monitors your services, detects significant changes, and automatically investigates findings and alerts using your observability tools. Engineers can work with it through Slack and coding agents, using saved findings and procedures to build on what the team has learned.

New to Tokonoma? [Start here](references/start-here.md) for use cases, deployment choices, and a first investigation. The [product website](https://tokonoma.ai/) has the broader feature tour.

The installation runs in your Kubernetes cluster and includes:

- **Tokonoma MCP service:** investigation tools, saved findings and procedures, the Slack connection, and a local administration UI. MCP means Model Context Protocol, which lets coding agents use these tools.
- **Tokonoma runner and its dedicated MCP instance:** Agentic Monitoring and automatic investigations using your connected telemetry and alert sources.
- **PostgreSQL:** bundled storage for records and application state. Helm creates its credentials.
- **Ollama:** local search embeddings, which turn text into numeric representations for search.

Agentic Monitoring checks telemetry without waiting for an alert. Automatic investigations use the full alert stream from connected sources. Both are enabled by default; your agent will ask whether you want either turned off. You choose which systems Tokonoma can access and where it posts in Slack. Existing paging destinations stay in place.

Tokonoma connects to the Anthropic API for analysis and investigations, to Slack, and to each connected system's MCP or the bundled adapter for an existing Grafana. Investigation content and retrieved telemetry are sent to Anthropic. Code access and cloud telemetry storage are optional additions.

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

First, get Tokonoma healthy, detectors running, and connected alerts automatically investigated with saved results and Slack delivery. MCP stays inside the cluster, with local operator access. Shared engineer access comes afterward, with authentication, the runner's machine login, and the chosen HTTPS route.

## Give these instructions to your agent

Use a coding agent on a workstation with access to your Kubernetes cluster. Paste this request and provide any configuration files you already have:

> Help me install Tokonoma using https://github.com/tokonoma-ai/tokonoma-docs. Fetch the complete repository, read SKILL.md, and follow its installation guides. Inspect supplied configuration and any existing installation, then ask for all currently missing inputs and choices in one batch before changing the cluster. Preserve existing configuration, credentials, authentication, and paging destinations. Guide me through account setup and administrator actions as they are needed. Continue through verification until Tokonoma is healthy, detectors are actively checking the intended services, and connected alerts produce completed automatic investigations with saved results and Slack delivery. Report any blockers or explicit opt-outs. Set up shared engineer access afterward if I request it.

## Follow along with the agent

1. **Answer its setup questions.** The agent checks what is already configured and asks for the remaining cluster, monitoring, integration, and alert details together. If a later answer reveals another requirement, it explains what changed.
2. **Complete account and credential steps when prompted.** The agent explains how to obtain the license, API keys, and Slack tokens, and which permissions each connection needs. Fill secret placeholders and run those commands locally, or use existing Kubernetes Secret references. Do not paste secrets or filled commands into chat.
3. **Stay with it through the checks.** The agent installs the services, connects the selected alert senders, and verifies monitoring and investigations. Expect active detectors and an approved test alert producing a completed investigation, a saved record, and a Slack result. Continue with the agent until any failures are resolved; ready pods alone do not complete the installation.

The agent should finish with the saved configuration locations, the checks it ran and their results, and any remaining actions. If no alert sender is configured, it should say so explicitly rather than claim alert delivery was verified.

## Reference documentation

The agent uses [SKILL.md](SKILL.md) and the [detailed guides](references/) for installation commands, provider setup, and operation. You can read them to inspect a particular step; the agent will bring the relevant instructions into your conversation. After installation, follow [Using Tokonoma](references/using-tokonoma.md) to investigate an issue, share knowledge, and take findings into a code review.

Use your Tokonoma contact for a license or deployment help. Keep credentials, issued licenses, customer data, and unredacted diagnostics out of this repository and public issues.
