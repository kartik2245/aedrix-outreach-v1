"""
personalization_qa.py
19-Point Personalization QA & Outbound Safety Layer for Aedrix Cold Outreach System.
Verifies all copy constraints from the "Aedrix Sequences by Company Role" document.
"""

import re
from typing import Dict, Any, List, Optional, Union
from src.models import (
    LeadIntelligenceOutput,
    EmailGenerationResult,
    PersonalizationQAResult,
    PersonalizationNoteStatus,
)


class PersonalizationQA:
    BANNED_WORDS = ["streamline", "seamless", "empower", "solution", "leverage"]
    AMERICANISMS = ["change orders", "punch list", "gc", "blueprints", "jobsite"]

    def get_body_content(self, body: str) -> str:
        """Returns email body content excluding signature block."""
        parts = re.split(r"\b(Best|All the best|Best regards),", body)
        if parts:
            return parts[0].strip()
        return body.strip()

    def validate_lead_drafts(
        self,
        lead_intel: LeadIntelligenceOutput,
        email_1: Union[EmailGenerationResult, str],
        followup_a: Optional[Union[EmailGenerationResult, str]] = None,
        followup_b: Optional[Union[EmailGenerationResult, str]] = None,
        touch_3: Optional[Union[EmailGenerationResult, str]] = None,
        touch_4: Optional[Union[EmailGenerationResult, str]] = None,
        touch_5: Optional[Union[EmailGenerationResult, str]] = None,
    ) -> PersonalizationQAResult:
        """
        Runs comprehensive 19-point Personalization QA checks on all sequence steps.
        Invalid leads must be placed on HOLD (FAIL status).
        """
        reasons: List[str] = []
        checks_passed: List[str] = []
        checks_failed: List[str] = []

        # Extract values
        e1_body = email_1.body if isinstance(email_1, EmailGenerationResult) else str(email_1)
        e1_subject = email_1.subject if isinstance(email_1, EmailGenerationResult) else ""

        fa_body = (followup_a.body if isinstance(followup_a, EmailGenerationResult) else str(followup_a or "")).strip()
        fa_subject = (followup_a.subject if isinstance(followup_a, EmailGenerationResult) else "").strip()

        fb_body = (followup_b.body if isinstance(followup_b, EmailGenerationResult) else str(followup_b or "")).strip()
        fb_subject = (followup_b.subject if isinstance(followup_b, EmailGenerationResult) else "").strip()

        t3_body = (touch_3.body if isinstance(touch_3, EmailGenerationResult) else str(touch_3 or "")).strip()
        t3_subject = (touch_3.subject if isinstance(touch_3, EmailGenerationResult) else "").strip()

        t4_body = (touch_4.body if isinstance(touch_4, EmailGenerationResult) else str(touch_4 or "")).strip()
        t4_subject = (touch_4.subject if isinstance(touch_4, EmailGenerationResult) else "").strip()

        t5_body = (touch_5.body if isinstance(touch_5, EmailGenerationResult) else str(touch_5 or "")).strip()
        t5_subject = (touch_5.subject if isinstance(touch_5, EmailGenerationResult) else "").strip()

        # Word count variables
        word_counts = {
            "email_1": len(self.get_body_content(e1_body).split()),
            "followup_a": len(self.get_body_content(fa_body).split()) if fa_body else 0,
            "followup_b": len(self.get_body_content(fb_body).split()) if fb_body else 0,
            "touch_3": len(self.get_body_content(t3_body).split()) if t3_body else 0,
            "touch_4": len(self.get_body_content(t4_body).split()) if t4_body else 0,
            "touch_5": len(self.get_body_content(t5_body).split()) if t5_body else 0,
        }

        # 1. Variables Gate: first_name and company must exist
        names = lead_intel.contact_name.strip().split()
        first_name = names[0].capitalize() if names else ""
        if not first_name or first_name.lower() == "there":
            reasons.append("Missing first_name or fallback 'Hi there' detected.")
            checks_failed.append("VARIABLES_GATE_FIRST_NAME")
        else:
            checks_passed.append("VARIABLES_GATE_FIRST_NAME")

        if not lead_intel.company_name or not lead_intel.company_name.strip():
            reasons.append("Missing company name variable.")
            checks_failed.append("VARIABLES_GATE_COMPANY")
        else:
            checks_passed.append("VARIABLES_GATE_COMPANY")

        # 2. Body Word Limit Checks
        if word_counts["email_1"] > 90:
            reasons.append(f"Email 1 exceeds limit ({word_counts['email_1']} > 90 words).")
            checks_failed.append("WORD_COUNT_EMAIL_1")
        else:
            checks_passed.append("WORD_COUNT_EMAIL_1")

        if fa_body and word_counts["followup_a"] > 90:
            reasons.append(f"Follow-up A exceeds limit ({word_counts['followup_a']} > 90 words).")
            checks_failed.append("WORD_COUNT_FOLLOWUP_A")
        elif fa_body:
            checks_passed.append("WORD_COUNT_FOLLOWUP_A")

        if fb_body and word_counts["followup_b"] > 90:
            reasons.append(f"Follow-up B exceeds limit ({word_counts['followup_b']} > 90 words).")
            checks_failed.append("WORD_COUNT_FOLLOWUP_B")
        elif fb_body:
            checks_passed.append("WORD_COUNT_FOLLOWUP_B")

        if t3_body and word_counts["touch_3"] > 90:
            reasons.append(f"Touch 3 exceeds limit ({word_counts['touch_3']} > 90 words).")
            checks_failed.append("WORD_COUNT_TOUCH_3")
        elif t3_body:
            checks_passed.append("WORD_COUNT_TOUCH_3")

        if t4_body and word_counts["touch_4"] > 90:
            reasons.append(f"Touch 4 exceeds limit ({word_counts['touch_4']} > 90 words).")
            checks_failed.append("WORD_COUNT_TOUCH_4")
        elif t4_body:
            checks_passed.append("WORD_COUNT_TOUCH_4")

        # Touch 5 limit: <= 45 words
        if t5_body and word_counts["touch_5"] > 45:
            reasons.append(f"Touch 5 exceeds limit ({word_counts['touch_5']} > 45 words).")
            checks_failed.append("WORD_COUNT_TOUCH_5")
        elif t5_body:
            checks_passed.append("WORD_COUNT_TOUCH_5")

        # 3. Subject Word Count Limit Checks (<= 6 words)
        for name, subject in [
            ("Email 1", e1_subject),
            ("Follow-up B", fb_subject),
            ("Touch 3", t3_subject),
            ("Touch 4", t4_subject)
        ]:
            if subject:
                words = len(subject.split())
                if words > 6:
                    reasons.append(f"{name} subject exceeds 6 words ({words} words: '{subject}').")
                    checks_failed.append(f"SUBJECT_WORD_COUNT_{name.upper().replace(' ', '_')}")
                else:
                    checks_passed.append(f"SUBJECT_WORD_COUNT_{name.upper().replace(' ', '_')}")

        # 4. No "Hi there"
        all_draft_text = f"{e1_body} {fa_body} {fb_body} {t3_body} {t4_body} {t5_body}"
        all_text_lower = all_draft_text.lower()
        if "hi there" in all_text_lower or "hello there" in all_text_lower:
            reasons.append("Banned greeting 'Hi there' or 'Hello there' detected.")
            checks_failed.append("NO_HI_THERE")
        else:
            checks_passed.append("NO_HI_THERE")

        # 5. No Exclamation Marks
        if "!" in all_draft_text or "!" in f"{e1_subject} {fb_subject} {t3_subject} {t4_subject}":
            reasons.append("Exclamation mark (!) detected in subject or body.")
            checks_failed.append("NO_EXCLAMATION")
        else:
            checks_passed.append("NO_EXCLAMATION")

        # 6. No Em Dashes
        if "—" in all_draft_text or "--" in all_draft_text:
            reasons.append("Em dash (—) or '--' detected in subject or body.")
            checks_failed.append("NO_EM_DASH")
        else:
            checks_passed.append("NO_EM_DASH")

        # 7. Banned Vendor Language (streamline, seamless, empower, solution, leverage)
        for banned in self.BANNED_WORDS:
            if re.search(r"\b" + banned + r"\b", all_text_lower):
                reasons.append(f"Banned vendor word '{banned}' detected.")
                checks_failed.append(f"NO_BANNED_{banned.upper()}")
            else:
                checks_passed.append(f"NO_BANNED_{banned.upper()}")

        # 8. Banned Americanisms (change orders, punch list, GC, blueprints, jobsite)
        for banned in self.AMERICANISMS:
            if re.search(r"\b" + banned + r"\b", all_text_lower):
                reasons.append(f"Banned Americanism '{banned}' detected.")
                checks_failed.append(f"NO_AMERICANISM_{banned.upper().replace(' ', '_')}")
            else:
                checks_passed.append(f"NO_AMERICANISM_{banned.upper().replace(' ', '_')}")

        # 9. No Fake "Re:" for New Threads
        for name, subject in [
            ("Email 1", e1_subject),
            ("Follow-up B", fb_subject),
            ("Touch 3", t3_subject),
            ("Touch 4", t4_subject)
        ]:
            if subject and (subject.lower().startswith("re:") or subject.lower().startswith("re -")):
                reasons.append(f"Fake 'Re:' prefix found on new thread {name} subject.")
                checks_failed.append(f"NO_FAKE_RE_{name.upper().replace(' ', '_')}")
            else:
                checks_passed.append(f"NO_FAKE_RE_{name.upper().replace(' ', '_')}")

        # 10. Required Variables Resolved (no unresolved double curly braces)
        if "{{" in all_draft_text or "}}" in all_draft_text:
            reasons.append("Unresolved variables (curly braces) remaining in draft copy.")
            checks_failed.append("VARIABLES_RESOLVED")
        else:
            checks_passed.append("VARIABLES_RESOLVED")

        # 11. Approved Signature and Unsubscribe mechanism
        # Only check drafts that are actually non-empty
        drafts_to_check = [("Email 1", e1_body)]
        if fa_body: drafts_to_check.append(("Follow-up A", fa_body))
        if fb_body: drafts_to_check.append(("Follow-up B", fb_body))
        if t3_body: drafts_to_check.append(("Touch 3", t3_body))
        if t4_body: drafts_to_check.append(("Touch 4", t4_body))
        if t5_body: drafts_to_check.append(("Touch 5", t5_body))

        for name, body in drafts_to_check:
            # Allow "Alex Mitchell" or "Aedrix Team" or "Aedrix" as valid signature
            if not any(sig in body for sig in ["Alex Mitchell", "Aedrix Team", "Aedrix"]):
                reasons.append(f"Approved signature missing from {name}.")
                checks_failed.append(f"SIGNATURE_PRESENT_{name.upper().replace(' ', '_')}")
            else:
                checks_passed.append(f"SIGNATURE_PRESENT_{name.upper().replace(' ', '_')}")

            if "unsubscribe" not in body.lower():
                reasons.append(f"Unsubscribe link/mechanism missing from {name}.")
                checks_failed.append(f"UNSUBSCRIBE_PRESENT_{name.upper().replace(' ', '_')}")
            else:
                checks_passed.append(f"UNSUBSCRIBE_PRESENT_{name.upper().replace(' ', '_')}")

        # 12. Check for Invented Dates/Years (legacy validation)
        years_in_draft = set(re.findall(r"\b(20\d\d)\b", all_draft_text))
        company_name = getattr(lead_intel, "company_name", "") or ""
        contact_name = getattr(lead_intel, "contact_name", "") or ""
        job_title = getattr(lead_intel, "job_title", "") or ""
        relevant_signal = getattr(lead_intel, "relevant_signal", "") or ""
        personalization_note = getattr(lead_intel, "personalization_note", "") or ""
        research_sources = getattr(lead_intel, "research_sources", []) or []
        industry = getattr(lead_intel, "industry", "") or ""
        company_size = getattr(lead_intel, "company_size", "") or ""
        evidence_corpus = f"{company_name} {contact_name} {job_title} {relevant_signal} {personalization_note} {' '.join(research_sources)} {industry} {company_size}".lower()
        for yr in years_in_draft:
            if yr not in evidence_corpus:
                reasons.append(f"Invented date/year '{yr}' detected not present in verified research signals.")
                checks_failed.append("NO_INVENTED_DATES")
                break
        else:
            checks_passed.append("NO_INVENTED_DATES")

        # 13. Check for Fabricated Metric Claims
        # Normalize replacement characters to £
        all_draft_normalized = all_draft_text
        for raw_char in ["\ufffd", "\u00a3"]:
            all_draft_normalized = all_draft_normalized.replace(raw_char, "£")
        money_matches = set(re.findall(r"(?:£|\$|€)\s*\d+(?:\.\d+)?[MBK]?", all_draft_normalized, re.IGNORECASE))
        for m in money_matches:
            clean_m = m.lower().replace(" ", "")
            if clean_m not in evidence_corpus.replace(" ", ""):
                reasons.append(f"Fabricated financial metric '{m}' detected in draft.")
                checks_failed.append("NO_FABRICATED_METRICS")
                break
        else:
            checks_passed.append("NO_FABRICATED_METRICS")

        # 14. Check for Fabricated Partnerships
        suspicious_partners = re.findall(r"(?:partnered with|partnering with|teamed up with)\s+([A-Z][A-Za-z0-9\s&]+)", all_draft_text)
        for partner in suspicious_partners:
            partner_clean = partner.strip().lower()
            if partner_clean and partner_clean not in evidence_corpus and "aedrix" not in partner_clean:
                reasons.append(f"Fabricated partnership claim with '{partner.strip()}' detected.")
                checks_failed.append("NO_FABRICATED_PARTNERSHIPS")
                break
        else:
            checks_passed.append("NO_FABRICATED_PARTNERSHIPS")

        # 15. Check Personalization consistency with NO_STRONG_SIGNAL
        p_status = getattr(lead_intel, "personalization_note_status", None)
        if p_status in (PersonalizationNoteStatus.NO_STRONG_SIGNAL, "NO_STRONG_SIGNAL"):
            fake_signal_indicators = ["saw your recent announcement", "congratulations on", "read about your recent", "saw your press release"]
            if any(ind in all_text_lower for ind in fake_signal_indicators):
                reasons.append("Fabricated personalization note found on a lead marked NO_STRONG_SIGNAL.")
                checks_failed.append("PERSONALIZATION_MATCHES_EVIDENCE")
            else:
                checks_passed.append("PERSONALIZATION_MATCHES_EVIDENCE")
        else:
            checks_passed.append("PERSONALIZATION_MATCHES_EVIDENCE")

        # 16. Check for Internal System Leaks (e.g. NO_STRONG_SIGNAL, SIGNAL_VERIFIED, HARD_DISQUALIFIED)
        forbidden_internal_terms = [
            "NO_STRONG_SIGNAL",
            "SIGNAL_VERIFIED",
            "HARD_DISQUALIFIED",
            "CAMPAIGN_EXCLUDED",
            "INVALID_BOUNCED",
        ]
        for term in forbidden_internal_terms:
            if term.lower() in all_text_lower:
                reasons.append(f"Forbidden internal system code/label '{term}' leaked into generated email copy.")
                checks_failed.append("NO_INTERNAL_SYSTEM_LEAKS")
                break
        else:
            checks_passed.append("NO_INTERNAL_SYSTEM_LEAKS")

        qa_status = "PASS" if len(reasons) == 0 else "FAIL"

        return PersonalizationQAResult(
            qa_status=qa_status,
            qa_reasons=reasons,
            word_counts=word_counts,
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )
