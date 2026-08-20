# Dynamic Claude ICP Designer & Safety Specification

## 1. Overview
The **Aedrix Dynamic ICP Designer** allows marketing operators to generate campaign-tailored Ideal Customer Profiles (ICPs) using natural language requirements (e.g., *"Target UK construction companies with digital transformation initiatives"*).

Claude interprets the intent and compiles a structured `ICPConfig` adhering to strict schema rules, zero-hallucination validation, and human review gates.

---

## 2. ICP Lifecycle & State Machine

```
   [Natural Language Requirement]
                │
                ▼
        [Claude ICP Designer]
                │
                ▼
      ┌────────────────────┐
      │   PENDING_REVIEW   │ ◄── [Default State, deepline_eligible=False]
      └─────────┬──────────┘
                │
        ┌───────┴───────────────┬─────────────────┐
        ▼                       ▼                 ▼
 ┌──────────────┐        ┌──────────────┐  ┌──────────────┐
 │   APPROVED   │        │   REJECTED   │  │   BLOCKED    │
 └──────┬───────┘        └──────────────┘  └──────────────┘
        │ (deepline_eligible=True)
        │
        ├─────────────────────────────┐
        │                             │
        ▼                             ▼
 [Deepline Discovery Run]      [Operator Edit]
                                      │
                                      ▼
                               ┌──────────────┐
                               │    EDITED    │ (deepline_eligible=False)
                               └──────┬───────┘ (Requires Re-Approval)
                                      │
                                      ▼
                             [Back to Review]
```

### Safety Guarantees:
1. **Pending Status by Default**: Newly designed ICPs start as `PENDING_REVIEW` with `deepline_eligible=False`.
2. **Immutable Claude Original**: The initial Claude output is preserved permanently in `original_claude_icp`.
3. **Edit Invalidation**: Editing an approved ICP invalidates approval, sets status to `EDITED`, sets `deepline_eligible=False`, increments the semantic version (e.g. `1.0.0` $\rightarrow$ `1.1.0`), and records a detailed diff in `edit_history`.
4. **Structured Audit Trail**: Every status change, edit, review, and run execution records an `ICPAuditEntry` with timestamp and reviewer ID.

---

## 3. Data Model (`src/icp/icp_models.py`)

```python
class ICPConfig(BaseModel):
    id: str
    campaign_id: str
    name: str
    version: str
    campaign_description: str
    geography: GeographyConfig
    industries: List[str]
    allowed_industry_keywords: List[str]
    disallowed_industry_keywords: List[str]
    company_size: str
    minimum_employees: Optional[int]
    maximum_employees: Optional[int]
    minimum_revenue: Optional[float]
    maximum_revenue: Optional[float]
    target_personas: List[str]
    persona_title_keywords: List[str]
    positive_signals: List[str]
    negative_signals: List[str]
    hard_disqualifiers: List[HardDisqualificationRule]
    campaign_exclusions: List[CampaignExclusionRule]
    reasoning: Optional[str]
    status: ICPStatus
```

---

## 4. API Endpoints (`app/api/icp.py`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/icp/generate` | Generates a new `ICPConfig` from natural language and enrolls it into the queue. |
| `GET` | `/api/icp` | Lists all ICP records (supports `status` and `campaign_id` filters). |
| `GET` | `/api/icp/{icp_id}` | Retrieves an ICP record including edit history and audit trail. |
| `POST` | `/api/icp/{icp_id}/approve` | Approves an ICP, setting `deepline_eligible=True`. |
| `POST` | `/api/icp/{icp_id}/reject` | Rejects an ICP with a required reason. |
| `PUT` | `/api/icp/{icp_id}` | Updates criteria, resets status to `EDITED`, and requires re-approval. |
| `POST` | `/api/icp/{icp_id}/deepline-preview` | Previews the Deepline discovery specification without running network requests. |
| `POST` | `/api/icp/{icp_id}/deepline-run` | Executes Deepline discovery for 100–5000 leads (requires `APPROVED` status). |
