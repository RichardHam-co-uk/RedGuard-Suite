# Blue Team Dry-Run Validation Exercise

> **Classification**: Public/generic template. Replace all `[PLACEHOLDER]` values
> with engagement-specific data in the internal repo only. Use safe placeholders
> (`example.com`, fictional names) everywhere in this public repo.

A **dry-run validation exercise** is a low-risk, fully-announced rehearsal in which
the red team executes (or simulates) a known set of techniques while the blue team
attempts to detect, triage, and respond. Because RedGuard Suite defaults to
`safety.dry_run: true`, the goal is **not** to compromise anything — it is to
validate that detections fire, alerts route correctly, and the response runbooks
work, *before* a live engagement.

- **Audience**: Blue team (SOC/detection engineers), red team lead, exercise control.
- **Duration**: Typically a half-day window (see [Scenario Guide](#1-scenario-guide)).
- **Prerequisite**: A signed [Rules of Engagement](../roe_template.md) and an agreed
  [deconfliction](../playbooks/deconfliction_guide.md) channel.

## Contents

1. [Scenario Guide](#1-scenario-guide)
2. [Exercise Checklists](#2-exercise-checklists)
3. [Scoring Rubric](#3-scoring-rubric)
4. [After-Action Review (AAR) Template](#4-after-action-review-aar-template)

---

## 1. Scenario Guide

### 1.1 Objectives

| # | Objective                                                        | Success looks like                              |
|---|------------------------------------------------------------------|-------------------------------------------------|
| 1 | Validate that mapped detections fire for exercised techniques    | Alert generated for each in-scope technique     |
| 2 | Validate alert routing and on-call paging                        | Right team paged within the target SLA          |
| 3 | Validate triage and enrichment runbooks                          | Analyst reaches correct verdict from the alert  |
| 4 | Validate red/blue deconfliction                                  | Activity confirmed as exercise, not real threat |
| 5 | Surface detection coverage gaps                                  | Gaps logged with owning team and ticket         |

### 1.2 Roles

| Role            | Responsibility                                                          |
|-----------------|------------------------------------------------------------------------|
| Exercise Control (White Cell) | Owns timeline, injects, deconfliction, and the abort call. |
| Red Team        | Executes/simulates techniques per the [RoE](../roe_template.md).        |
| Blue Team       | Detects, triages, and responds as if it were real (until deconflicted). |
| Observer/Scribe | Records timestamps and evidence for the [AAR](#4-after-action-review-aar-template). |

### 1.3 Scope and safety

- All targets are non-production placeholders (e.g. `app.staging.example.com`).
- `safety.dry_run` stays `true` unless the RoE explicitly authorises active testing.
- `safety.stop_on_prod` stays `true`; any production target aborts the run.
- The **abort phrase** is `[ABORT_PHRASE]`. Anyone may call it; Exercise Control
  enforces it. On abort, follow the
  [incident response playbook](../playbooks/incident_response.md).

### 1.4 Example scenario — "Phished foothold rehearsal" (fictional)

A simulated user opens a phishing lure, leading to script execution and a
credential-access attempt. The blue team should detect the chain and respond.

| Stage | ATT&CK technique             | Red team action (dry-run)        | Expected blue team detection         |
|-------|------------------------------|----------------------------------|--------------------------------------|
| 1     | T1566 Phishing               | Simulated lure delivery          | Mail/security gateway alert          |
| 2     | T1059.001 PowerShell         | Simulated script execution       | EDR script-block / process alert     |
| 3     | T1003 OS Credential Dumping  | Simulated credential access      | EDR credential-access alert          |
| 4     | T1071 Application Layer C2   | Simulated beacon to sinkhole     | Network/proxy anomaly alert          |

> Map the exercised techniques and detections in a config so the
> [detection feedback module](../../src/redguard/modules/detection_feedback.py)
> can score coverage automatically after the run.

### 1.5 Timeline (half-day example)

| Time   | Activity                                                        |
|--------|-----------------------------------------------------------------|
| T-1d   | Confirm RoE signed, scope frozen, deconfliction channel live    |
| T+0:00 | Kickoff; confirm `dry_run`/`stop_on_prod`; confirm abort phrase  |
| T+0:15 | Execute stages 1–4 with spacing for triage                      |
| T+2:00 | Blue team completes triage/response on outstanding alerts        |
| T+3:00 | Hot-wash (immediate verbal debrief) and evidence collection      |
| T+1w   | AAR finalised and gap tickets filed                             |

---

## 2. Exercise Checklists

### 2.1 Pre-exercise (Exercise Control + Red Team)

- [ ] Signed [Rules of Engagement](../roe_template.md) on file; scope frozen.
- [ ] [Legal compliance checklist](../playbooks/legal_compliance_checklist.md) complete.
- [ ] Deconfliction channel and contacts confirmed
      ([deconfliction guide](../playbooks/deconfliction_guide.md)).
- [ ] Config reviewed: `safety.dry_run: true`, `safety.stop_on_prod: true`,
      targets are non-production placeholders.
- [ ] Abort phrase agreed and distributed.
- [ ] Techniques ↔ detections mapping prepared for coverage scoring.
- [ ] Observer/scribe assigned; evidence-capture method ready
      ([evidence handling](../playbooks/evidence_handling.md)).

### 2.2 Pre-exercise (Blue Team)

- [ ] On-call and escalation paths confirmed for the window.
- [ ] SIEM/EDR healthy: ingestion current, no detection rules disabled.
- [ ] Triage runbooks for in-scope techniques accessible.
- [ ] Team briefed that an exercise window is open **without** the specific TTPs.

### 2.3 During exercise

- [ ] Red team logs each action with a UTC timestamp and technique ID.
- [ ] Blue team handles alerts as real until Exercise Control deconflicts.
- [ ] Scribe records: action time, alert time, ack time, verdict time.
- [ ] Any unexpected impact → call abort phrase and run
      [incident response](../playbooks/incident_response.md).

### 2.4 Post-exercise

- [ ] Hot-wash held; immediate observations captured.
- [ ] Coverage scored (detected vs. gaps) per technique.
- [ ] Gaps logged with owning team and tracking ticket.
- [ ] Evidence stored/retained per
      [evidence handling](../playbooks/evidence_handling.md).
- [ ] [AAR](#4-after-action-review-aar-template) drafted within `[N]` business days.
- [ ] Any temporary exercise allowances (allowlists, muted alerts) reverted.

---

## 3. Scoring Rubric

Score each in-scope technique on the dimensions below, then aggregate. Times are
measured from the red team action timestamp.

### 3.1 Per-technique dimensions

| Dimension      | 0 — Missed            | 1 — Partial                          | 2 — Met                                  |
|----------------|-----------------------|--------------------------------------|------------------------------------------|
| **Detection**  | No alert generated    | Low-fidelity/correlated signal only  | Dedicated alert fired                     |
| **Alerting**   | No page/notification  | Notified, wrong/slow routing         | Correct team paged within SLA             |
| **Triage**     | Wrong verdict         | Correct verdict, missing context     | Correct verdict with enrichment           |
| **Response**   | No action taken       | Partial/manual containment           | Runbook executed, containment confirmed   |

Maximum per technique = **8 points** (4 dimensions × 2).

### 3.2 Coverage and timing metrics

| Metric                          | Definition                                                     | Target          |
|---------------------------------|---------------------------------------------------------------|-----------------|
| Detection coverage              | `detected_techniques / total_techniques`                      | `[≥ 90%]`       |
| Mean time to detect (MTTD)      | Action → first alert                                          | `[≤ X min]`     |
| Mean time to acknowledge (MTTA) | Alert → analyst ack                                          | `[≤ X min]`     |
| Mean time to respond (MTTR)     | Ack → containment action                                     | `[≤ X min]`     |
| False-positive rate             | Non-exercise alerts raised during the window (context)        | `[informational]` |

> The [detection feedback module](../../src/redguard/modules/detection_feedback.py)
> computes the coverage ratio and the gap list directly from the
> techniques↔detections mapping.

### 3.3 Overall rating

| Aggregate score (% of max) | Rating              | Interpretation                                  |
|----------------------------|---------------------|-------------------------------------------------|
| 90–100%                    | Strong              | Detections and response validated; minor tuning |
| 70–89%                     | Adequate            | Works, with notable gaps to remediate           |
| 50–69%                     | Needs improvement   | Significant coverage/response gaps               |
| < 50%                      | Critical            | Core detection/response objectives not met       |

---

## 4. After-Action Review (AAR) Template

> Complete within `[N]` business days. Keep it blameless: focus on systems and
> processes, not individuals.

### 4.1 Summary

| Field                | Value             |
|----------------------|-------------------|
| Exercise name        | `[PLACEHOLDER]`   |
| Date / window (UTC)  | `[YYYY-MM-DD]`    |
| Scenario             | `[e.g. Phished foothold rehearsal]` |
| Scope                | `[placeholder targets]` |
| Overall rating       | `[from §3.3]`     |
| Detection coverage   | `[X% — Y/Z techniques]` |
| Participants         | `[roles]`         |

### 4.2 Timeline of events

| UTC time | Actor      | Event / action                         | Detection / response          |
|----------|------------|----------------------------------------|-------------------------------|
| `[hh:mm]`| Red team   | `[technique ID + action]`              | `[alert / none]`              |
| `[hh:mm]`| Blue team  | `[ack / triage / containment]`         | `[verdict]`                   |

### 4.3 What went well

- `[Observation — what worked and why; keep it for reinforcement.]`

### 4.4 What didn't go well

- `[Observation — gap or failure; reference the technique and dimension from §3.]`

### 4.5 Detection coverage gaps

| Technique ID | Detected? | Gap description                 | Owning team | Ticket        |
|--------------|-----------|---------------------------------|-------------|---------------|
| `[Txxxx]`    | `[No]`    | `[no rule / rule too narrow]`   | `[team]`    | `[TICKET-123]`|

### 4.6 Action items

| # | Action item                          | Owner      | Priority | Due date     | Status |
|---|--------------------------------------|------------|----------|--------------|--------|
| 1 | `[e.g. add detection for T1003]`     | `[owner]`  | `[High]` | `[YYYY-MM-DD]` | Open   |

### 4.7 Sign-off

| Role             | Name            | Date          |
|------------------|-----------------|---------------|
| Exercise Control | `[PLACEHOLDER]` | `[YYYY-MM-DD]`|
| Red Team Lead    | `[PLACEHOLDER]` | `[YYYY-MM-DD]`|
| Blue Team Lead   | `[PLACEHOLDER]` | `[YYYY-MM-DD]`|

---

## Related documents

- [Rules of Engagement Template](../roe_template.md)
- [Deconfliction Guide](../playbooks/deconfliction_guide.md)
- [Incident Response Playbook](../playbooks/incident_response.md)
- [Evidence Handling Playbook](../playbooks/evidence_handling.md)
- [Risk Matrix Schema](../risk_matrix_schema.md)
- [Detection Feedback Module](../../src/redguard/modules/detection_feedback.py)
