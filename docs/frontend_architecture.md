# Operator Frontend & FastAPI Architecture

This document describes the technical architecture of the **Aedrix AI Cold Outreach Operator Dashboard**, bridging the **React + TypeScript + Vite** frontend with the existing **Python 3.12** outreach services via **FastAPI**.

---

## 1. Architecture Overview

```text
React + TypeScript + Vite (Port 5173 / Production Static Assets)
        │
        │ HTTP REST Requests (/api/...)
        ▼
FastAPI Application Bridge (app/main.py, Port 8000)
        │
        ├── app/api/dashboard.py   → Aggregated Stats & Quality Funnel
        ├── app/api/leads.py       → Lead Intelligence Dossiers & Filters
        ├── app/api/approvals.py   → Human Approval Engine & Safety Gating
        ├── app/api/campaigns.py   → State Machine Graph & Smartlead Staging
        └── app/api/system.py      → Status Matrix & Zero-Risk Demo Pipeline
        │
        ▼
Existing Python Core Engines (Single Source of Truth)
        ├── src/approval/approval_engine.py
        ├── src/lead_intelligence.py
        ├── src/research_pipeline.py
        ├── src/icp/icp_engine.py
        ├── src/personalization/voc_engine.py
        ├── src/personalization/personalization_qa.py
        ├── src/integrations/claude_client.py
        ├── src/integrations/smartlead_client.py
        ├── src/smartlead_staging_runner.py
        ├── src/smartlead_production_runner.py
        └── src/outreach_state_machine.py
```

---

## 2. Key Architectural Guarantees

1. **Backend as Single Source of Truth**:
   The frontend is strictly an operator interface. It contains **no business logic**, no separate qualification criteria, and no duplicate approval state transitions. All state transitions are executed by calling `src/approval/approval_engine.py` via FastAPI.

2. **Immutable AI Drafts**:
   When an operator edits an email draft in the frontend, the original AI-generated text (`email_1_original`, `followup_a_original`, `followup_b_original`) remains permanently immutable in the queue store. The draft status transitions to `EDITED` and requires explicit subsequent re-approval before becoming eligible for Smartlead.

3. **Zero-Risk Default Safety**:
   - `DRY_RUN=true`
   - `SEND_EMAILS=false`
   - `SMARTLEAD_LIVE=false`
   Opening or browsing the dashboard **never** invokes paid external APIs or sends live prospect emails.

4. **Credential Protection**:
   All API responses mask sensitive secrets (e.g. `ANTHROPIC_API_KEY`, `SMARTLEAD_API_KEY`) using `SmartleadClient.mask_api_key()` (`************7890`).

---

## 3. Frontend Pages & Capabilities

| Page | Path / Route | Capabilities |
| :--- | :--- | :--- |
| **Dashboard** | Tab: `dashboard` | Executive KPIs, research funnel, pending approvals preview, live safety indicators (`REAL EMAILS: 0`), and "Run Demo Pipeline" button. |
| **Leads Dossier** | Tab: `leads` | Contractor directory with multi-filter (ICP, Priority, Approval, Personalization), live search, sortable columns, and pagination. |
| **Lead Detail** | Click any lead | Complete contractor dossier: Decision-maker profile, opportunity/accessibility scoring breakdown, verified research evidence audit, VoC angle, and 3-stage email draft preview (Email 1, Follow-up A, Follow-up B) with anti-hallucination QA status. |
| **Approval Queue** | Tab: `approvals` | Operator review queue with single-click Approve, Edit (triggers re-approval), Reject, and Block actions. |
| **Campaign Flow** | Tab: `campaign` | Interactive visual sequence diagram enforcing the 2-day initial wait rule and webhook event branches (Positive Reply $\rightarrow$ Sales Handoff, Bounce/Unsub $\rightarrow$ Stop). |
| **Smartlead Staging** | Tab: `staging` | Staged batches inspector (Batch size: 400), custom field preview (`{{personalization_note}}`, `{{voc_angle}}`, `{{outreach_priority_index}}`), and raw JSON download. |
| **System & Safety** | Tab: `system` | Integration matrix (Deepline, Claude, Smartlead, n8n), active safety flags, masked environment variable inspection, and real-time audit log stream. |

---

## 4. API Endpoints

- `GET /api/dashboard/stats`: Aggregated metrics and safety status.
- `GET /api/leads`: Paginated, filtered, and sorted lead list.
- `GET /api/leads/{lead_id}`: Full lead intelligence dossier and email drafts.
- `GET /api/approvals`: Approval records filtered by status.
- `POST /api/approvals/{lead_id}/approve`: Approves draft for Smartlead staging.
- `POST /api/approvals/{lead_id}/edit`: Saves edited draft copy; transitions status to `EDITED`.
- `POST /api/approvals/{lead_id}/reject`: Rejects draft.
- `POST /api/approvals/{lead_id}/block`: Blocks lead from outreach.
- `GET /api/campaign`: Campaign sequence definition and state machine states.
- `GET /api/smartlead/staging`: Staging plan generation and batch preview.
- `GET /api/system/status`: Integration matrix and audit logs.
- `POST /api/demo/run`: Executes local sample pipeline and staging planner (0 emails sent).
