import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from src.database.connection import get_db_session
from src.database.models import Lead, Campaign, ICP

client = TestClient(app)

print("=" * 70)
print(" AEDRIX DEMO MODE SUPABASE POSTGRESQL END-TO-END VERIFICATION")
print("=" * 70)

# 1. Database Health Endpoint
db_health = client.get('/api/system/database-health').json()
print("1. /api/system/database-health:")
print(f"   Database:         {db_health.get('database')}")
print(f"   Connected:        {db_health.get('connected')}")
print(f"   Latency:          {db_health.get('latency_ms')} ms")
print(f"   Status:           {db_health.get('status')}")

# 2. Mode Endpoint
mode_resp = client.get('/api/system/mode').json()
print("\n2. /api/system/mode:")
print(f"   Mode:             {mode_resp.get('mode')}")
print(f"   Demo Mode:        {mode_resp.get('demo_mode')}")
print(f"   Database:         {mode_resp.get('database')}")
print(f"   DB Connected:     {mode_resp.get('database_connected')}")
print(f"   Real Emails:      {mode_resp.get('real_emails_enabled')} (Sent: {mode_resp.get('real_emails_sent')})")
print(f"   Safety Summary:   {mode_resp.get('safety_summary')}")

# 3. Readiness Endpoint
readiness_resp = client.get('/api/system/readiness').json()
print("\n3. /api/system/readiness:")
print(f"   Application:      {readiness_resp.get('application')}")
print(f"   Database:         {readiness_resp.get('database')}")
print(f"   Frontend:         {readiness_resp.get('frontend')}")
print(f"   Claude:           {readiness_resp.get('claude')}")
print(f"   Deepline:         {readiness_resp.get('deepline')}")
print(f"   Smartlead:        {readiness_resp.get('smartlead')}")
print(f"   Email:            {readiness_resp.get('email')}")

# 4. Dashboard Stats Endpoint (Reads from Supabase)
stats_resp = client.get('/api/dashboard/stats').json()
print("\n4. /api/dashboard/stats (Live Supabase Query):")
print(f"   Total Leads:      {stats_resp.get('total_leads')}")
print(f"   Qualified Leads:  {stats_resp.get('qualified_leads')}")
print(f"   P1 Leads:         {stats_resp.get('p1_leads')}")
print(f"   Pending Review:   {stats_resp.get('pending_approvals')}")
print(f"   Approved Leads:   {stats_resp.get('approved_leads')}")
print(f"   Real Emails Sent: {stats_resp.get('safety', {}).get('real_emails_sent')}")

# 5. Leads List Endpoint
leads_resp = client.get('/api/leads?page_size=5').json()
print("\n5. /api/leads (Pagination & Search):")
print(f"   Total:            {leads_resp.get('total')}")
print(f"   Page Items:       {len(leads_resp.get('items', []))}")
if leads_resp.get('items'):
    first = leads_resp['items'][0]
    print(f"   Sample Lead:      {first['company']} - {first['contact']} ({first['priority']} / {first['qualification_status']})")

# 6. Execute Isolated Full Demo Run
demo_run_resp = client.post('/api/demo/run').json()
print("\n6. /api/demo/run (Simulated Workflow Execution):")
print(f"   Success:          {demo_run_resp.get('ok')}")
print(f"   Message:          {demo_run_resp.get('message')}")
print(f"   Real Emails:      {demo_run_resp.get('summary', {}).get('real_emails_sent')}")
print(f"   Paid Credits:     {demo_run_resp.get('summary', {}).get('stats', {}).get('paid_api_credits_consumed')}")

# 7. Check Data Isolation: Demo Reset vs Production Records
with get_db_session() as session:
    before_prod_leads = session.query(Lead).filter(Lead.environment == 'PRODUCTION').count()
    before_prod_camps = session.query(Campaign).filter(Campaign.environment == 'PRODUCTION').count()
    before_demo_leads = session.query(Lead).filter(Lead.environment == 'DEMO').count()

reset_resp = client.post('/api/demo/reset').json()
print("\n7. /api/demo/reset (Strict Isolation Check):")
print(f"   Reset Message:    {reset_resp.get('message')}")
print(f"   Deleted Records:  {reset_resp.get('deleted_demo_records')}")

with get_db_session() as session:
    after_prod_leads = session.query(Lead).filter(Lead.environment == 'PRODUCTION').count()
    after_prod_camps = session.query(Campaign).filter(Campaign.environment == 'PRODUCTION').count()
    after_demo_leads = session.query(Lead).filter(Lead.environment == 'DEMO').count()

print(f"   PROD Leads:       {before_prod_leads} -> {after_prod_leads} (STRICTLY PRESERVED: {before_prod_leads == after_prod_leads})")
print(f"   PROD Campaigns:   {before_prod_camps} -> {after_prod_camps} (STRICTLY PRESERVED: {before_prod_camps == after_prod_camps})")
print(f"   DEMO Leads:       {before_demo_leads} -> {after_demo_leads} (CLEANLY RE-SEEDED)")
print("=" * 70)
