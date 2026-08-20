# Aedrix AI Cold Outreach System — Operator SaaS Platform

> **ZERO-RISK SAFETY GUARANTEES**  
> - **0** real emails sent (`DRY_RUN=true`, `SEND_EMAILS=false`).
> - **0** real prospects contacted.
> - **0** Smartlead, Apollo, or Deepline credits purchased or consumed in Demo mode.
> - **0** real client mailboxes connected.
> - **Human Approval Gate**: AI drafts are NEVER eligible for Smartlead without explicit human approval.
> - **Strict Isolation**: Demo records are tagged with `environment='DEMO'`; demo reset operations never touch production data.

---

## 1. Quick Start: One-Click Windows Launchers

The entire platform is configured for **One-Click Launching** on Windows:

### A. One-Click Demo Mode (Safe Simulation)
Double-click `START_AEDRIX_DEMO.bat` or run:
```cmd
START_AEDRIX_DEMO.bat
```
- Sets `APP_MODE=DEMO`, `DRY_RUN=true`, `SEND_EMAILS=false`.
- Seeds 10 realistic UK B2B construction contractor leads (Balfour Beatty, Mace, Morgan Sindall, Kier, Willmott Dixon, Bowmer & Kirkland, Wates, Multiplex, plus disqualified test cases).
- Verifies and builds the React frontend bundle.
- Starts the FastAPI operator service on `http://localhost:8000`.
- Automatically opens your default browser at `http://localhost:8000`.

### B. One-Click Production Mode
Double-click `START_AEDRIX_PRODUCTION.bat` or run:
```cmd
START_AEDRIX_PRODUCTION.bat
```
- Performs pre-flight database diagnostics (`python scripts/health_check.py`).
- Connects directly to **Supabase PostgreSQL**.
- Sets `APP_MODE=PRODUCTION`.
- Preserves `SEND_EMAILS=false` safety flag by default.

### C. Graceful Process Terminator
```cmd
scripts\stop_aedrix.bat
```
Terminates background FastAPI and Vite services on ports 8000 and 5173 cleanly.

---

## 2. Platform Architecture & Mode Separation

```text
                                  ┌─────────────────────────────┐
                                  │   FastAPI Bridge (Port 8000)│
                                  └──────────────┬──────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   ▼                                                           ▼
       ┌───────────────────────┐                                   ┌───────────────────────┐
       │       DEMO MODE       │                                   │    PRODUCTION MODE    │
       │  (Safe Simulation)    │                                   │  (Guarded Live Ops)   │
       ├───────────────────────┤                                   ├───────────────────────┤
       │ • 0 Paid API Credits  │                                   │ • Supabase PostgreSQL │
       │ • 0 Real Emails Sent  │                                   │ • Real Deepline / API │
       │ • Isolated Demo Data  │                                   │ • Real Smartlead API  │
       │ • Full UI Walkthrough │                                   │ • SEND_EMAILS=false   │
       │ • environment='DEMO'  │                                   │ • Human Approval Req. │
       └───────────────────────┘                                   └───────────────────────┘
```

### Safety Gates & Switching Protection
- **Header Badge**: Prominently shows `DEMO MODE 🟡 SAFE SIMULATION` vs `PRODUCTION MODE 🟢 PRODUCTION`.
- **Confirmation Modal**: Switching from DEMO to PRODUCTION in the UI requires typing `"ENABLE PRODUCTION"` in a confirmation dialog.
- **Demo Reset Isolation**: `POST /api/demo/reset` and `scripts/reset_demo.py` delete ONLY `environment='DEMO'` records. Production campaigns, ICPs, and leads are 100% untouched.

---

## 3. Complete Outreach Pipeline

```text
1. manual icp generator
      ↓
2. Human ICP Approval Gate (data/icp_approval_queue.json & PostgreSQL)
      ↓
3. Deepline Discovery Ingestion (UK Main Contractors £10M+ Revenue)
      ↓
4. Evidence & Normalization Engine (Zero-Hallucination Claim Validation)
      ↓
5. Lead Intelligence & Multi-Tier Scoring (Opportunity, Accessibility, OPI, P1/P2/P3)
      ↓
6. Voice-of-Customer (VoC) Personalization Engine (Pre-Construction Document Control)
      ↓
7. Claude 3-Touch Email Generation (Email 1, Follow-up A, Follow-up B)
      ↓
8. 10-Point Personalization QA & Hallucination Guard
      ↓
9. HUMAN EMAIL APPROVAL GATE (Approve, Edit Copy, Block, or Reject)
      ↓
10. Smartlead Campaign Staging & Batch Planner (400-lead batches)
      ↓
11. n8n Event-Driven Orchestration & Dynamic Follow-ups
```

---

## 4. CLI Diagnostic & Management Tools

| Command | Description |
|---|---|
| `python scripts/health_check.py` | Inspects database connection, latency, mode, and safety status. |
| `python scripts/seed_demo.py` | Idempotently seeds the 10 UK construction demo contractor leads. |
| `python scripts/reset_demo.py` | Safely wipes only demo records and restores fresh seed state. |
| `python scripts/export_db_to_json.py` | Exports Supabase PostgreSQL data to local JSON backups. |
| `.venv\Scripts\pytest -v` | Runs the complete 150-test automated test suite. |

---

## 5. Primary Database & Alembic Migrations

The platform utilizes **Supabase PostgreSQL** as its primary production database:
- **16 Normalized SQLAlchemy 2.x Models**: `Campaign`, `ICP`, `ICPVersion`, `ICPApproval`, `Lead`, `LeadResearch`, `LeadEvidence`, `VoCContext`, `EmailDraft`, `EmailApproval`, `DeeplineRun`, `DeeplineRunLead`, `SmartleadCampaign`, `SmartleadSequenceStep`, `SmartleadUploadBatch`, `AuditLog`.
- **Alembic Migrations**:
  - `001_initial_normalized_schema`: Initial normalized PostgreSQL schema with indexes and foreign keys.
  - `002_add_environment_isolation`: Adds indexed `environment` (`VARCHAR(32)`) column to isolate DEMO vs PRODUCTION records.

To apply migrations manually:
```bash
.venv\Scripts\alembic upgrade head
```

---

## 6. Automated Verification & Test Suite

All 150 automated tests pass with 100% pass rate:
```bash
.venv\Scripts\pytest -v
```
Verified test coverage includes:
- Mode detection & runtime switching
- Confirmation modal enforcement (`ENABLE PRODUCTION`)
- Database connectivity, query latency, and JSON fallback
- Zero real email sending & zero API credit consumption
- Dynamic ICP generation, human approval, versioning, and editing
- Deepline discovery simulation & preview
- Lead scoring, opportunity indexing, and VoC mapping
- 10-point Personalization QA & anti-hallucination guards
- Human Email Approval Gate (approve, edit, block, reject)
- Smartlead 2-day wait sequencing and 400-lead batch chunking
