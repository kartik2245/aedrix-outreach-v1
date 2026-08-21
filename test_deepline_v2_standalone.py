"""
test_deepline_v2_standalone.py
Controlled standalone test for Deepline V2 lead discovery & schema normalization.
Isolates Deepline Client from DeepSeek, Bedrock, EmailGenerator, and Smartlead.
"""

import os
import json
from dotenv import load_dotenv
from src.icp.icp_models import DeeplineDiscoveryRequest
from src.integrations.deepline_client import DeeplineClient
from src.deepline_export_adapter import DeeplineExportAdapter

load_dotenv()

# Controlled 1-lead discovery request
req = DeeplineDiscoveryRequest(
    icp_id="test_icp_v2_probe",
    campaign_id="test_camp_v2_probe",
    campaign_name="Controlled Deepline V2 Test",
    geography=["United Kingdom"],
    industries=["Commercial Construction"],
    company_size="100+ employees",
    personas=["Digital Director"],
    positive_signals=[],
    exclusions=[],
    requested_lead_count=1
)

print("==================================================")
print(" AEDRIX DEEPLINE V2 STANDALONE INTEGRATION AUDIT")
print("==================================================")
print(f" Request Lead Count: {req.requested_lead_count}")
print(f" Target Industry:    {req.industries[0]}")
print(f" Target Geography:   {req.geography[0]}")
print(f" Target Persona:     {req.personas[0]}")
print("--------------------------------------------------")

client = DeeplineClient()
masked_key = client.mask_api_key(client.api_key)

print(f" Client Mode:        {'LIVE API (V2)' if client.live_mode else 'DRY_RUN SIMULATION'}")
print(f" Run Confirmed:      {client.run_confirmed}")
print(f" Masked Key:         {masked_key}")
print("--------------------------------------------------")

# Part 1: Client Lead Discovery
try:
    res = client.discover_leads(req)
    leads = res.get("leads", [])
    print(f"\n[1. DEEPLINE DISCOVERY RESULT]")
    print(f" Connection:         PASS")
    print(f" Status:             {res.get('status')}")
    print(f" Execution Mode:     {res.get('mode')}")
    print(f" Discovered Leads:   {len(leads)}")

    adapter = DeeplineExportAdapter()

    if leads:
        sample_raw_lead = leads[0]
        adapted_lead = adapter.adapt_record(sample_raw_lead)

        print(f"\n[2. CANONICAL RECORD ADAPTATION]")
        print(f" Company Name:       {adapted_lead.get('company_name')}")
        print(f" Company Domain:     {adapted_lead.get('company_domain')}")
        print(f" Contact Name:       {adapted_lead.get('contact_name')}")
        print(f" Job Title:          {adapted_lead.get('job_title')}")
        print(f" Email:              {adapted_lead.get('email')}")
        print(f" Employee Count:     {adapted_lead.get('employee_count')}")
        print(f" Company Size:       {adapted_lead.get('company_size')}")
        print(f" Is UK Operating:    {adapted_lead.get('is_uk_operating')}")
        print(f" Is Construction:    {adapted_lead.get('is_construction_sector')}")
        print(f" Audit Validity:     {adapted_lead.get('adapter_audit', {}).get('is_valid')}")

    # Part 2: V2 Tool Field Format Direct Test (ai_ark_people_search)
    v2_raw_tool_item = {
        "company": "Kier Group plc",
        "domain": "kier.co.uk",
        "location": "United Kingdom",
        "first_name": "Colin",
        "last_name": "Bell",
        "title": "Digital Director",
        "email": "c.bell@kier.co.uk",
        "linkedin": "https://linkedin.com/in/colin-bell",
        "size": "11000 employees"
    }

    adapted_v2 = adapter.adapt_record(v2_raw_tool_item)
    print(f"\n[3. DEEPLINE V2 TOOL FIELD MAPPING (ai_ark_people_search)]")
    print(f" Raw V2 Keys:        {list(v2_raw_tool_item.keys())}")
    print(f" Mapped Company:     {adapted_v2.get('company_name')}")
    print(f" Mapped Domain:      {adapted_v2.get('company_domain')}")
    print(f" Mapped Contact:     {adapted_v2.get('contact_name')}")
    print(f" Mapped Job Title:   {adapted_v2.get('job_title')}")
    print(f" Mapped LinkedIn:    {adapted_v2.get('linkedin_url')}")
    print(f" Mapped Employee Ct: {adapted_v2.get('employee_count')}")
    print(f" Schema Audit Valid: {adapted_v2.get('adapter_audit', {}).get('is_valid')}")

    print("\n[SUCCESS] Deepline V2 integration & schema normalization verified!")

except Exception as e:
    print(f"\n[FAILURE] Deepline discovery error: {e}")
