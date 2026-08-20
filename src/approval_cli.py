"""
approval_cli.py
Human Approval & Safety Gate CLI for Aedrix Cold Outreach System (Python 3.12).

Commands:
  python src/approval_cli.py list [--status STATUS]
  python src/approval_cli.py show <lead_id>
  python src/approval_cli.py approve <lead_id> [--reviewer REVIEWER]
  python src/approval_cli.py reject <lead_id> [--reviewer REVIEWER] [--reason REASON]
  python src/approval_cli.py edit <lead_id> [--email-1 TEXT] [--followup-a TEXT] [--followup-b TEXT] [--reviewer REVIEWER]
  python src/approval_cli.py block <lead_id> [--reason REASON] [--reviewer REVIEWER]
"""

import argparse
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_store import ApprovalStore
from src.approval.approval_models import ApprovalStatus


def format_table_row(cols, widths):
    formatted = []
    for col, width in zip(cols, widths):
        val = str(col)
        if len(val) > width:
            val = val[:width - 3] + "..."
        formatted.append(val.ljust(width))
    return " | ".join(formatted)


def cmd_list(engine: ApprovalEngine, args):
    records = engine.store.list_records(args.status)
    if not records:
        print("\nNo approval records found matching criteria.\n")
        return

    print("\n=========================================================================================================")
    print(" AEDRIX HUMAN APPROVAL QUEUE")
    print("=========================================================================================================")

    headers = ["Lead ID", "Company", "Contact", "Status", "Eligible", "QA", "Priority", "Flag"]
    widths = [32, 24, 18, 16, 10, 8, 10, 10]

    print(format_table_row(headers, widths))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))

    for r in records:
        flag_str = "NO_SIGNAL" if r.flag_no_strong_signal else "VERIFIED"
        eligible_str = "YES" if r.smartlead_eligible else "NO"
        row = [
            r.lead_id,
            r.company,
            r.contact,
            r.approval_status.value,
            eligible_str,
            r.qa_status,
            f"{r.priority} ({r.outreach_priority_index})",
            flag_str
        ]
        print(format_table_row(row, widths))

    print("=========================================================================================================\n")
    print(f"Total: {len(records)} record(s) | Pending: {sum(1 for r in records if r.approval_status == ApprovalStatus.PENDING_REVIEW)} | Approved: {sum(1 for r in records if r.approval_status == ApprovalStatus.APPROVED)}\n")


def cmd_show(engine: ApprovalEngine, args):
    record = engine.store.get_record(args.lead_id)
    if not record:
        print(f"\nError: Lead '{args.lead_id}' not found in approval queue.\n")
        return

    print("\n===================================================================")
    print(f" LEAD APPROVAL RECORD: {record.lead_id}")
    print("===================================================================")
    print(f"Company:               {record.company}")
    print(f"Contact:               {record.contact} ({record.title})")
    print(f"Email:                 {record.email}")
    print(f"Qualification:         {record.qualification_status}")
    print(f"Opportunity Score:     {record.opportunity_score} / 100")
    print(f"Accessibility Score:   {record.accessibility_score} / 100")
    print(f"Outreach Priority:     {record.outreach_priority_index} [{record.priority}]")
    print(f"Personalization Note:  {record.personalization_note}")
    print(f"VoC Pain Angle:        {record.voc_angle}")
    print(f"QA Status:             {record.qa_status}")
    if record.qa_reasons:
        print(f"QA Reasons:            {record.qa_reasons}")
    print(f"Approval Status:       {record.approval_status.value}")
    print(f"Smartlead Eligible:    {'YES' if record.smartlead_eligible else 'NO'}")
    if record.reviewer:
        print(f"Reviewer:              {record.reviewer}")
    if record.reviewed_at:
        print(f"Reviewed At:           {record.reviewed_at}")
    if record.blocked_reason:
        print(f"Blocked Reason:        {record.blocked_reason}")

    print("\n--- ORIGINAL AI-GENERATED DRAFT (IMMUTABLE) ---")
    print(f"[Email 1]\n{record.email_1_original}\n")
    print(f"[Follow-up A]\n{record.followup_a_original}\n")
    print(f"[Follow-up B]\n{record.followup_b_original}\n")

    if record.edited_email_1 or record.edited_followup_a or record.edited_followup_b:
        print("--- HUMAN-EDITED DRAFT ---")
        if record.edited_email_1:
            print(f"[Edited Email 1]\n{record.edited_email_1}\n")
        if record.edited_followup_a:
            print(f"[Edited Follow-up A]\n{record.edited_followup_a}\n")
        if record.edited_followup_b:
            print(f"[Edited Follow-up B]\n{record.edited_followup_b}\n")
    print("===================================================================\n")


def cmd_approve(engine: ApprovalEngine, args):
    try:
        record = engine.approve(args.lead_id, reviewer=args.reviewer)
        print(f"\n[SUCCESS] Lead '{record.lead_id}' APPROVED.")
        print(f"  -> Approval Status:    {record.approval_status.value}")
        print(f"  -> Smartlead Eligible: {record.smartlead_eligible}")
        print(f"  -> Reviewer:           {record.reviewer}")
        print(f"  -> Reviewed At:        {record.reviewed_at}\n")
    except Exception as e:
        print(f"\n[FAILED] Could not approve lead: {e}\n")


def cmd_reject(engine: ApprovalEngine, args):
    try:
        record = engine.reject(args.lead_id, reviewer=args.reviewer, reason=args.reason)
        print(f"\n[SUCCESS] Lead '{record.lead_id}' REJECTED.")
        print(f"  -> Approval Status:    {record.approval_status.value}")
        print(f"  -> Smartlead Eligible: {record.smartlead_eligible}")
        print(f"  -> Reason:             {record.blocked_reason}\n")
    except Exception as e:
        print(f"\n[FAILED] Could not reject lead: {e}\n")


def cmd_edit(engine: ApprovalEngine, args):
    try:
        record = engine.edit(
            args.lead_id,
            email_1=args.email_1,
            followup_a=args.followup_a,
            followup_b=args.followup_b,
            reviewer=args.reviewer
        )
        print(f"\n[SUCCESS] Lead '{record.lead_id}' EDITED.")
        print(f"  -> Approval Status:    {record.approval_status.value}")
        print(f"  -> Smartlead Eligible: {record.smartlead_eligible} (Requires explicit approval)")
        print(f"  -> Note: Original AI draft preserved without alteration.\n")
    except Exception as e:
        print(f"\n[FAILED] Could not edit lead: {e}\n")


def cmd_block(engine: ApprovalEngine, args):
    try:
        record = engine.block(args.lead_id, reason=args.reason or "Blocked by operator", reviewer=args.reviewer)
        print(f"\n[SUCCESS] Lead '{record.lead_id}' BLOCKED.")
        print(f"  -> Approval Status:    {record.approval_status.value}")
        print(f"  -> Smartlead Eligible: {record.smartlead_eligible}")
        print(f"  -> Reason:             {record.blocked_reason}\n")
    except Exception as e:
        print(f"\n[FAILED] Could not block lead: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Aedrix Human Approval & Safety Gate CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    list_p = subparsers.add_parser("list", help="List approval queue records")
    list_p.add_argument("--status", choices=["PENDING_REVIEW", "APPROVED", "REJECTED", "EDITED", "BLOCKED"], help="Filter by status")

    # show
    show_p = subparsers.add_parser("show", help="Show full draft details for a lead")
    show_p.add_argument("lead_id", help="Lead ID")

    # approve
    app_p = subparsers.add_parser("approve", help="Approve draft for Smartlead eligibility")
    app_p.add_argument("lead_id", help="Lead ID")
    app_p.add_argument("--reviewer", default="HUMAN_OPERATOR", help="Reviewer name")

    # reject
    rej_p = subparsers.add_parser("reject", help="Reject draft")
    rej_p.add_argument("lead_id", help="Lead ID")
    rej_p.add_argument("--reviewer", default="HUMAN_OPERATOR", help="Reviewer name")
    rej_p.add_argument("--reason", default="Rejected by human reviewer", help="Rejection reason")

    # edit
    edit_p = subparsers.add_parser("edit", help="Edit draft text")
    edit_p.add_argument("lead_id", help="Lead ID")
    edit_p.add_argument("--email-1", dest="email_1", help="New Email 1 text")
    edit_p.add_argument("--followup-a", dest="followup_a", help="New Follow-up A text")
    edit_p.add_argument("--followup-b", dest="followup_b", help="New Follow-up B text")
    edit_p.add_argument("--reviewer", default="HUMAN_OPERATOR", help="Reviewer name")

    # block
    blk_p = subparsers.add_parser("block", help="Block lead from outreach")
    blk_p.add_argument("lead_id", help="Lead ID")
    blk_p.add_argument("--reason", default="Blocked by operator", help="Block reason")
    blk_p.add_argument("--reviewer", default="HUMAN_OPERATOR", help="Reviewer name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    engine = ApprovalEngine()

    if args.command == "list":
        cmd_list(engine, args)
    elif args.command == "show":
        cmd_show(engine, args)
    elif args.command == "approve":
        cmd_approve(engine, args)
    elif args.command == "reject":
        cmd_reject(engine, args)
    elif args.command == "edit":
        cmd_edit(engine, args)
    elif args.command == "block":
        cmd_block(engine, args)


if __name__ == "__main__":
    main()
