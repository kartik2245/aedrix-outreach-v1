"""
production_batch_runner.py
Master Production Batch Runner with Human Approval Gate Integration for Aedrix Cold Outreach System (Python 3.12).

Flow:
Deepline Research Export
        ↓
Deepline Export Adapter (src/deepline_export_adapter.py)
        ↓
Research Normalizer (src/research_normalizer.py)
        ↓
Evidence Validator (src/evidence_validator.py)
        ↓
ICP Engine (src/icp/icp_engine.py)
        ↓
Lead Intelligence Engine (src/lead_intelligence.py)
        ↓
VoC Engine (src/personalization/voc_engine.py)
        ↓
Claude Personalization Engine (src/integrations/claude_client.py)
        ↓
Personalization QA (src/personalization/personalization_qa.py)
        ↓
Human Approval Gate (src/approval/approval_engine.py)
        ↓
Local JSON Output: data/claude_personalization_drafts.json & data/approval_queue.json

SAFETY GUARANTEES:
- All generated drafts start as PENDING_REVIEW (smartlead_eligible=False).
- Hard disqualifications, exclusions, and QA failures are auto-BLOCKED.
- ZERO real email sending.
- ZERO Smartlead API calls.
- ZERO external credit consumption.
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.deepline_export_adapter import DeeplineExportAdapter
from src.research_normalizer import ResearchNormalizer
from src.evidence_validator import EvidenceValidator
from src.icp.icp_engine import ICPEngine
from src.lead_intelligence import LeadIntelligenceEngine
from src.personalization.voc_engine import VoCEngine
from src.integrations.bedrock_client import BedrockClient
from src.integrations.claude_client import ClaudeClient
from src.personalization.personalization_qa import PersonalizationQA
from src.email_generator import EmailGenerator
from src.approval.approval_engine import ApprovalEngine
from src.approval.approval_store import ApprovalStore
from src.approval.approval_models import ApprovalStatus
from src.models import (
    DisqualificationStatus,
    PersonalizationNoteStatus,
    BatchLeadDraftOutput,
    LeadIntelligenceOutput,
)


class ProductionBatchRunner:
    def __init__(
        self,
        config_path: Optional[str] = None,
        llm_client: Optional[Any] = None,
        claude_client: Optional[Any] = None,
        approval_store: Optional[ApprovalStore] = None,
    ):
        self.adapter = DeeplineExportAdapter()
        self.normalizer = ResearchNormalizer()
        self.validator = EvidenceValidator()
        self.icp_engine = ICPEngine(config_path=config_path)
        self.intel_engine = LeadIntelligenceEngine()
        self.voc_engine = VoCEngine()
        self.llm_client = llm_client or claude_client or BedrockClient()
        self.claude_client = self.llm_client
        self.qa_engine = PersonalizationQA()
        self.email_generator = EmailGenerator(
            llm_client=self.llm_client,
            voc_engine=self.voc_engine,
            qa_engine=self.qa_engine,
        )
        self.approval_store = approval_store or ApprovalStore()
        self.approval_engine = ApprovalEngine(store=self.approval_store)

    def run_batch(
        self,
        input_export_path: str,
        output_drafts_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Executes full production batch flow on Deepline research export and enrolls into Approval Queue."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not output_drafts_path:
            output_drafts_path = os.path.join(base_dir, "data", "claude_personalization_drafts.json")

        print("===================================================================")
        print(" AEDRIX PRODUCTION BATCH RUNNER - EMAIL DRAFT & APPROVAL PIPELINE")
        print(f" Dry-Run Mode: {self.claude_client.dry_run} | Send Emails: {self.claude_client.send_emails}")
        print(" Safety: ZERO emails sent, ZERO Smartlead calls, ZERO credits spent")
        print(" Human Gate: All drafts require explicit human review before sending")
        print("===================================================================\n")

        # Step 1: Adapt Deepline export
        adapted_records = self.adapter.adapt(input_export_path)

        # Step 2: Normalize
        normalized_records = self.normalizer.normalize(adapted_records)

        # Step 3: Validate evidence
        validated_records = self.validator.validate(normalized_records)

        draft_outputs: List[Dict[str, Any]] = []

        print(f"Loaded and validated {len(validated_records)} lead records from research export.\n")

        for idx, rec in enumerate(validated_records):
            company_name = rec.get("company_name", f"Lead {idx+1}")
            print(f"[{idx+1}/{len(validated_records)}] Processing: {company_name}")

            # Step 4: ICP Qualification
            icp_result = self.icp_engine.evaluate_lead(rec)
            print(f"  -> ICP Status: {icp_result.status.value}" + (f" ({icp_result.disqualification_reason})" if icp_result.disqualification_reason else ""))

            # Step 5: Lead Intelligence
            lead_intel = self.intel_engine.process_lead(rec)

            if icp_result.status != DisqualificationStatus.QUALIFIED:
                print(f"  -> Skipping draft generation (Non-qualified lead) -> Enrolling as BLOCKED in Approval Queue")
                
                # Enroll blocked record into approval engine
                self.approval_engine.enroll_draft(
                    company=lead_intel.company_name,
                    contact=lead_intel.contact_name,
                    title=lead_intel.job_title,
                    email=lead_intel.email,
                    qualification_status=icp_result.status.value,
                    opportunity_score=lead_intel.opportunity_score,
                    accessibility_score=lead_intel.accessibility_score,
                    outreach_priority_index=lead_intel.outreach_priority_index,
                    priority=lead_intel.priority_level.value,
                    personalization_status=lead_intel.personalization_note_status.value,
                    personalization_note=lead_intel.personalization_note,
                    voc_angle="N/A - Disqualified / Excluded",
                    email_1=f"[SKIPPED] Disqualified: {icp_result.disqualification_reason}",
                    followup_a="[SKIPPED]",
                    followup_b="[SKIPPED]",
                    qa_status="SKIPPED",
                    qa_reasons=[icp_result.disqualification_reason or "Lead disqualified/excluded by ICP Engine"],
                    email_status=lead_intel.email_status.value,
                    disqualification_reason=icp_result.disqualification_reason
                )

                record_output = {
                    "company": lead_intel.company_name,
                    "contact": lead_intel.contact_name,
                    "title": lead_intel.job_title,
                    "qualification_status": icp_result.status.value,
                    "opportunity_score": lead_intel.opportunity_score,
                    "accessibility_score": lead_intel.accessibility_score,
                    "outreach_priority_index": lead_intel.outreach_priority_index,
                    "priority": lead_intel.priority_level.value,
                    "personalization_note_status": lead_intel.personalization_note_status.value,
                    "personalization_note": lead_intel.personalization_note,
                    "voc_angle": "N/A - Disqualified / Excluded",
                    "email_1": f"[SKIPPED] Disqualified: {icp_result.disqualification_reason}",
                    "followup_a": "[SKIPPED]",
                    "followup_b": "[SKIPPED]",
                    "qa_status": "SKIPPED",
                    "qa_reasons": [icp_result.disqualification_reason or "Lead disqualified/excluded by ICP Engine"]
                }
                draft_outputs.append(record_output)
                print("")
                continue

            # Step 6 & 7: VoC Mapping + Email Generation + Personalization QA
            voc_context = self.voc_engine.map_lead_voc(lead_intel)
            print(f"  -> VoC Pain Angle: {voc_context.voc_angle}")

            e1 = self.email_generator.generate_email_1(lead_intel, voc_context)
            fa = self.email_generator.generate_followup_a(lead_intel, e1, voc_context)
            fb = self.email_generator.generate_followup_b(lead_intel, voc_context)

            qa_res = self.qa_engine.validate_lead_drafts(lead_intel, e1, fa, fb)
            print(f"  -> QA Status: {qa_res.qa_status} | E1: {e1.word_count}w, FA: {fa.word_count}w, FB: {fb.word_count}w")
            if qa_res.qa_reasons:
                print(f"  -> QA Issues: {qa_res.qa_reasons}")

            # Step 8: Enroll into Approval Queue
            approval_rec = self.approval_engine.enroll_draft(
                company=lead_intel.company_name,
                contact=lead_intel.contact_name,
                title=lead_intel.job_title,
                email=lead_intel.email,
                qualification_status=icp_result.status.value,
                opportunity_score=lead_intel.opportunity_score,
                accessibility_score=lead_intel.accessibility_score,
                outreach_priority_index=lead_intel.outreach_priority_index,
                priority=lead_intel.priority_level.value,
                personalization_status=lead_intel.personalization_note_status.value,
                personalization_note=lead_intel.personalization_note,
                voc_angle=voc_context.voc_angle,
                email_1=e1.body,
                followup_a=fa.body,
                followup_b=fb.body,
                qa_status=qa_res.qa_status,
                qa_reasons=qa_res.qa_reasons,
                email_status=lead_intel.email_status.value,
                disqualification_reason=None
            )
            print(f"  -> Approval Queue Status: {approval_rec.approval_status.value} (Smartlead Eligible: {approval_rec.smartlead_eligible})")

            record_output = {
                "company": lead_intel.company_name,
                "contact": lead_intel.contact_name,
                "title": lead_intel.job_title,
                "qualification_status": icp_result.status.value,
                "opportunity_score": lead_intel.opportunity_score,
                "accessibility_score": lead_intel.accessibility_score,
                "outreach_priority_index": lead_intel.outreach_priority_index,
                "priority": lead_intel.priority_level.value,
                "personalization_note_status": lead_intel.personalization_note_status.value,
                "personalization_note": lead_intel.personalization_note,
                "voc_angle": voc_context.voc_angle,
                "email_1": e1.body,
                "followup_a": fa.body,
                "followup_b": fb.body,
                "qa_status": qa_res.qa_status,
                "qa_reasons": qa_res.qa_reasons
            }
            draft_outputs.append(record_output)
            print("")

        # Save to Local JSON Output (Drafts)
        os.makedirs(os.path.dirname(output_drafts_path), exist_ok=True)
        with open(output_drafts_path, "w", encoding="utf-8") as f:
            json.dump(draft_outputs, f, indent=2)

        print(f"Drafts saved successfully to: {output_drafts_path}")
        print(f"Approval queue persisted to: {self.approval_store.storage_path}")
        print(f"Total processed: {len(draft_outputs)} | Enrolled in Human Approval Gate: {len(self.approval_store.load_queue())}\n")

        return draft_outputs


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_export = os.path.join(base_dir, "data", "deepline_export_sample.json")
    output_drafts = os.path.join(base_dir, "data", "claude_personalization_drafts.json")

    runner = ProductionBatchRunner()
    runner.run_batch(sample_export, output_drafts)


if __name__ == "__main__":
    main()
