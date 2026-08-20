"""
demo_data.py
Realistic demo dataset representing UK B2B construction contractors.

Contains diverse:
- Company profiles (Balfour Beatty, Mace, Morgan Sindall, Kier, Willmott Dixon, Bowmer & Kirkland, Wates, Multiplex, plus disqualified test cases)
- Priorities: P1, P2, P3
- Qualification states: QUALIFIED, HARD_DISQUALIFIED, CAMPAIGN_EXCLUDED
- Personalization states: SIGNAL_VERIFIED, NO_STRONG_SIGNAL
- Approval states: PENDING_REVIEW, APPROVED, EDITED, REJECTED, BLOCKED
- Verified evidence, VoC angles, email drafts, QA statuses
"""

from typing import List, Dict, Any

DEMO_CAMPAIGN_ID = "demo_uk_tier1_contractors"
DEMO_CAMPAIGN_NAME = "Demo: UK Main Contractors — Modular Construction SaaS"
DEMO_CAMPAIGN_OBJECTIVE = "Demonstrate AI outreach targeting tier-1 and tier-2 UK main commercial building contractors (£10M+ revenue, 50+ staff) facing document versioning and site coordination challenges."
DEMO_ICP_ID = "demo_icp_uk_contractors_v1"

DEMO_ICP_CONFIG: Dict[str, Any] = {
    "id": DEMO_ICP_ID,
    "campaign_id": DEMO_CAMPAIGN_ID,
    "name": "UK Commercial Main Contractors (Tier 1 & 2)",
    "version": "1.0.0",
    "status": "APPROVED",
    "campaign_description": DEMO_CAMPAIGN_OBJECTIVE,
    "geography": {
        "primary_country": "United Kingdom",
        "country_codes": ["UK", "GB", "GBR"],
        "allowed_country_keywords": ["UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "LONDON", "BIRMINGHAM", "MANCHESTER", "LEEDS"],
        "require_target_country_operating": True,
    },
    "industries": ["Construction", "Commercial Building", "Infrastructure", "Civil Engineering", "Main Contracting"],
    "allowed_industry_keywords": ["construction", "contractor", "civil", "infrastructure", "building"],
    "disallowed_industry_keywords": ["residential plumbing", "sole trader", "recruitment agency"],
    "company_size": "50+ employees or £10M+ revenue",
    "minimum_employees": 50,
    "maximum_employees": None,
    "minimum_revenue": 10.0,
    "maximum_revenue": None,
    "target_personas": ["Head of Pre-Construction", "Commercial Director", "Operations Director", "Digital Construction Lead", "Head of Procurement"],
    "persona_title_keywords": ["pre-construction", "commercial director", "operations director", "digital construction", "procurement"],
    "positive_signals": [
        "Won major public or commercial building framework in last 12 months",
        "Expanding digital construction / BIM department",
        "Publicly stated net-zero or modular construction initiatives",
        "Managing multiple concurrent live site projects (£5M+ value)"
    ],
    "negative_signals": [
        "Sole trader or residential remodeling contractor",
        "Subcontractor with fewer than 10 employees",
        "Bankruptcy or active liquidation notices"
    ],
    "hard_disqualifiers": [
        {"code": "NON_UK_OPERATING", "description": "Operating headquarters outside the United Kingdom.", "field": "geography"},
        {"code": "NON_TARGET_INDUSTRY", "description": "Not a commercial main or civil building contractor.", "field": "industry"},
        {"code": "UNDER_MINIMUM_SCALE", "description": "Company under minimum scale threshold (under 50 staff and under £10M revenue).", "field": "company_size"}
    ],
    "campaign_exclusions": [
        {"code": "ACTIVE_CRM_DEAL", "description": "Account currently has an active enterprise CRM negotiation or is an existing customer.", "fields": ["crm_status"]},
        {"code": "INVALID_EMAIL_STATUS", "description": "Prospect email address bounced or failed pattern verification.", "fields": ["email_status"]}
    ],
    "required_conditions": ["UK operating entity", "50+ staff or £10M+ revenue"],
    "preferred_conditions": ["Active Tier 1 or Tier 2 framework appointment", "BIM/Digital construction lead in place"],
    "voc_context": "Pre-construction document control and audit-ready site logs: Main contractors struggle with site teams building against outdated drawings and submittal delays.",
    "reasoning": "Standard tier-1 UK main contractors have high document volumes and multiple subcontractors, making them ideal high-value SaaS adopters.",
}


DEMO_LEADS_DATA: List[Dict[str, Any]] = [
    {
        "lead_id": "demo_lead_001_balfour",
        "company_name": "Balfour Beatty plc",
        "company_domain": "balfourbeatty.com",
        "contact_name": "John Foster",
        "job_title": "Head of Pre-Construction",
        "email": "j.foster@balfourbeatty.com",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/john-foster-balfour",
        "company_size": "26,000 employees / £8.9B revenue",
        "industry": "Infrastructure & Main Contracting",
        "opportunity_score": 94.0,
        "accessibility_score": 90.0,
        "outreach_priority_index": 92.4,
        "priority_level": "P1",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Won £1.2B Lower Thames Crossing package and actively standardizing digital pre-construction submittals.",
        "voc_angle": "Pre-construction document control",
        "evidence_items": [
            {"claim_type": "signal", "evidence_level": "VERIFIED", "source_reference": "Construction Enquirer Oct 2024", "verified": True},
            {"claim_type": "company_size", "evidence_level": "VERIFIED", "source_reference": "Companies House 2024 Annual Return", "verified": True},
            {"claim_type": "pain_point", "evidence_level": "INFERRED", "source_reference": "Industry Benchmark", "verified": True}
        ],
                "email_draft": {
            "ai_original_email_1": "Subject: superseded drawings on site?\n\nHi John,\n\nmost document controllers at UK contractors have the same worry, that someone on site is working from a superseded drawing and nobody knows yet. Aedrix keeps the drawing and document register, revisions and distribution in one place, so the current revision is the only one anyone can open.\n\nWorth 15 minutes to see how that would run at Balfour Beatty plc?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: superseded drawings on site?\n\nQuick addition to my last note. When a revision is issued in Aedrix, everyone holding the old copy is notified through distribution groups, and every issue is logged against the document. That is usually the part that ends the chasing. Happy to show the register with a project loaded rather than a demo file. 15 minutes this week?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: who approved that drawing?\n\nHi John,\n\ndifferent question. When a client, an auditor or an adjudicator asks who approved a document and when, at most contractors the answer lives in email trails and someone loses a day to it. Aedrix logs approvals and issues against each document, so the audit trail is a lookup. If that is a sore point at Balfour Beatty plc, happy to show it. 15 minutes?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "BLOCKED",
            "reviewer": "SYSTEM_SAFETY_GATE",
            "reviewed_at": "2026-08-17T09:00:00Z",
            "smartlead_eligible": False,
            "blocked_reason": "Hard Disqualified: Subcontractor under minimum size threshold (£10M / 50 staff).",
            "flag_no_strong_signal": True
        }
    },
    {
        "lead_id": "demo_lead_010_acmedemo",
        "company_name": "Acme Demolition & Civil Works",
        "company_domain": "acmedemo.co.uk",
        "contact_name": "Thomas White",
        "job_title": "Managing Director",
        "email": "t.white@acmedemo.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/thomas-white-acmedemo",
        "company_size": "80 employees / £25M revenue",
        "industry": "Demolition & Groundworks",
        "opportunity_score": 30.0,
        "accessibility_score": 18.0,
        "outreach_priority_index": 25.0,
        "priority_level": "P3",
        "qualification_status": "CAMPAIGN_EXCLUDED",
        "disqualification_reason": "Active CRM Enterprise Deal in late-stage contract negotiation.",
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Expanding demolition fleet across Birmingham.",
        "voc_angle": "Equipment tracking",
        "evidence_items": [],
        "email_draft": {
            "ai_original_email_1": "[SKIPPED — CAMPAIGN EXCLUDED]",
            "ai_original_followup_a": "[SKIPPED — CAMPAIGN EXCLUDED]",
            "ai_original_followup_b": "[SKIPPED — CAMPAIGN EXCLUDED]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "FAIL",
            "qa_reasons": ["Lead is CAMPAIGN_EXCLUDED (Active CRM Deal)."]
        },
        "approval": {
            "approval_status": "BLOCKED",
            "reviewer": "SYSTEM_SAFETY_GATE",
            "reviewed_at": "2026-08-17T09:00:00Z",
            "smartlead_eligible": False,
            "blocked_reason": "Campaign Excluded: Active CRM Enterprise Deal in late-stage contract negotiation.",
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_002_mace",
        "company_name": "Mace Group",
        "company_domain": "macegroup.com",
        "contact_name": "David Smith",
        "job_title": "Director",
        "email": "david.smith@macegroup.com",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/davidsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P2",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: mobilisation paperwork\n\nHi David,\n\nmobilisation is usually where the paperwork bites, subcontractor onboarding, tender packages turning into live documents, drawings landing on site in the right revision. Most contractors run that across a shared drive, a spreadsheet and email. Aedrix runs it from one place, tender through to site. Worth 15 minutes to see how it would fit Mace Group?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: mobilisation paperwork\n\nOne more thought. The teams that get mobilisation right usually pin down document distribution first, because everything else hangs off it. In Aedrix, site teams open current drawings on a phone or tablet, so the printed set in the cabin stops being the reference. Happy to show it against your setup, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: rework from a wrong revision\n\nHi David,\n\nmost rework stories start the same way, someone built from a superseded drawing. That is real money and programme, and it is avoidable. Aedrix makes the current revision the only one site can open, with a log of who was issued what. If that risk is on your list at Mace Group, worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_003_morgansindall",
        "company_name": "Morgan Sindall",
        "company_domain": "morgansindall.com",
        "contact_name": "Sarah Smith",
        "job_title": "Director",
        "email": "sarah.smith@morgansindall.com",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/sarahsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P2",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: variations never claimed\n\nHi Sarah,\n\nmost margin leaks the same way, variations agreed on site, never recorded, missing from the application for payment. Aedrix logs variations against cost tracking as they happen, so valuations carry them instead of relying on memory. Worth 15 minutes to see it against how Morgan Sindall runs CVRs now?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: variations never claimed\n\nOne more on this. Because variations, procurements and invoices sit against the same project in Aedrix, the CVR stops being a month-end reconstruction. You see cost against value while there is still time to act on it. Happy to show it with a project loaded, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: when it goes to adjudication\n\nHi Sarah,\n\ndifferent angle. If a final account ever goes to adjudication, the side with the cleaner record usually has the easier time. Aedrix keeps valuations, applications, variations and the documents behind them logged and dated. Cover for the day you hope never comes. Worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_004_kier",
        "company_name": "Kier Group",
        "company_domain": "kier.co.uk",
        "contact_name": "Michael Smith",
        "job_title": "Director",
        "email": "michael.smith@kier.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/michaelsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P1",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: a CDE clients will accept\n\nHi Michael,\n\nmore clients now expect a common data environment, and running one from folders and email does not survive an audit. Aedrix holds drawings, BIM documents and revisions with controlled distribution, which covers the working core of that requirement. Worth 15 minutes to see where it fits what Kier Group already has?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: a CDE clients will accept\n\nFollowing on. The part teams feel daily is revision flow, design changes reaching site as controlled issues rather than email attachments, with interactive drawings viewable on a phone. If you are midway through standing up a CDE, I can show where Aedrix fits. 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: the golden thread question\n\nHi Michael,\n\ndifferent angle. The Building Safety Act makes the golden thread a duty on in-scope buildings, a digital, current record kept through design and construction. Assembling that from shared drives is the hard way. Aedrix keeps documents, revisions and approvals in one place, most of the thread by default. Worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_005_willmott",
        "company_name": "Willmott Dixon",
        "company_domain": "willmottdixon.co.uk",
        "contact_name": "Emma Smith",
        "job_title": "Director",
        "email": "emma.smith@willmottdixon.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/emmasmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P2",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: chasing RAMS before Monday?\n\nHi Emma,\n\nevery main contractor wants RAMS, inductions and tickets evidenced before anyone sets foot on site, and most specialist contractors chase that through spreadsheets and inbox threads. Aedrix keeps RAMS, inductions and the training matrix in one place, with expiry dates visible. Worth 15 minutes to see how it would work at Willmott Dixon?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: chasing RAMS before Monday?\n\nAdding one thing. The expiry view is what usually lands, which CSCS cards, tickets and certs run out in the next 60 days, seen before a main contractor's audit finds out first. All crews on one screen. Happy to show it, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: timesheets without the Friday chase\n\nHi Emma,\n\ndifferent angle. If Friday still means chasing timesheets from three sites, Aedrix captures timesheets and holidays against each project, so payroll and job costing stop being a reconstruction exercise. Fifteen minutes to see it against how Willmott Dixon runs now?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_006_bandk",
        "company_name": "Bowmer & Kirkland",
        "company_domain": "bandk.co.uk",
        "contact_name": "James Smith",
        "job_title": "Director",
        "email": "james.smith@bandk.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/jamessmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P1",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: superseded drawings on site?\n\nHi James,\n\nmost document controllers at UK contractors have the same worry, that someone on site is working from a superseded drawing and nobody knows yet. Aedrix keeps the drawing and document register, revisions and distribution in one place, so the current revision is the only one anyone can open.\n\nWorth 15 minutes to see how that would run at Bowmer & Kirkland?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: superseded drawings on site?\n\nQuick addition to my last note. When a revision is issued in Aedrix, everyone holding the old copy is notified through distribution groups, and every issue is logged against the document. That is usually the part that ends the chasing. Happy to show the register with a project loaded rather than a demo file. 15 minutes this week?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: who approved that drawing?\n\nHi James,\n\ndifferent question. When a client, an auditor or an adjudicator asks who approved a document and when, at most contractors the answer lives in email trails and someone loses a day to it. Aedrix logs approvals and issues against each document, so the audit trail is a lookup. If that is a sore point at Bowmer & Kirkland, happy to show it. 15 minutes?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_007_wates",
        "company_name": "Wates Group",
        "company_domain": "wates.co.uk",
        "contact_name": "Robert Smith",
        "job_title": "Director",
        "email": "robert.smith@wates.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/robertsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P2",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: mobilisation paperwork\n\nHi Robert,\n\nmobilisation is usually where the paperwork bites, subcontractor onboarding, tender packages turning into live documents, drawings landing on site in the right revision. Most contractors run that across a shared drive, a spreadsheet and email. Aedrix runs it from one place, tender through to site. Worth 15 minutes to see how it would fit Wates Group?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: mobilisation paperwork\n\nOne more thought. The teams that get mobilisation right usually pin down document distribution first, because everything else hangs off it. In Aedrix, site teams open current drawings on a phone or tablet, so the printed set in the cabin stops being the reference. Happy to show it against your setup, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: rework from a wrong revision\n\nHi Robert,\n\nmost rework stories start the same way, someone built from a superseded drawing. That is real money and programme, and it is avoidable. Aedrix makes the current revision the only one site can open, with a log of who was issued what. If that risk is on your list at Wates Group, worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_008_multiplex",
        "company_name": "Multiplex",
        "company_domain": "multiplex.global",
        "contact_name": "William Smith",
        "job_title": "Director",
        "email": "william.smith@multiplex.global",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/williamsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P1",
        "qualification_status": "QUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: service records when clients ask\n\nHi William,\n\nmaintenance contracts live and die on evidence, inspections done, service requests closed, records ready when the client or an auditor asks. Aedrix runs recurring tasks, service requests and inspections with digital records against each contract. Worth 15 minutes to see it against how Multiplex works now?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: service records when clients ask\n\nOne addition. Recurring tasks are the quiet win, planned inspections scheduled once, then evidenced as crews complete them, so nothing depends on someone remembering. Happy to show a live view, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: renewal without the scramble\n\nHi William,\n\ndifferent angle. When a contract comes up for renewal, the provider with clean records has the easier conversation. Aedrix keeps inspection history, service requests and completion evidence in one place per client. If renewals at Multiplex still mean assembling folders, worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    },
    {
        "lead_id": "demo_lead_009_skanska",
        "company_name": "Skanska UK",
        "company_domain": "skanska.co.uk",
        "contact_name": "Richard Smith",
        "job_title": "Director",
        "email": "richard.smith@skanska.co.uk",
        "email_status": "PATTERN_CONFIRMED",
        "linkedin_url": "https://linkedin.com/in/richardsmith",
        "company_size": "5000 employees",
        "industry": "Construction",
        "opportunity_score": 85.0,
        "accessibility_score": 80.0,
        "outreach_priority_index": 82.5,
        "priority_level": "P3",
        "qualification_status": "HARD_DISQUALIFIED",
        "disqualification_reason": None,
        "personalization_status": "SIGNAL_VERIFIED",
        "personalization_note": "Recent project win mentioned in news.",
        "voc_angle": "Document control",
        "evidence_items": [
            {
                "claim_type": "signal",
                "evidence_level": "VERIFIED",
                "source_reference": "News",
                "verified": True
            }
        ],
        "email_draft": {
            "ai_original_email_1": "Subject: variations never claimed\n\nHi Richard,\n\nmost margin leaks the same way, variations agreed on site, never recorded, missing from the application for payment. Aedrix logs variations against cost tracking as they happen, so valuations carry them instead of relying on memory. Worth 15 minutes to see it against how Skanska UK runs CVRs now?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_a": "Subject: Re: variations never claimed\n\nOne more on this. Because variations, procurements and invoices sit against the same project in Aedrix, the CVR stops being a month-end reconstruction. You see cost against value while there is still time to act on it. Happy to show it with a project loaded, 15 minutes.\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "ai_original_followup_b": "Subject: when it goes to adjudication\n\nHi Richard,\n\ndifferent angle. If a final account ever goes to adjudication, the side with the cleaner record usually has the easier time. Aedrix keeps valuations, applications, variations and the documents behind them logged and dated. Cover for the day you hope never comes. Worth a short call?\n\nBest,\nAedrix Team\n[Unsubscribe]",
            "edited_email_1": None,
            "edited_followup_a": None,
            "edited_followup_b": None,
            "qa_status": "PASS",
            "qa_reasons": []
        },
        "approval": {
            "approval_status": "PENDING_REVIEW",
            "reviewer": "SYSTEM",
            "reviewed_at": None,
            "smartlead_eligible": False,
            "blocked_reason": None,
            "flag_no_strong_signal": False
        }
    }
]
