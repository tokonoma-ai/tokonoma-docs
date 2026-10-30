# Plan an installation

Use this page with the platform and integration owners before starting the [agent-led installation](../README.md#give-these-instructions-to-your-agent). It describes the standard chart deployment using existing telemetry providers. Optional telemetry storage has a separate capacity and cloud bill.

## Capacity and cluster policy

Start with roughly **8 vCPU and 32 GiB of RAM available to Tokonoma across your Kubernetes cluster**, after reserving resources for Kubernetes and other workloads. This is a recommended starting capacity, not a benchmark, throughput guarantee, or scheduling floor. Individual pods must still fit on a node.

Chart 0.40.0 requests the following resources with the [installation example](../examples/values.yaml), before optional adapters and telemetry storage. These figures describe that release; inspect the current chart's values before relying on them for a new installation.

| Workload | CPU request | Memory request | Persistent storage |
| --- | --- | --- | --- |
| Primary MCP | 100m | 256 MiB | Attachments disabled in the example |
| Unattended MCP | 100m | 256 MiB | Shares PostgreSQL |
| Runner | 100m | 1 GiB | Shares PostgreSQL |
| PostgreSQL | 100m | 256 MiB | 8 GiB |
| Ollama | 200m | 512 MiB | 8 GiB |
| **Total** | **600m (0.6 vCPU)** | **2304 MiB (2.25 GiB)** | **16 GiB** |

These are scheduling floors, not a minimum node size or a measured peak. The runner has a 3 GiB memory limit. These workloads have no CPU limits, and the other listed workloads have no memory limits. Leave allocatable capacity for Kubernetes, other workloads, model loading, query bursts, and concurrent investigations. Ollama uses a CPU image; a GPU is not required for local embeddings. Monitor actual memory, CPU, database growth, and queueing, then adjust requests and disk capacity with your platform team. No general production node-size benchmark is published here; obtain a sizing review for your expected workload rather than treating the request total as production capacity.

The bundled PostgreSQL is one replica. Node or volume recovery can interrupt records, monitoring, and investigations; it is not a high-availability database. Set a [backup and recovery policy](backup.md) before storing important records.

The chart targets **baseline Pod Security**. The bundled PostgreSQL and Ollama images start as root, and a namespace enforcing the **restricted** profile rejects those pods. Have the platform owner review this before installation. Do not weaken a namespace policy to bypass a failed install; agree on an approved deployment design with Tokonoma if restricted admission is mandatory.

The core chart declares no Kubernetes version support range. The optional Grafana adapter requires Kubernetes 1.25 or later; that is an adapter prerequisite, not a claim that every Kubernetes release from 1.25 onward is supported. Confirm the chosen cluster version, storage driver, and ingress controller with your platform owner and Tokonoma. Check [network destinations](data-flows.md#network-destinations), a default StorageClass, and volume provisioning before Helm installation.

Resource and admission details come from the released [chart values](https://github.com/tokonoma-ai/tokonoma-charts/blob/v0.40.0/charts/tokonoma/values.yaml) and [chart metadata](https://github.com/tokonoma-ai/tokonoma-charts/blob/v0.40.0/charts/tokonoma/Chart.yaml). Optional components add their own requests, storage, and policy requirements.

## Model and infrastructure cost

Budget for the Tokonoma license, cluster compute and volumes, any load balancers and storage, observability-provider query charges, and Anthropic API usage. Reusing your telemetry provider avoids deploying Tokonoma's optional telemetry storage; it does not remove that provider's query costs.

There is no fixed price per investigation. Model choice, input and output tokens, cache use, tool results, and the number of turns change the bill. Run an approved representative investigation, inspect usage in your Anthropic account, and measure a sample of ordinary and critical investigations before forecasting a daily cost. Missing usage data is not zero usage.

Default runner controls are five concurrent runs, 40 turns per investigation, and a 900-second run timeout. Automatic intake has two independent daily counters: 200 non-critical starts and 200 critical starts. Their sum permits up to 400 automatic starts per runner process per day. The counters reset on restart and are not a durable spending limit.

As a planning estimate, multiply each daily start count by its measured cost per run. Add Agentic Monitoring checks, memory analysis, and manual investigations separately. Turn and time limits are not token or dollar limits. Use your provider's current pricing and budget controls, then review actual usage after rollout. The [Datadog recipe](datadog-alerts.md#all-monitor-coverage) deliberately forwards every monitor; review volume before enabling that rule. Existing paging destinations remain in place.

## People and elapsed time

Line up these owners before the operator starts; one person may hold several roles:

| Owner | Preparation |
| --- | --- |
| Platform operator | Authorized cluster context and namespace, capacity, StorageClass, admission policy, egress, and any webhook route |
| Tokonoma contact | Issued license, deployment choice, sizing or compatibility questions |
| Anthropic account owner | API key supplied securely, model access, spend monitoring and budget controls |
| Telemetry owner | Query endpoint, approved read-only tools, credentials, cluster and namespace scope |
| Alerting owner | Receiver token, sender configuration, preserved paging routes, approved test alert |
| Slack administrator, when selected | App approval, tokens supplied securely, channel and app membership |
| Identity and network owners, for later shared access | Human login, hostname, TLS, and routing; preserve the runner's installed machine identity |

Hands-on setup and calendar lead time are separate. Configuration and checks need an operator session; account approvals, network changes, and administrator availability can span days. There is no measured install-duration guarantee. Arrange the approved alert test and integration owners in advance, and allow time to resolve failed checks. A healthy Helm release alone does not complete installation: require active monitoring, completed investigations, saved results, and configured Slack delivery before moving to shared team access.
