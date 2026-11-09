# Start here

Tokonoma is a reliability teammate for engineers operating production services. It uses the telemetry tools you connect, investigates problems, and saves evidence and procedures so the next investigation can build on earlier work. You choose its access and where it posts results.

## What you can do with it

| Situation | How Tokonoma helps | Your next step |
| --- | --- | --- |
| A service changes without firing an alert | Agentic Monitoring discovers and evaluates checks for the services in scope, then assesses significant findings | Review coverage, evidence, and detector proposals |
| An existing alert fires | The runner queries connected tools, investigates, saves a result, and posts to Slack when configured | Check the evidence and proposed next steps |
| Engineers investigate together | Optional Slack sessions and connected coding agents keep investigation context available to the team | [Enable incident sessions](slack-app.md#optional-incident-sessions), then save the timeline, decisions, and outcome |
| A similar problem returns | Agents can search past investigations and procedures before starting fresh | Check that the old evidence and procedure still apply |

Start with [Using Tokonoma](using-tokonoma.md) for a first investigation, an illustrative result, Slack commands, and a glossary. The [product walkthrough](https://tokonoma.ai/guides/detection-to-fix) shows how evidence passes to a coding agent to prepare a pull request. Your team reviews, releases, and verifies the fix.

Tokonoma can query existing providers such as Grafana, Datadog, and Axiom; you do not need to move your telemetry. Its optional telemetry platform provides storage and querying in your cloud when you want to ingest logs and traces there. Choose it for that need, after checking storage, retention, and operating costs, rather than enabling it just to connect an existing provider.

## Choose the deployment path

These guides cover the full monitoring and investigation workflow on an existing Kubernetes cluster. Other delivery paths have separate setup instructions and may start with fewer features.

| Path | Choose it when | Where to start and what to verify |
| --- | --- | --- |
| Helm in your Kubernetes cluster | Your platform team owns a cluster and can operate the workloads | Use the [agent-led installation](../README.md#give-these-instructions-to-your-agent) and [planning guide](planning.md). This is the workflow maintained in this repository. |
| Single-VM AWS AMI | You want a prebuilt single-node environment instead of supplying a cluster | Ask your Tokonoma contact for the current AMI, region, profile, and customer launch guide. The AMI's default **lite** profile provides memory and skills; **full** adds the telemetry stack. Neither profile alone proves monitoring, alert investigations, or Slack are configured. |
| `tokonoma-setup` Terraform | You need to provision AWS networking, EKS, storage, and Cognito before installing workloads | Ask your Tokonoma contact for the supported infrastructure package and access, then reconcile its generated values with these installation requirements. Infrastructure provisioning and a healthy MCP alone do not verify monitoring or investigations. Preserve its existing authentication and routing. |
| Tokonoma-operated AWS deployment (BYOC) | You want Tokonoma to operate the deployment in your AWS account | Agree with your Tokonoma contact on account access, operating responsibilities, feature scope, and the current BYOC onboarding guide. Do not apply the self-managed commands alongside the operator's deployment. |

AMI and infrastructure recipes are separate delivery workflows, not a drop-in substitute for this repository's values file. Confirm the delivered chart and application versions and which features are configured. Do not assume a lightweight memory deployment meets the full installation completion checks.

## Follow the installation

Start with the [upfront choices and agent request](../README.md#what-to-expect), then follow [Install Tokonoma](install.md). Select the telemetry platform and MCP query access independently; the fastest setup uses existing telemetry and Slack with MCP private. The guide completes selected options during the same installation and supports adding them later.

For a new telemetry platform, the [customer collector example](customer-telemetry.md) comes after Tokonoma setup. Application data and monitoring coverage have separate checks. Preserve existing authentication, routes, and paging destinations when adding capabilities.

After setup, use [Using Tokonoma](using-tokonoma.md), [upgrading](upgrading.md), and [backup and recovery](backup.md) for ongoing operation.
