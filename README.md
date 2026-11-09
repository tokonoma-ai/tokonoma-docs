# Install and use Tokonoma

Tokonoma monitors your services, investigates changes and alerts, and shares findings in Slack. It saves evidence and procedures so your team can build on earlier investigations. It runs in your Kubernetes cluster and can query telemetry you already collect.

## What to expect

The quickest setup uses your existing telemetry provider, required Slack connection, and a private MCP service. It needs no shared MCP hostname or ingress. The installer creates the runner's internal machine login; engineers can add their own MCP query access later.

Choose these two options before installation:

| Choice | What to prepare |
| --- | --- |
| Use Tokonoma's telemetry platform? | Use the [telemetry platform](references/telemetry-platform.md) to store and query logs and traces in your cloud. Prepare [AWS](references/cloud-providers/aws.md) or [Google Cloud](references/cloud-providers/google-cloud.md) storage and identity. You can keep using existing telemetry providers. |
| Expose MCP for queries from coding agents? | Choose a private or public HTTPS hostname, routing, TLS, and human authentication using [shared access](references/team-access.md). This is independent of the telemetry platform. |

Select either, both, or neither. The guide completes every option you select during the same installation. You can add options later using your saved configuration. When you choose the telemetry platform, finish setting up Tokonoma first, then use the [example OpenTelemetry collector](references/customer-telemetry.md) to connect your applications. The bundled collector only collects Tokonoma's own telemetry.

The installation includes the MCP service, a runner with its dedicated MCP instance, PostgreSQL for records and state, and Ollama for local search embeddings. Agentic Monitoring and automatic investigations are enabled unless you opt out. Existing paging destinations stay in place. Alert senders are optional; Slack and telemetry query access support investigations without them.

Analysis and investigations use the Anthropic API or [Amazon Bedrock](references/amazon-bedrock.md). Retrieved telemetry and investigation context reach that model provider. Review [data flows](references/data-flows.md) and [capacity and costs](references/planning.md) with your platform team.

## Give these instructions to your agent

Use a coding agent on a workstation with access to your Kubernetes cluster. Paste this request and provide any configuration files you already have:

> Help me install Tokonoma using https://github.com/tokonoma-ai/tokonoma-docs. Fetch the complete repository, read SKILL.md, and follow the installation guides. Inspect supplied configuration and any existing installation. Ask up front whether I want the telemetry platform and whether I want MCP query access for coding agents, along with missing cluster, Slack, monitoring, and credential inputs. Use the quickest private monitoring setup unless I select additions, and complete every selected option. Preserve existing configuration, authentication, credentials, and paging destinations. Guide me through administrator actions and verify the setup. If I choose the telemetry platform, provide an example OpenTelemetry collector with my ingest endpoints after Tokonoma setup is complete. Report pending customer telemetry separately from installation health, and do not claim untested monitoring or alert delivery works.

Your agent brings the relevant commands into the conversation. Fill secret placeholders and run credential commands locally, or use existing Kubernetes Secrets. Do not paste secrets or filled commands into chat.

## Follow the installation

1. [Plan capacity and access](references/planning.md), identify the cluster and monitoring scope, and prepare a license and model credentials.
2. [Install Tokonoma](references/install.md), including Slack and every selected option. Existing telemetry providers can supply query access immediately; a new platform can receive application data after setup.
3. Review the verification results. Ready workloads establish deployment health; working Slack, telemetry queries, active monitoring checks, and connected alert senders each have their own checks. Keep any pending collection or verification work explicit.
4. Use [Tokonoma in Slack](references/slack-app.md#use-tokonoma-in-a-channel), or connect a [coding agent](references/coding-agents.md) if you selected MCP access.

## Reference documentation

[Start here](references/start-here.md) covers use cases and deployment alternatives. The [reference guides](references/) cover integrations, authentication, operations, and troubleshooting. [SKILL.md](SKILL.md) contains instructions for the installing agent, and [values.yaml](examples/values.yaml) explains the configuration fields.

Use your Tokonoma contact for a license or deployment help. Keep credentials, issued licenses, customer data, and unredacted diagnostics out of this repository and public issues.
