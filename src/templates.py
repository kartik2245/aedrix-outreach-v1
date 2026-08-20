"""
templates.py
Fixed approved email templates for AEDRIX V1 outbound role tracks (R1–R6).
Conforms strictly to the "Aedrix Sequences by Company Role" document.
"""

from typing import Dict, Any

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "R1": {
        "email_1": {
            "subject_a": "superseded drawings on site?",
            "subject_b": "the drawing register question",
            "body": "Hi {{first_name}},\n\nmost document controllers at UK contractors have the same worry, that someone on site is working from a superseded drawing and nobody knows yet. Aedrix keeps the drawing and document register, revisions and distribution in one place, so the current revision is the only one anyone can open.\n\nWorth 15 minutes to see how that would run at {{company}}?"
        },
        "followup_a": {
            "body": "Quick addition to my last note. When a revision is issued in Aedrix, everyone holding the old copy is notified through distribution groups, and every issue is logged against the document. That is usually the part that ends the chasing. Happy to show the register with a project loaded rather than a demo file. 15 minutes this week?"
        },
        "followup_b": {
            "subject_a": "who approved that drawing?",
            "subject_b": "the audit trail question",
            "body": "Hi {{first_name}},\n\ndifferent question. When a client, an auditor or an adjudicator asks who approved a document and when, at most contractors the answer lives in email trails and someone loses a day to it. Aedrix logs approvals and issues against each document, so the audit trail is a lookup. If that is a sore point at {{company}}, happy to show it. 15 minutes?"
        },
        "touch_3": {
            "subject_a": "how SJ Roberts run documents",
            "subject_b": "one register, one truth",
            "body": "Hi {{first_name}},\n\nUK contractors including SJ Roberts Construction run project documents on Aedrix. The pattern is consistent, one register, revision control, distribution groups, and an approval trail that holds up when someone asks who signed off. If document control at {{company}} still leans on a master spreadsheet, the module page shows how it works: aedrix.com/solutions/documentmanagement"
        },
        "touch_4": {
            "subject_a": "two minute document check",
            "subject_b": "where the gaps are",
            "body": "Hi {{first_name}},\n\nlast useful thing from me. We built a 2 minute Document Control Health Check, twelve questions scoring revision control, distribution, approvals, site access, compliance records and handover. You get a band and the three fixes with the biggest payoff. Document controllers mostly use the result to make the case internally: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nno reply usually means not now, which is fair. If the paperwork stacks up, or handover season arrives, the door is open. Otherwise I will close the file here. All the best."
        }
    },
    "R2": {
        "email_1": {
            "subject_a": "mobilisation paperwork",
            "subject_b": "starting on site soon?",
            "body": "Hi {{first_name}},\n\nmobilisation is usually where the paperwork bites, subcontractor onboarding, tender packages turning into live documents, drawings landing on site in the right revision. Most contractors run that across a shared drive, a spreadsheet and email. Aedrix runs it from one place, tender through to site. Worth 15 minutes to see how it would fit {{company}}?"
        },
        "followup_a": {
            "body": "One more thought. The teams that get mobilisation right usually pin down document distribution first, because everything else hangs off it. In Aedrix, site teams open current drawings on a phone or tablet, so the printed set in the cabin stops being the reference. Happy to show it against your setup, 15 minutes."
        },
        "followup_b": {
            "subject_a": "rework from a wrong revision",
            "subject_b": "what rebuilding costs",
            "body": "Hi {{first_name}},\n\nmost rework stories start the same way, someone built from a superseded drawing. That is real money and programme, and it is avoidable. Aedrix makes the current revision the only one site can open, with a log of who was issued what. If that risk is on your list at {{company}}, worth a short call?"
        },
        "followup_b_hrb": {
            "subject_a": "the golden thread question",
            "subject_b": "in scope of the Act?",
            "body": "Hi {{first_name}},\n\nfor work in scope of the Building Safety Act, the golden thread is now a duty, a digital, current record of building information kept through design and construction. Most contractors are assembling it from folders and email. Aedrix holds documents, revisions and approvals in one place, which covers most of that. Worth 15 minutes?"
        },
        "touch_3": {
            "subject_a": "how UK contractors run projects",
            "subject_b": "five systems, or one",
            "body": "Hi {{first_name}},\n\ncontractors including SJ Roberts Construction run projects on Aedrix, documents, drawings, photos and progress in one place rather than five systems and a shared drive. The module page shows the workflow: aedrix.com/solutions/projectmanagement. Happy to walk {{company}}'s setup through it in 15 minutes."
        },
        "touch_4": {
            "subject_a": "two minute check",
            "subject_b": "where the time leaks",
            "body": "Hi {{first_name}},\n\nlast one from me. Our 2 minute health check scores how a contractor handles revisions, distribution, approvals, site access and handover, and returns the three fixes with the biggest payoff. Project leads mostly use it to see which gaps sit with them and which sit with document control: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nsilence usually means not now, fair enough. If paperwork starts costing programme, the door is open. Otherwise I will close the file. Good luck with the build."
        }
    },
    "R3": {
        "email_1": {
            "subject_a": "chasing RAMS before Monday?",
            "subject_b": "tickets before site access",
            "body": "Hi {{first_name}},\n\nevery main contractor wants RAMS, inductions and tickets evidenced before anyone sets foot on site, and most specialist contractors chase that through spreadsheets and inbox threads. Aedrix keeps RAMS, inductions and the training matrix in one place, with expiry dates visible. Worth 15 minutes to see how it would work at {{company}}?"
        },
        "followup_a": {
            "body": "Adding one thing. The expiry view is what usually lands, which CSCS cards, tickets and certs run out in the next 60 days, seen before a main contractor's audit finds out first. All crews on one screen. Happy to show it, 15 minutes."
        },
        "followup_b": {
            "subject_a": "timesheets without the Friday chase",
            "subject_b": "hours across three sites",
            "body": "Hi {{first_name}},\n\ndifferent angle. If Friday still means chasing timesheets from three sites, Aedrix captures timesheets and holidays against each project, so payroll and job costing stop being a reconstruction exercise. Fifteen minutes to see it against how {{company}} runs now?"
        },
        "touch_3": {
            "subject_a": "records that pass any audit",
            "subject_b": "evidence in one place",
            "body": "Hi {{first_name}},\n\nUK contractors including SJ Roberts Construction run Aedrix day to day. For specialist contractors the draw is usually the same, workforce records that satisfy a main contractor audit without a scramble. The module page shows it: aedrix.com/solutions/manpowermanagement"
        },
        "touch_4": {
            "subject_a": "two minute records check",
            "subject_b": "before the next audit",
            "body": "Hi {{first_name}},\n\nlast useful thing. The 2 minute health check scores how a contractor handles compliance records, site documents and handover evidence, and returns the three cheapest fixes. Contracts managers tend to run it before framework audits: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nno reply means not now, fair enough. If an audit or a new framework makes records urgent, the door is open. Otherwise I will close the file. All the best."
        }
    },
    "R4": {
        "email_1": {
            "subject_a": "variations never claimed",
            "subject_b": "margin that walks off site",
            "body": "Hi {{first_name}},\n\nmost margin leaks the same way, variations agreed on site, never recorded, missing from the application for payment. Aedrix logs variations against cost tracking as they happen, so valuations carry them instead of relying on memory. Worth 15 minutes to see it against how {{company}} runs CVRs now?"
        },
        "followup_a": {
            "body": "One more on this. Because variations, procurements and invoices sit against the same project in Aedrix, the CVR stops being a month-end reconstruction. You see cost against value while there is still time to act on it. Happy to show it with a project loaded, 15 minutes."
        },
        "followup_b": {
            "subject_a": "when it goes to adjudication",
            "subject_b": "the final account record",
            "body": "Hi {{first_name}},\n\ndifferent angle. If a final account ever goes to adjudication, the side with the cleaner record usually has the easier time. Aedrix keeps valuations, applications, variations and the documents behind them logged and dated. Cover for the day you hope never comes. Worth a short call?"
        },
        "touch_3": {
            "subject_a": "one place for commercials",
            "subject_b": "a spreadsheet per surveyor",
            "body": "Hi {{first_name}},\n\nUK contractors including SJ Roberts Construction run Aedrix. On the commercial side the pattern is one place for cost tracking, procurements, invoices, valuations and variations, rather than a spreadsheet per surveyor. The module page shows it: aedrix.com/solutions/financialmanagement"
        },
        "touch_4": {
            "subject_a": "two minute evidence check",
            "subject_b": "gaps that surface later",
            "body": "Hi {{first_name}},\n\nlast one. The 2 minute health check covers how well approvals, variations and handover records are evidenced. The gaps it finds are usually the ones that surface at final account. Two minutes, three fixes: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nsilence means not now, fair enough. If a final account or a difficult valuation makes records urgent, the door is open. Otherwise I will close the file."
        }
    },
    "R5": {
        "email_1": {
            "subject_a": "a CDE clients will accept",
            "subject_b": "information requirements",
            "body": "Hi {{first_name}},\n\nmore clients now expect a common data environment, and running one from folders and email does not survive an audit. Aedrix holds drawings, BIM documents and revisions with controlled distribution, which covers the working core of that requirement. Worth 15 minutes to see where it fits what {{company}} already has?"
        },
        "followup_a": {
            "body": "Following on. The part teams feel daily is revision flow, design changes reaching site as controlled issues rather than email attachments, with interactive drawings viewable on a phone. If you are midway through standing up a CDE, I can show where Aedrix fits. 15 minutes."
        },
        "followup_b": {
            "subject_a": "the golden thread question",
            "subject_b": "who owns the record",
            "body": "Hi {{first_name}},\n\ndifferent angle. The Building Safety Act makes the golden thread a duty on in-scope buildings, a digital, current record kept through design and construction. Assembling that from shared drives is the hard way. Aedrix keeps documents, revisions and approvals in one place, most of the thread by default. Worth a short call?"
        },
        "followup_b_hrb": {
            "subject_a": "the golden thread question",
            "subject_b": "in scope of the Act?",
            "body": "Hi {{first_name}},\n\nfor work in scope of the Building Safety Act, the golden thread is now a duty, a digital, current record of building information kept through design and construction. Most contractors are assembling it from folders and email. Aedrix holds documents, revisions and approvals in one place, which covers most of that. Worth 15 minutes?"
        },
        "touch_3": {
            "subject_a": "drawings, BIM, one register",
            "subject_b": "how contractors run it",
            "body": "Hi {{first_name}},\n\nUK contractors including SJ Roberts Construction run drawings and project documents on Aedrix, BIM documents and interactive drawings included. The module page shows the workflow: aedrix.com/solutions/documentmanagement"
        },
        "touch_4": {
            "subject_a": "two minute CDE check",
            "subject_b": "a gap read in two minutes",
            "body": "Hi {{first_name}},\n\nlast one from me. The 2 minute health check scores revision control, distribution, approvals and site access. A quick read on how far a business is from a defensible CDE, with the three fixes that close most of the gap: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nno reply means not now, which is fair. If an information requirement lands on the next bid, the door is open. Otherwise I will close the file."
        }
    },
    "R6": {
        "email_1": {
            "subject_a": "service records when clients ask",
            "subject_b": "proving the work happened",
            "body": "Hi {{first_name}},\n\nmaintenance contracts live and die on evidence, inspections done, service requests closed, records ready when the client or an auditor asks. Aedrix runs recurring tasks, service requests and inspections with digital records against each contract. Worth 15 minutes to see it against how {{company}} works now?"
        },
        "followup_a": {
            "body": "One addition. Recurring tasks are the quiet win, planned inspections scheduled once, then evidenced as crews complete them, so nothing depends on someone remembering. Happy to show a live view, 15 minutes."
        },
        "followup_b": {
            "subject_a": "renewal without the scramble",
            "subject_b": "the folder assembly week",
            "body": "Hi {{first_name}},\n\ndifferent angle. When a contract comes up for renewal, the provider with clean records has the easier conversation. Aedrix keeps inspection history, service requests and completion evidence in one place per client. If renewals at {{company}} still mean assembling folders, worth a short call?"
        },
        "touch_3": {
            "subject_a": "evidence in one place",
            "subject_b": "how UK firms run it",
            "body": "Hi {{first_name}},\n\nUK firms including SJ Roberts Construction run their project records on Aedrix. For maintenance and service agencies the workflow covers recurring tasks, service requests, inspections and digital records against each client: aedrix.com/whoweserve"
        },
        "touch_4": {
            "subject_a": "two minute records check",
            "subject_b": "before the client review",
            "body": "Hi {{first_name}},\n\nlast useful thing. The 2 minute health check scores how compliance records, document control and handover evidence are handled, and returns the three cheapest fixes. A fast read before the next client review: aedrix.com/health-check"
        },
        "touch_5": {
            "body": "Hi {{first_name}},\n\nno reply means not now, fair enough. If a client review or renewal makes records urgent, the door is open. Otherwise I will close the file."
        }
    }
}
