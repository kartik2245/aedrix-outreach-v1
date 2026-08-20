# Multi-Campaign Management & Isolation

## 1. Overview
The Aedrix Outreach System enforces strict campaign isolation across all layers:
- Dynamic ICP specifications
- Deepline discovery runs
- Research dossiers
- Generated drafts and sequences
- Human approval queue records
- Smartlead staging payloads

---

## 2. Multi-Campaign Metadata Tracking

Every lead dossier (`LeadIntelligenceOutput`) and approval queue item (`ApprovalRecord`) carries explicit lineage metadata:

```json
{
  "campaign_id": "camp_uk_tier_1_contractors_20260817",
  "icp_id": "icp_camp_uk_tier_1_contractors_20260817",
  "icp_version": "1.1.0",
  "deepline_run_id": "run_20260817_055544_a1b2c3d4"
}
```

### Isolation Guarantees:
1. **No Cross-Contamination**: Leads from different campaigns are never merged into a single Smartlead batch or outreach run.
2. **Version Pinning**: If an ICP is updated to version `1.1.0`, previously generated drafts remain pinned to version `1.0.0` with clear lineage.
3. **Dedicated Campaign Runs**: Operators can filter the dashboard, lead dossier, and approval queue by `campaign_id`.
