"""
poc_runner.py
Master Execution Script for the Aedrix AI Outreach Pipeline & Research Ingestion POC (Python 3.12).
Zero real email sending; zero credit expenditure; zero paid API calls.
"""

import json
import os
import sys

# Ensure src package is in Python path when executed directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.research_pipeline import ResearchPipeline
from src.outreach_engine import OutreachEngine
from src.models import DisqualificationStatus, OutreachState


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    deepline_export_path = os.path.join(base_dir, "data", "deepline_export_sample.json")
    research_leads_path = os.path.join(base_dir, "data", "research_leads.json")
    final_intel_path = os.path.join(base_dir, "data", "final_lead_intelligence.json")
    events_path = os.path.join(base_dir, "data", "simulated_events.json")

    research_pipeline = ResearchPipeline()
    outreach_engine = OutreachEngine()

    print("===================================================================")
    print(" AEDRIX AI COLD OUTREACH PIPELINE - TECHNICAL POC DRY-RUN (PHASE 5 PYTHON)")
    print(" Architecture: Deepline Export -> Normalizer -> Validator -> Lead Intel -> Outreach Engine -> Smartlead Simulator")
    print(" Mode: ZERO-RISK SIMULATION (0 Emails Sent / 0 Credits Consumed)")
    print("===================================================================\n")

    # 1. DEEPLINE EXPORT ADAPTATION & RESEARCH INGESTION
    print("--- PHASE 1: RESEARCH INGESTION & EVIDENCED LEAD INTELLIGENCE ---\n")

    processed_leads = research_pipeline.run_and_save(deepline_export_path, research_leads_path, final_intel_path)
    
    with open(events_path, "r", encoding="utf-8") as f:
        simulated_events = json.load(f)

    for index, lead_intel in enumerate(processed_leads):
        print(f"[Lead {index + 1}/5 Pipeline Ingestion] Processing {lead_intel.company_name}...")
        print(f"  -> Disqualification Status: {lead_intel.disqualification_status.value}")
        print(f"  -> Opportunity Score:       {lead_intel.opportunity_score} / 100 ({lead_intel.opportunity_tier})")
        print(f"  -> Accessibility Score:     {lead_intel.accessibility_score} / 100 ({lead_intel.accessibility_tier.value})")
        print(f"  -> Outreach Priority Index: {lead_intel.outreach_priority_index} [{lead_intel.priority_level.value}]")
        print(f"  -> Email Status:            {lead_intel.email_status.value}")
        print(f"  -> Personalization Status:  {lead_intel.personalization_note_status.value}")
        print(f'  -> Personalization Note:    "{lead_intel.personalization_note}"')
        print(f"  -> Persona Rationale:       {lead_intel.persona_selection_rationale}")

        if lead_intel.disqualification_status == DisqualificationStatus.QUALIFIED:
            record = outreach_engine.enroll_lead(lead_intel)
            print(f'  -> Email 1 Subject: "{record.email1.subject}"')
            print(f"  -> Smartlead Payload Prepared: POST /api/v1/campaigns/123456/leads")
        else:
            reason = lead_intel.disqualification_reason or "Lead excluded or disqualified"
            print(f"  -> 🛑 SKIPPED ENROLLMENT: {reason}")
        print("")

    # 2. SIMULATED EVENT PROCESSING & STATE MACHINE TRANSITIONS
    print("--- PHASE 2: SIMULATED WEBHOOK EVENTS & DYNAMIC BRANCHING ---\n")

    for evt in simulated_events:
        evt_type = evt.get("event_type")
        lead_email = evt.get("lead_email")
        print(f"[Webhook Event Received] Type: {evt_type} | Lead: {lead_email}")

        record = outreach_engine.pipelines.get(lead_email)
        if not record:
            print(f"  -> Lead email {lead_email} not active in pipeline.")
            print("")
            continue

        if evt_type == "EMAIL_OPENED":
            print("  -> Open Event Verified. Scheduling 24h delay (1 day) before Branch A.")
            followup_a = outreach_engine.simulate_opened_event(lead_email, evt.get("timestamp"))
            print(f'  -> Follow-up A Generated: "{followup_a.subject}"')

        elif evt_type == "EMAIL_REPLIED":
            reply_text = evt.get("details", {}).get("reply_text", "")
            print(f'  -> Reply Received: "{reply_text}"')
            classification = outreach_engine.simulate_reply_event(lead_email, reply_text)
            print(f"  -> Claude Intent Classification: {classification.classification} (Confidence: {classification.confidence})")
            print(f"  -> Rationale: {classification.reasoning}")

            if classification.classification == "POSITIVE":
                print("  -> 🚨 TRIGGERED SLACK ALERT: Sales Handoff required within 1 hour!")

        elif evt_type == "EMAIL_BOUNCED":
            bounce_type = evt.get("details", {}).get("bounce_type", "HARD_BOUNCE")
            outreach_engine.simulate_bounce_event(lead_email, bounce_type)
            print("  -> Hard Bounce Processed. Sequence PAUSED in Smartlead.")

        elif evt_type == "EMAIL_UNSUBSCRIBED":
            outreach_engine.simulate_unsubscribe_event(lead_email)
            print("  -> Unsubscribe Processed. Contact Suppressed.")

        print("")

    # 3. UNOPENED BRANCH B TIMEOUT SIMULATION
    print("--- PHASE 3: UNOPENED TIMEOUT SIMULATION (BRANCH B) ---\n")

    lead4_record = outreach_engine.pipelines.get("a.spragg@laingorourke.com")
    if lead4_record and lead4_record.state_machine.get_current_state() == OutreachState.EMAIL_1_SENT:
        print(f"[No-Open Timeout] Lead: {lead4_record.lead.company_name} ({lead4_record.lead.contact_name})")
        followup_b = outreach_engine.simulate_unopened_timeout("a.spragg@laingorourke.com")
        print(f'  -> Follow-up B Generated (Pivoted Angle): "{followup_b.subject}"')
        print("")

    # 4. PIPELINE SUMMARY REPORT
    print("===================================================================")
    print(" FINAL RESEARCH INGESTION & OUTREACH PIPELINE POC SUMMARY")
    print("===================================================================\n")

    summary_data = []
    for lead in processed_leads:
        active_record = outreach_engine.pipelines.get(lead.email)
        final_state = active_record.state_machine.get_current_state().value if active_record else "NOT_ENROLLED"
        summary_data.append({
            "Company": lead.company_name,
            "Contact": lead.contact_name,
            "Opp Score": lead.opportunity_score,
            "Acc Score": lead.accessibility_score,
            "Outreach Index": lead.outreach_priority_index,
            "Priority": lead.priority_level.value,
            "Personalization": lead.personalization_note_status.value,
            "Status": lead.disqualification_status.value,
            "Final State": final_state
        })

    # Print formatted table
    print(f"{'Company':<28} | {'Contact':<16} | {'Opp':<5} | {'Acc':<5} | {'Index':<6} | {'Prio':<5} | {'Personalization':<18} | {'Status':<10} | {'Final State':<22}")
    print("-" * 135)
    for row in summary_data:
        print(f"{row['Company']:<28} | {row['Contact']:<16} | {row['Opp Score']:<5.0f} | {row['Acc Score']:<5.0f} | {row['Outreach Index']:<6.1f} | {row['Priority']:<5} | {row['Personalization']:<18} | {row['Status']:<10} | {row['Final State']:<22}")

    stats = outreach_engine.get_stats()

    print("\n===================================================")
    print(" AEDRIX AI OUTREACH PIPELINE - PHASE 5")
    print("===================================================")
    print(" MODE: ZERO-RISK DRY RUN\n")
    print(f" Deepline Credits:              0")
    print(f" Apollo Credits:                0")
    print(f" Claude API Calls:              0")
    print(f" Smartlead API Calls:           0")
    print(f" Real Emails Sent:              0")
    print(f" Real Mailboxes Connected:      0\n")
    print(f" Qualified Leads:               {stats['qualified_leads']}")
    print(f" Email 1 Generated:             {stats['email_1_generated']}")
    print(f" Follow-up A Generated:         {stats['followup_a_generated']}")
    print(f" Follow-up B Generated:         {stats['followup_b_generated']}")
    print(f" Positive Replies Simulated:    {stats['positive_replies']}")
    print(f" Human Sales Handoffs Simulated: {stats['human_handoffs']}")
    print(f" Bounces Handled:               {stats['bounces_handled']}")
    print(f" Unsubscribes Handled:          {stats['unsubscribes_handled']}")
    print("===================================================\n")
    print("Status: Production architecture implemented locally; external integrations remain simulated.\n")


if __name__ == "__main__":
    main()
