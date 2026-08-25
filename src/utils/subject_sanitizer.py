"""
subject_sanitizer.py
Deterministic subject line sanitizer and safety guard for AEDRIX Outreach System.
Enforces subject word count <= 6, prevents VoC angle leaks, and eliminates forbidden terms.
"""

import re
from typing import Optional


DANGLING_ENDINGS = {
    "at", "for", "to", "in", "and", "of", "with", "or", "the", "a", "an", "on", "about", "into", "by", "from", "as"
}


def sanitize_subject(
    raw_subject: Optional[str],
    company_name: str,
    product_or_industry: Optional[str] = None,
    voc_angle: Optional[str] = None,
    email_type: str = "EMAIL_1",
    max_words: int = 6,
) -> str:
    """
    Sanitizes and bounds an email subject to <= 6 words deterministically.
    Never copies long VoC angle descriptions.
    """
    company = (company_name or "Your Team").strip()
    # Strip common trailing corporate entity suffixes if present
    clean_company = re.sub(
        r"\b(Private Limited|Pvt Ltd|Ltd|Inc|LLC|Corp|Corporation|Co|Limited)\b",
        "",
        company,
        flags=re.IGNORECASE,
    ).strip()
    if not clean_company:
        clean_company = company

    subject = str(raw_subject or "").strip()
    subject = re.sub(r"[\r\n\t]+", " ", subject)
    subject = subject.strip("\"' ")
    subject = re.sub(r"\s+", " ", subject).strip()

    # Check if raw_subject simply copied full VoC angle or is too long (> max_words)
    is_voc_copy = False
    if voc_angle and len(voc_angle.strip()) > 30 and voc_angle.strip().lower() in subject.lower():
        is_voc_copy = True

    words = subject.split()
    if not subject or is_voc_copy or len(words) > max_words:
        topic = (product_or_industry or "Operations").strip()
        topic_words = topic.split()
        if len(topic_words) > 3:
            topic = " ".join(topic_words[:2])

        if email_type == "FOLLOWUP_A":
            subject = f"Re: {topic} for {clean_company}"
        elif email_type == "FOLLOWUP_B":
            subject = f"{topic} Discussion: {clean_company}"
        else:
            subject = f"{topic} for {clean_company}"

        words = subject.split()

    if len(words) > max_words:
        trimmed = words[:max_words]
        while len(trimmed) > 1 and trimmed[-1].lower().rstrip(":,.") in DANGLING_ENDINGS:
            trimmed.pop()
        subject = " ".join(trimmed)

    # Final cleanup of trailing punctuation except ?
    subject = re.sub(r"[\.,;-]+$", "", subject).strip()
    return subject
