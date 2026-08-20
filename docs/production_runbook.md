# Aedrix Outreach Production Runbook

**Audience:** Campaign Operators, Sales Operations, Systems Administrators.  
**Objective:** Provide safe, step-by-step instructions for operating the Aedrix Cold Outreach System without accidental email dispatch or credit loss.

---

## 1. Pre-Flight Safety Verification

Before running any commands, confirm your active environment configuration:

```powershell
# Verify environment safety flags
.venv\Scripts\python -c "import os; from src.integrations.smartlead_client import load_env_file_if_present; load_env_file_if_present(); print('DRY_RUN:', os.getenv('DRY_RUN', 'true')); print('SEND_EMAILS:', os.getenv('SEND_EMAILS', 'false')); print('SMARTLEAD_LIVE:', os.getenv('SMARTLEAD_LIVE', 'false'))"
```

**Standard Safe Defaults:**
- `DRY_RUN`: `true`
- `SEND_EMAILS`: `false`
- `SMARTLEAD_LIVE`: `false`
- `PRODUCTION_SEND_CONFIRMATION`: `false`

---

## 2. Standard Campaign Workflow

### Step 1: Run Deepline Research & Draft Generation
```powershell
# Process research leads, run ICP/VoC/Claude, QA, and populate approval queue
.venv\Scripts\python src/production_batch_runner.py
```
*Outputs: `data/claude_personalization_drafts.json`, `data/approval_queue.json`*

---

### Step 2: Review and Approve Leads via Human Approval CLI

Inspect the queue of generated drafts:
```powershell
# 1. List all pending reviews
.venv\Scripts\python src/approval_cli.py list --status PENDING_REVIEW

# 2. Inspect a specific lead's evidence, scores, and email copy
.venv\Scripts\python src/approval_cli.py show lead_kier_group_plc_colin_bell

# 3. Explicitly approve a lead for outreach
.venv\Scripts\python src/approval_cli.py approve lead_kier_group_plc_colin_bell --reviewer "Operator Name"

# 4. Optional: Edit copy if needed (note: edited copy requires re-approval)
.venv\Scripts\python src/approval_cli.py edit lead_kier_group_plc_colin_bell --email-1 "Custom adjusted copy..." --reviewer "Operator Name"
.venv\Scripts\python src/approval_cli.py approve lead_kier_group_plc_colin_bell --reviewer "Operator Name"

# 5. Reject or block any unsuitable leads
.venv\Scripts\python src/approval_cli.py reject lead_balfour_beatty_plc_jon_ozanne --reason "Targeting later quarter"
```

---

### Step 3: Run Offline Smartlead Staging Planner
Verify exactly what payloads and variables would be sent to Smartlead:
```powershell
.venv\Scripts\python src/smartlead_staging_runner.py
```
*Outputs: `data/smartlead_staging_plan.json` (0 API calls executed).*

Review `data/smartlead_staging_plan.json`:
- Confirm only `APPROVED` leads are included.
- Verify custom variables: `{{personalization_note}}`, `{{voc_angle}}`, `{{opportunity_score}}`, etc.
- Verify that sequence delay is 2 days (48h).

---

### Step 4: Run Safe Smartlead API Test (Mode 2)
In this mode, campaigns and leads are uploaded to Smartlead in **PAUSED/DRAFT** state. **Zero emails are sent.**

```powershell
# In PowerShell:
$env:SMARTLEAD_LIVE="true"
$env:SEND_EMAILS="false"
$env:DRY_RUN="false"

.venv\Scripts\python src/smartlead_production_runner.py
```
*Outputs: Logs in `data/logs/smartlead_audit.jsonl`, Campaign ID created in Smartlead.*

---

### Step 5: Live Production Send (Mode 3 - Human Sign-Off Required)
> [!CAUTION]
> This will activate email dispatch in Smartlead. Only execute after explicit operator sign-off and lead verification.

```powershell
# In PowerShell:
$env:SMARTLEAD_LIVE="true"
$env:SEND_EMAILS="true"
$env:PRODUCTION_SEND_CONFIRMATION="true"
$env:DRY_RUN="false"

.venv\Scripts\python src/smartlead_production_runner.py --confirm-production-send
```

---

## 3. Emergency Campaign Pause

If you need to halt outreach immediately:

```powershell
# Immediately pause via Python API
.venv\Scripts\python -c "from src.integrations.smartlead_client import SmartleadClient; client = SmartleadClient(live=True, dry_run=False); client.pause_campaign('YOUR_CAMPAIGN_ID'); print('Campaign successfully paused.')"
```

Alternatively, in the Smartlead Web UI:
1. Log into `https://app.smartlead.ai`.
2. Go to **Campaigns**.
3. Toggle status switch from **Active** to **Paused**.

---

## 4. Webhook & Alert Monitoring

- **Positive Replies:** Incoming positive replies trigger an immediate Slack alert to `#sales-hot-leads` requiring a human sales response within 1 hour.
- **Bounces & Unsubscribes:** The state machine automatically marks leads `STOPPED_BOUNCED` or `STOPPED_UNSUBSCRIBED` and pauses outreach for that contact in Smartlead.

---

## 5. Audit Trail Verification

Inspect the append-only audit trail at any time:
```powershell
# View recent audit events
Get-Content data/logs/smartlead_audit.jsonl -Tail 20
```
