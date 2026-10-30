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

Illustrative summary:

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

Use [Slack commands](slack-app.md#use-tokonoma-in-a-channel) to request an investigation or read a saved result. [Incident coordination](slack-app.md#optional-incident-sessions) is optional and off by default. When enabled, start a shared session, review its timeline, and save it when closed. Give the posted `TKNM-<N>` handoff to each teammate's coding agent to join the session.

Review a detector's scope, query, and findings before enabling it. When evidence supports a recurrence, Tokonoma links the finding to the earlier investigation. Other eligible findings can start a new investigation within your configured limits. [Monitoring verification](agentic-monitoring.md#verify-monitoring) explains how to identify coverage gaps.

## Terms you will see

| Term | Meaning |
| --- | --- |
| Record or memory | A saved item, such as an investigation or procedure, with a searchable summary and detailed body. |
| Investigation | Evidence, hypotheses, dead ends, and a diagnostic outcome for a particular incident or question. |
| Procedure | Reusable troubleshooting or remediation steps, with a scope and trigger for when to use them. |
| Recall | Reading a record's full body rather than its search summary; requires a valid license. |
| Detector | A configured check that the runner evaluates against telemetry to find significant changes. |
| Runner | The service that runs Agentic Monitoring and automatic investigations using connected tools. |
| Judge | Checks whether monitoring findings repeat a known issue and assesses their severity. Helps decide whether to investigate or link to an earlier investigation. |

New records are shared with everyone in the organization by default. Choose private or an available identity-provider group when needed. The Slack app can access organization-wide records, with the [sharing limits described in its guide](slack-app.md#channel-access-and-shared-records). Keep secrets out of records.
