# Using Tokonoma

After [installation verification](install.md#4-verify), use Tokonoma to investigate a symptom, check service health, or reuse the team's earlier findings. Your agent needs a [Tokonoma connection](coding-agents.md) and access to telemetry for the services you ask about. Available log, trace, metric, and code tools depend on the integrations you configured.

## Run your first investigation

Choose a known symptom and a time window with telemetry. Ask your coding agent:

```text
Use Tokonoma's investigate skill to investigate the checkout error spike in
cluster REPLACE_WITH_CLUSTER, namespace REPLACE_WITH_NAMESPACE, during
REPLACE_WITH_START_UTC to REPLACE_WITH_END_UTC. Search previous investigations
and procedures first, then confirm the cause with current telemetry. Report
the evidence, uncertainty, and recommended next step, and save the outcome.
```

Use actual timestamps, including the UTC offset, and your telemetry's service name. If you only know the symptom, say so; the agent can help narrow the scope. Missing telemetry or failed queries should appear as gaps in the result.

The `investigate` skill looks for prior investigations and applicable procedures before fresh diagnosis. It checks whether a prior explanation fits the current occurrence, queries the connected telemetry, and saves the outcome and dead ends for the next investigator. A matching old record is a starting point; current evidence must support the conclusion.

### What to look for in the result

Expect an affected service and time window, evidence for the conclusion, its confidence, remaining gaps, a recommended action, and a saved or cited record identifier. A result may conclude that the cause is still unknown. In Slack, the runner posts its result in a thread with a record reference and **Full record** button when a record is available.

The following is an **illustrative summary**, not output from a real incident or an exact UI template:

```text
Scope: checkout, 14:00–14:30 UTC
Finding: requests began failing while waiting for a database connection.
Evidence: connection-pool timeout logs began at 14:07; pool-wait metrics rose
at the same time. A prior investigation describes the same symptom.
Confidence: inferred. The database's own metrics were unavailable.
Next step: check database connection pressure before changing pool limits.
Record: <identifier returned by the save or recall>
```

Open the record to inspect the supporting queries, hypotheses, and unresolved questions. Ask the agent to explain evidence that is unclear before acting on a recommendation. If code needs a fix, give the finding and record identifier to your coding agent and ask it to prepare a change and tests for review. Code access is an optional integration; an investigation result does not itself deploy a fix.

## Check health before on-call

```text
Use Tokonoma's check-health skill for checkout and payments in
REPLACE_WITH_CLUSTER / REPLACE_WITH_NAMESPACE over the last hour.
```

`check-health` produces a service table with **Healthy**, **Concerns**, or **Unknown** and a reason for each. It compares current signals with baselines from procedures and prior investigations where available. It reports missing evidence, including when no metric tool is available to assess saturation. This is a read-only snapshot; it does not save a new investigation. Ask for `investigate` on a concern that needs diagnosis.

## Add and reuse team knowledge

Run `Run Tokonoma onboard.` to select historical incidents, prior agent sessions, or runbooks to import. A runbook becomes a procedure; an incident becomes an investigation. You can skip any step. See [coding-agent onboarding](coding-agents.md#3-onboard-your-coding-agent).

For a completed investigation, ask `Save this investigation to Tokonoma, including the evidence, dead ends, and remaining uncertainty.` For a reusable runbook, ask the agent to save it as a procedure with its trigger, scope, and steps. Review the content and sharing choice before saving sensitive material.

To retrieve it later, ask `What has the team learned about checkout connection-pool timeouts? Search Tokonoma and fetch the relevant records.` Search results contain summaries; fetching the body reveals the detailed record.

## Work with teammates in Slack

Use [Slack commands](slack-app.md#use-tokonoma-in-a-channel) to request a runner investigation or read a saved result. [Incident coordination](slack-app.md#optional-incident-sessions) is optional and off by default for Slack, coding agents, and the runner. Ordinary investigations and their saved outcomes remain available. When enabled, start a shared session, see its timeline, and save the closed session. Give the posted `TKNM-<N>` handoff to each teammate's coding agent so their work joins the same session.

For monitoring, inspect detector findings and proposals before approving a proposed detector. A finding describes something observed by a check. The runner groups related signals and asks the Judge whether they repeat a known issue. A sufficiently supported recurrence links to the prior record instead of starting another investigation; other groups proceed to investigation subject to the runner's guardrails. If the Judge is unavailable, the group proceeds rather than being silently dismissed. [Monitoring verification](agentic-monitoring.md#verify-monitoring) explains how to distinguish active checks from coverage gaps.

## Terms you will see

| Term | Meaning |
| --- | --- |
| Record or memory | A saved item, such as an investigation or procedure, with a searchable summary and detailed body. |
| Investigation | Evidence, hypotheses, dead ends, and a diagnostic outcome for a particular incident or question. |
| Procedure | Reusable troubleshooting or remediation steps, with a scope and trigger for when to use them. |
| Recall | A licensed read of a record body. Search summaries and full-body reads are distinct; body reads pass through the license meter. |
| Detector | A configured check that the runner evaluates against telemetry to find significant changes. |
| Runner | The service that runs Agentic Monitoring and automatic investigations using connected tools. |
| Judge | The decision step that compares grouped detector signals with known issues and assesses recurrence and severity. It helps decide whether to investigate or reuse a prior record. |

New records are shared with everyone in the organization by default (`toko:everyone`). Choose private or an available identity-provider group when needed. The Slack app can access organization-wide records, with the [sharing limits described in its guide](slack-app.md#channel-access-and-shared-records). Keep secrets out of records.
