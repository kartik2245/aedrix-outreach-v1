# Smartlead Production Setup & Integration Guide

This document outlines the production architecture, configuration, safety gates, and operational procedures for connecting the **Aedrix AI Cold Outreach System** with **Smartlead** (https://server.smartlead.ai/api/v1).

---

## 1. Architecture Overview

```text
Deepline Research Export
        ↓
Deepline Export Adapter (src/deepline_export_adapter.py)
        ↓
Research Normalizer (src/research_normalizer.py)
        ↓
Evidence Validator (src/evidence_validator.py)
        ↓
ICP Engine (src/icp/icp_engine.py + config/icp_config.json)
        ↓
Lead Intelligence / Scoring (src/lead_intelligence.py)
        ↓
VoC Engine (src/personalization/voc_engine.py)
        ↓
Claude Personalization (src/integrations/claude_client.py)
        ↓
Personalization QA (src/personalization/personalization_qa.py)
        ↓
HUMAN APPROVAL GATE (src/approval/approval_engine.py + data/approval_queue.json)
        ↓ (Only APPROVED + smartlead_eligible=True)
Smartlead Production Runner / Staging Runner
        ↓
Smartlead Campaigns & Leads (DRAFT / PAUSED / ACTIVE)
        ↓
Smartlead Webhook Events
        ↓
n8n Event-Driven Orchestration (n8n/aedrix_outreach_workflow.json)
        ↓
Claude Follow-Up Generation & State Machine
```

---

## 2. Environment Variables & Configuration

Configure these values in `.env` (derived from `.env.example`):

```bash
# Anthropic Claude API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Smartlead Production API Configuration
SMARTLEAD_API_KEY=your_smartlead_api_key_here
SMARTLEAD_BASE_URL=https://server.smartlead.ai/api/v1
SMARTLEAD_LIVE=false
SMARTLEAD_CAMPAIGN_ID=

# Batch Execution Settings
BATCH_SIZE=400

# Safety Controls - MUST REMAIN FALSE UNTIL EXPLICIT HUMAN UNLOCK
DRY_RUN=true
SEND_EMAILS=false
PRODUCTION_SEND_CONFIRMATION=false
```

---

## 3. The Three Operational Modes

| Mode | Environment Settings | API Behavior | Email Sending | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Mode 1: Offline Dry Run** | `DRY_RUN=true`<br>`SMARTLEAD_LIVE=false`<br>`SEND_EMAILS=false` | 0 API calls | 0 emails | Generates `data/smartlead_staging_plan.json` for review. |
| **Mode 2: API Test Mode** | `DRY_RUN=false`<br>`SMARTLEAD_LIVE=true`<br>`SEND_EMAILS=false` | Real API calls to Smartlead | 0 emails (PAUSED/DRAFT) | Creates campaign, configures sequence, uploads test/approved leads in paused state. |
| **Mode 3: Production Send** | `DRY_RUN=false`<br>`SMARTLEAD_LIVE=true`<br>`SEND_EMAILS=true`<br>`PRODUCTION_SEND_CONFIRMATION=true` | Real API calls | Active outreach | Activates campaign and starts sending scheduled emails. |

---

## 4. Human Approval Gate Rules

Smartlead **NEVER** receives leads directly from Deepline or AI generators.

1. All newly generated lead drafts enter `data/approval_queue.json` in state `PENDING_REVIEW` (`smartlead_eligible=False`).
2. Disqualified leads (`HARD_DISQUALIFIED`, `CAMPAIGN_EXCLUDED`, `INVALID_BOUNCED`, or QA `FAIL`) are automatically `BLOCKED`.
3. Leads with `NO_STRONG_SIGNAL` use the baseline value proposition and are flagged `flag_no_strong_signal=True`.
4. Only leads explicitly marked `APPROVED` via CLI/API receive `smartlead_eligible=True`.
5. If a human edits a draft, its status transitions to `EDITED` (`smartlead_eligible=False`), requiring explicit re-approval.
6. The original AI drafts (`email_1_original`, `followup_a_original`, `followup_b_original`) remain permanently immutable.

---

## 5. Lead Data Mapping & Custom Fields

The system deterministically maps internal `ApprovalRecord` fields to Smartlead custom variables:

| Smartlead Field | Source Internal Field | Description |
| :--- | :--- | :--- |
| `email` | `record.email` | Recipient email address |
| `first_name` | Split from `record.contact` | Recipient first name |
| `last_name` | Split from `record.contact` | Recipient last name |
| `company_name` | `record.company` | Company name |
| `website` | `record.metadata.website` | Company domain / website |
| `linkedin_profile` | `record.metadata.linkedin_url` | Prospect LinkedIn profile |
| `{{lead_id}}` | `record.lead_id` | Deterministic internal lead ID |
| `{{job_title}}` | `record.title` | Contact job title |
| `{{priority}}` | `record.priority` | Priority tier (`P1`, `P2`, `P3`) |
| `{{opportunity_score}}` | `record.opportunity_score` | 0–100 Opportunity score |
| `{{accessibility_score}}` | `record.accessibility_score` | 0–100 Accessibility score |
| `{{outreach_priority_index}}`| `record.outreach_priority_index` | 0–100 Combined Index |
| `{{personalization_note}}` | `record.personalization_note` | Evidenced personalization hook |
| `{{voc_angle}}` | `record.voc_angle` | Customer pain point angle |
| `{{email_1_subject}}` | Generated Subject | Email 1 subject line |
| `{{email_1_body}}` | `edited_email_1` or `email_1_original` | Active Email 1 body text |
| `{{followup_a_subject}}` | Generated Subject | Follow-up A subject line |
| `{{followup_a_body}}` | `edited_followup_a` or `followup_a_original` | Active Follow-up A body text |
| `{{followup_b_subject}}` | Generated Subject | Follow-up B subject line |
| `{{followup_b_body}}` | `edited_followup_b` or `followup_b_original` | Active Follow-up B body text |

---

## 6. Campaign Sequence & Timing

The system strictly enforces the business timing rules:

```text
STEP 1: EMAIL 1 (Day 0)
   ↓
WAIT 2 DAYS (48 Hours)
   ↓
CHECK BEHAVIOR / OPEN
   ├── IF OPENED → FOLLOW-UP A (Scheduled after 1 day delay)
   └── IF UNOPENED → FOLLOW-UP B (Scheduled after original 2-day wait, pivoted angle)
```

---

## 7. Webhook Normalization & Event Handling

Smartlead webhooks are received and normalized into `SmartleadWebhookEvent`:

| Incoming Smartlead Event | Internal Event | Next Action |
| :--- | :--- | :--- |
| `email_open` / `EMAIL_OPENED` | `EMAIL_OPENED` | Moves state to `EMAIL_1_OPENED`, schedules Follow-up A after 1 day. |
| `email_reply` / `EMAIL_REPLIED` | `EMAIL_REPLIED` | Evaluated by Reply Classifier: <br>• **POSITIVE** $\rightarrow$ Immediate Slack sales handoff alert + Pause lead outreach.<br>• **NEGATIVE** $\rightarrow$ Suppress lead.<br>• **OOO** $\rightarrow$ Log and wait.<br>• **UNSUBSCRIBE** $\rightarrow$ Global opt-out. |
| `email_bounce` / `EMAIL_BOUNCED`| `EMAIL_BOUNCED` | Moves state to `STOPPED_BOUNCED`, pauses lead in Smartlead. |
| `email_unsubscribe` | `EMAIL_UNSUBSCRIBED` | Moves state to `STOPPED_UNSUBSCRIBED`, pauses lead in Smartlead. |

---

## 8. Audit Logging

Every Smartlead interaction is recorded in `data/logs/smartlead_audit.jsonl`:

```json
{
  "timestamp": "2026-08-17T10:45:00.000000+00:00",
  "action": "SMARTLEAD_LEAD_UPLOADED",
  "lead_id": "lead_bowmer_kirkland_b_k_john_foster",
  "company": "Bowmer & Kirkland (B&K)",
  "provider": "SMARTLEAD",
  "status": "SUCCESS",
  "campaign_id": "123456",
  "approval_status": "APPROVED",
  "reviewer": "Sarah Campaign Lead",
  "dry_run": false,
  "error": null,
  "details": {"email": "j.foster@bandk.co.uk", "batch": 1}
}
```

---

## 9. Emergency Pause & Rollback Procedure

To immediately pause all active outreach across Smartlead:

```powershell
# 1. Using Python API
.venv\Scripts\python -c "from src.integrations.smartlead_client import SmartleadClient; client = SmartleadClient(); client.pause_campaign('YOUR_CAMPAIGN_ID'); print('Campaign PAUSED')"

# 2. Or reset environment variables
set SEND_EMAILS=false
set PRODUCTION_SEND_CONFIRMATION=false
```
