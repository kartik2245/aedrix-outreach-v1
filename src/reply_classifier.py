"""
reply_classifier.py
Offline Claude Reply Intent Classifier Simulation (Python 3.12).
Deterministic zero-shot classification for prospect replies.
Zero external API calls.
"""

from src.models import ReplyClassificationResult


class ReplyClassifier:
    def classify_reply(self, reply_text: str) -> ReplyClassificationResult:
        """Classifies incoming prospect email reply text."""
        if not reply_text or not isinstance(reply_text, str):
            return ReplyClassificationResult(
                classification="NEGATIVE",
                confidence=0.50,
                reasoning="Empty or invalid reply text.",
                requires_human_handoff=False,
                generation_mode="DRY_RUN_TEMPLATE"
            )

        lower = reply_text.lower()

        # 1. UNSUBSCRIBE Check (MUST be evaluated before POSITIVE)
        if any(kw in lower for kw in ["unsubscribe", "remove me", "stop emailing", "opt out", "take me off"]):
            return ReplyClassificationResult(
                classification="UNSUBSCRIBE",
                confidence=0.99,
                reasoning="Prospect explicitly requested removal from mailing list.",
                requires_human_handoff=False,
                generation_mode="DRY_RUN_TEMPLATE"
            )

        # 2. OOO (Out of Office) Check
        if any(kw in lower for kw in ["out of office", "out of the office", "vacation", "auto-reply", "returning on", "annual leave", "back in the office"]):
            return ReplyClassificationResult(
                classification="OOO",
                confidence=0.95,
                reasoning="Automated out-of-office or vacation responder.",
                requires_human_handoff=False,
                generation_mode="DRY_RUN_TEMPLATE"
            )

        # 3. POSITIVE Intent Check
        if any(kw in lower for kw in ["demo", "interesting", "schedule", "meeting", "call next week", "open to seeing", "send more info", "yes"]):
            return ReplyClassificationResult(
                classification="POSITIVE",
                confidence=0.98,
                reasoning="Prospect expressed interest or requested a demo/meeting.",
                requires_human_handoff=True,
                generation_mode="DRY_RUN_TEMPLATE"
            )

        # 4. NEGATIVE Intent Default
        return ReplyClassificationResult(
            classification="NEGATIVE",
            confidence=0.92,
            reasoning="Prospect declined, expressed no current need, or sent a negative response.",
            requires_human_handoff=False,
            generation_mode="DRY_RUN_TEMPLATE"
        )
