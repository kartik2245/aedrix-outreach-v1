"""
outreach_state_machine.py
Comprehensive Outreach State Machine Engine for Phase 5 (Python 3.12).
Strictly manages lead state transitions, delays (metadata), and transition history.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from src.models import OutreachState


class OutreachStateMachine:
    def __init__(self, lead_email: str):
        self.lead_email = lead_email
        self.current_state = OutreachState.INITIAL
        self.history: List[Dict[str, Any]] = [
            {
                "state": OutreachState.INITIAL.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {}
            }
        ]

    def transition(self, new_state: OutreachState, metadata: Dict[str, Any] = None) -> OutreachState:
        """Transitions state machine to new state with metadata."""
        if metadata is None:
            metadata = {}
        self.current_state = new_state
        record = {
            "state": new_state.value if isinstance(new_state, OutreachState) else str(new_state),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata
        }
        self.history.append(record)
        return self.current_state

    def get_current_state(self) -> OutreachState:
        return self.current_state

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
