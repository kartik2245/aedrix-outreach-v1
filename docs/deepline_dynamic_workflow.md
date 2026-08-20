# Deepline Dynamic Discovery & Lead Enrichment Workflow

## 1. Overview
The Deepline Discovery integration connects human-approved ICP specifications (`ICPConfig`) to large-scale contractor discovery (100 to 5,000+ accounts).

Discovered leads flow directly through:
1. **Research Normalization & Evidence Validation**
2. **Dynamic ICP Qualification & Hard Disqualification**
3. **Multi-Dimensional Opportunity & Accessibility Scoring**
4. **Voice-of-Customer (VoC) Personalization**
5. **Claude Batch Email Generation & QA Validation**
6. **Human Email Approval Gate Enrollment**

---

## 2. Safety Controls & Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DEEPLINE_LIVE` | `false` | When `false`, executes high-fidelity simulated discovery without API calls. |
| `DEEPLINE_RUN_CONFIRMATION` | `false` | Must be explicitly `true` to permit paid credit consumption in live discovery. |
| `DEEPLINE_API_KEY` | `""` | Deepline API secret key (automatically masked in logs). |
| `DEEPLINE_BASE_URL` | `https://api.deepline.ai/v1` | Deepline REST API endpoint. |

---

## 3. Execution Artifacts (`data/deepline_runs/{run_id}/`)

Every discovery execution creates an isolated run folder containing:

1. `icp.json`: Snapshot of the active approved `ICPConfig`.
2. `discovery_request.json`: The compiled `DeeplineDiscoveryRequest` sent to Deepline.
3. `export.json`: Full raw lead dataset returned by Deepline.
4. `run_metadata.json`: Comprehensive execution metrics (counts for discovered, valid, qualified, disqualified, excluded, P1, P2, P3, and safety status).

---

## 4. Lead Batching & Chunking

| Engine | Chunk Size | Rationale |
|---|---|---|
| **Claude Personalization** | `25 leads/chunk` | Prevents token window exhaustion and manages API latency. |
| **Deepline Discovery** | `400 leads/batch` | Matches upstream pagination limits. |
| **Smartlead Staging** | `400 leads/batch` | Conforms to Smartlead CSV/API ingestion limits. |
