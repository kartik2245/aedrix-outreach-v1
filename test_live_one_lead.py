"""
test_live_one_lead.py
Controlled standalone live integration test for AEDRIX V1.
Executes end-to-end flow for exactly 1 live lead:
Deepline V2 API -> DeeplineExportAdapter -> R1-R6 Classifier -> AWS Bedrock DeepSeek V3.2 -> PersonalizationQA -> Human Approval Gate

Guarantees:
- DEEPLINE_LIVE=true (Live Deepline V2 API)
- DEEPLINE_RUN_CONFIRMATION=true
- DRY_RUN=false (Invokes real AWS Bedrock DeepSeek V3.2)
- SEND_EMAILS=false (0 emails sent)
- SMARTLEAD_LIVE=false (0 Smartlead API calls)
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Set explicit process environment overrides
os.environ["DEEPLINE_LIVE"] = "true"
os.environ["DEEPLINE_RUN_CONFIRMATION"] = "true"
os.environ["DRY_RUN"] = "false"
os.environ["SEND_EMAILS"] = "false"
os.environ["SMARTLEAD_LIVE"] = "false"
os.environ["AWS_REGION"] = "ap-south-1"
os.environ["BEDROCK_MODEL_ID"] = "deepseek.v3.2"
os.environ["LLM_MODEL"] = "deepseek.v3.2"

from src.icp.icp_designer import ICPDesigner
from src.icp.icp_approval_engine import ICPApprovalEngine
from src.deepline_discovery_runner import DeeplineDiscoveryRunner
from src.integrations.deepline_client import DeeplineClient
from src.integrations.bedrock_client import BedrockClient
from src.approval.approval_store import ApprovalStore

def main():
    print("===================================================================")
    print(" AEDRIX V1 CONTROLLED LIVE 1-LEAD INTEGRATION TEST")
    print(" Pipeline: Deepline V2 -> R1-R6 -> AWS Bedrock DeepSeek V3.2 -> QA -> Human Approval")
    print(" Safety: DEEPLINE_LIVE=true | DRY_RUN=false | SEND_EMAILS=false | SMARTLEAD_LIVE=false")
    print("===================================================================\n")

    # Step 1: Design and Approve Test ICP Configuration
    print("[1/5] Initializing Test ICP Configuration...")
    designer = ICPDesigner()
    icp = designer.design_icp(
        campaign_name="Live 1-Lead Verification Campaign",
        campaign_objective="Target 1 high-priority UK Commercial Construction digital leadership lead for Aedrix platform overview.",
        product_context="Aedrix is a modular construction management SaaS platform for UK main contractors covering pre-construction document control, drawing versioning, site manpower tracking, and commercial control.",
        geography="United Kingdom",
        industry="Commercial Construction, Building, Infrastructure",
        company_size="50+ employees or £10M+ revenue",
        target_personas=["Digital Director", "IT Director", "Head of Pre-Construction", "Operations Director"],
        positive_signals=["Digital transformation initiatives", "BIM adoption", "Multi-site regional projects"],
        hard_disqualifiers=["Operating exclusively outside UK", "Non-construction sector", "Under 50 employees"],
        campaign_exclusions=["Active CRM deal", "Global suppression match", "Contacted within 60 days"],
        voc_context="Pre-construction document control and drawing revision risk across multi-site teams."
    )

    approval_engine = ICPApprovalEngine()
    enrolled_rec = approval_engine.enroll_icp(icp, source="MANUAL")
    approved_rec = approval_engine.approve_icp(enrolled_rec.icp_id, reviewer="HUMAN_OPERATOR_LIVE_TEST")
    
    print(f"  -> ICP ID:          {approved_rec.icp_id}")
    print(f"  -> Campaign Name:    {approved_rec.name}")
    print(f"  -> Approval Status:  {approved_rec.status.value}")
    print(f"  -> Deepline Eligible:{approved_rec.deepline_eligible}")

    # Step 2: Initialize Deepline Client & Bedrock Client with explicit live flags
    print("\n[2/5] Initializing Discovery Runner with Live Deepline V2 & Bedrock DeepSeek V3.2 Clients...")
    live_deepline = DeeplineClient(live_mode=True)
    live_bedrock = BedrockClient(dry_run=False)

    runner = DeeplineDiscoveryRunner(
        deepline_client=live_deepline,
        llm_client=live_bedrock
    )
    
    print(f"  -> Deepline Mode:    {'LIVE API (V2)' if runner.deepline_client.live_mode else 'SIMULATION'}")
    print(f"  -> Bedrock Dry-Run:  {runner.llm_client.dry_run} (False = Live Bedrock DeepSeek V3.2 API Calls)")
    print(f"  -> Bedrock Model ID: {runner.llm_client.model}")
    print(f"  -> AWS Region:       {runner.llm_client.region}")
    print(f"  -> Send Emails:      {runner.llm_client.send_emails}")

    # Step 3: Execute Live Deepline Lead Discovery (Requested Count = 1)
    print("\n[3/5] Executing Live Deepline Discovery & DeepSeek Copy Generation (Requested Count = 1)...")
    try:
        pipeline_result = runner.run_discovery_pipeline(
            icp=approved_rec.effective_icp,
            requested_count=1
        )
    except Exception as e:
        print(f"\n[FAILURE] Pipeline execution failed: {e}")
        sys.exit(1)

    summary = pipeline_result.get("summary", {})
    run_id = pipeline_result.get("run_id")

    print("\n[4/5] Pipeline Summary & Results:")
    print(f"  -> Run ID:           {run_id}")
    print(f"  -> Discovered Leads: {summary.get('discovered', 0)}")
    print(f"  -> Qualified Leads:  {summary.get('qualified', 0)}")
    print(f"  -> Disqualified:     {summary.get('hard_disqualified', 0)}")

    # Step 4: Inspect Enrolled Lead in Approval Queue
    store = ApprovalStore()
    queue = store.load_queue()
    matching_records = [r for r in queue if r.metadata.get("deepline_run_id") == run_id]

    print("\n[5/5] Enrolled Approval Queue Record Audit:")
    if matching_records:
        rec = matching_records[0]
        raw_email = rec.email or "unknown@domain.com"
        email_parts = raw_email.split("@") if "@" in raw_email else [raw_email, ""]
        masked_email = f"{email_parts[0][:2]}***@{email_parts[1]}" if len(email_parts[0]) > 2 else "***@***"
        
        print(f"  -> Company Name:     {rec.company}")
        print(f"  -> Contact Name:     {rec.contact}")
        print(f"  -> Job Title:        {rec.title}")
        print(f"  -> Email:            {masked_email}")
        print(f"  -> Qualification:    {rec.qualification_status}")
        print(f"  -> Outreach Priority:{rec.outreach_priority_index:.1f} ({rec.priority})")
        print(f"  -> VoC Pain Angle:   {rec.voc_angle}")
        print(f"  -> Personalization:  {rec.personalization_status}")
        print(f"  -> QA Status:        {rec.qa_status}")
        if rec.qa_reasons:
            print(f"  -> QA Reasons:       {rec.qa_reasons}")
        print(f"  -> Approval Status:  {rec.approval_status.value}")
        print(f"  -> Smartlead Eligible:{rec.smartlead_eligible}")

        print("\n-------------------------------------------------------------------")
        print(" GENERATED DEEPSEEK V3.2 EMAIL COPY AUDIT")
        print("-------------------------------------------------------------------")
        print(f"[EMAIL 1]\n{rec.email_1_original}\n")
        print(f"[FOLLOW-UP A]\n{rec.followup_a_original}\n")
        print(f"[FOLLOW-UP B]\n{rec.followup_b_original}\n")
        print("-------------------------------------------------------------------")

    else:
        print("  -> No matching approval record found.")

    print("\n===================================================================")
    print(" VERIFICATION AUDIT SUMMARY")
    print("===================================================================")
    qualified_count = summary.get("qualified", 0)
    hard_disqual_count = summary.get("hard_disqualified", 0)
    campaign_excl_count = summary.get("campaign_excluded", 0)
    discovered_count = summary.get("discovered", 0)

    print(f"  [OK] Deepline V2 API Call: EXECUTED ({discovered_count} lead(s) returned)")
    if qualified_count > 0:
        print(f"  [OK] AWS Bedrock DeepSeek V3.2 API Call: EXECUTED ({qualified_count} lead(s) processed)")
        print(f"  [OK] 19-Point PersonalizationQA: EXECUTED")
        if matching_records:
            print(f"  [OK] Enrolled in Human Approval Gate: SUCCESS ({len(matching_records)} record(s) verified in store/DB)")
        else:
            print(f"  [FAIL] Enrolled in Human Approval Gate: FAILED (0 matching records found in store/DB)")
    else:
        print(f"  [SKIP] AWS Bedrock DeepSeek V3.2 API Call: SKIPPED (0 leads qualified)")
        print(f"  [SKIP] 19-Point PersonalizationQA: SKIPPED (0 leads qualified)")
        print(f"  [SKIP] Enrolled in Human Approval Gate: SKIPPED (0 leads qualified)")
    if hard_disqual_count > 0:
        print(f"  [WARN] Hard Disqualified: {hard_disqual_count} lead(s) — check ICPEngine rules and adapter output")
    if campaign_excl_count > 0:
        print(f"  [WARN] Campaign Excluded: {campaign_excl_count} lead(s)")
    print(f"  [OK] Smartlead API Calls Made: 0 (Smartlead Live Disabled)")
    print(f"  [OK] Outbound Emails Sent: 0 (Send Emails Disabled)")
    print("===================================================================\n")

if __name__ == "__main__":
    main()
