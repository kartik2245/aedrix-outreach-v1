"""
deepline_client.py
Production-ready Deepline Lead Discovery & Enrichment Client (Python 3.12).

Safety Gates:
- DEEPLINE_LIVE: Must be set to 'true' to permit network API calls.
- DEEPLINE_RUN_CONFIRMATION: Must be set to 'true' to execute live discovery requests.
- Zero paid credit consumption in test / dry-run mode.
- Masked credentials for audit logging.
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from src.icp.icp_models import DeeplineDiscoveryRequest
from src.integrations.claude_client import load_env_file_if_present


class DeeplineAuthError(Exception):
    """Raised when Deepline API authentication fails (HTTP 401/403)."""
    pass


class DeeplineAPIError(Exception):
    """Raised when Deepline returns a non-200 response or network fails."""
    pass


class DeeplineClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        live_mode: Optional[bool] = None,
    ):
        load_env_file_if_present()

        self.api_key = api_key or os.getenv("DEEPLINE_API_KEY", "")
        self.base_url = (base_url or os.getenv("DEEPLINE_BASE_URL", "https://api.deepline.ai/v1")).rstrip("/")
        
        env_live = os.getenv("DEEPLINE_LIVE", "false").lower() in ("true", "1", "yes")
        self.live_mode = live_mode if live_mode is not None else env_live
        
        self.run_confirmed = os.getenv("DEEPLINE_RUN_CONFIRMATION", "false").lower() in ("true", "1", "yes")

    @classmethod
    def mask_api_key(cls, key: Optional[str]) -> str:
        """Returns safely masked API key for logging (e.g. ************7890)."""
        if not key:
            return "NOT_CONFIGURED"
        if len(key) <= 8:
            return "********"
        return f"{'*' * (len(key) - 4)}{key[-4:]}"

    def discover_leads(self, request: DeeplineDiscoveryRequest) -> Dict[str, Any]:
        """
        Executes lead discovery against Deepline.
        In dry-run mode or when DEEPLINE_LIVE=false, returns high-fidelity simulated contractor leads.
        """
        if not self.live_mode:
            return self._generate_simulated_discovery(request)

        # Strict safety check for live mode
        if not self.api_key:
            raise DeeplineAuthError("DEEPLINE_API_KEY is required when DEEPLINE_LIVE=true.")

        if not self.run_confirmed:
            raise DeeplineAPIError(
                "Live discovery blocked: DEEPLINE_RUN_CONFIRMATION must be set to 'true' to execute live discovery."
            )

        endpoint = f"{self.base_url}/leads/discover"
        payload_bytes = json.dumps(request.model_dump()).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Aedrix-ColdOutreach-DeeplineClient/1.0",
        }

        req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30.0) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise DeeplineAuthError(f"Deepline Authentication Failed: HTTP {e.code}")
            raise DeeplineAPIError(f"Deepline API Error: HTTP {e.code} - {e.reason}")
        except Exception as e:
            raise DeeplineAPIError(f"Deepline Network Error: {str(e)}")

    def _generate_simulated_discovery(self, request: DeeplineDiscoveryRequest) -> Dict[str, Any]:
        """Generates realistic simulated research contractor leads conforming to the discovery request."""
        count = request.requested_lead_count
        companies = [
            ("Balfour Beatty plc", "balfourbeatty.com", "Tier-1 Main Contractor", "London, UK", 24000, 8900.0, "Jon Ozanne", "Chief Information Officer", "j.ozanne@balfourbeatty.com", "EVIDENCE_VERIFIED", "Expanding digital pre-construction workflows across multi-site UK rail & commercial projects."),
            ("Kier Group plc", "kier.co.uk", "Regional & National Main Contractor", "Manchester, UK", 11000, 3400.0, "Colin Bell", "Digital Director", "c.bell@kier.co.uk", "EVIDENCE_VERIFIED", "Launched 'Digital by Default' roadmap prioritizing drawing versioning and subcontractor management."),
            ("Bowmer & Kirkland", "bandk.co.uk", "Main Building Contractor", "Belper, Derbyshire, UK", 1500, 1100.0, "John Foster", "Business Improvement Director", "j.foster@bandk.co.uk", "PATTERN_CONFIRMED", "Recruiting dedicated digital construction leads across regional offices to reduce document turnaround."),
            ("Laing O'Rourke", "laingorourke.com", "Engineering & Construction Enterprise", "Dartford, UK", 12000, 4100.0, "Adrian Spragg", "Head of Digital Transformation", "a.spragg@laingorourke.com", "EVIDENCE_VERIFIED", "Deploying advanced site data capture and modular tracking to streamline labor productivity."),
            ("Morgan Sindall Group plc", "morgansindall.com", "Construction & Infrastructure", "London, UK", 6700, 3600.0, "Lee Ramsey", "Digital Construction Director", "l.ramsey@morgansindall.com", "PATTERN_CONFIRMED", "Integrating commercial governance and pre-construction document approval workflows."),
            ("Wates Group", "wates.co.uk", "Construction & Property Services", "Leatherhead, UK", 4000, 1800.0, "David Clark", "Head of IT Operations", "d.clark@wates.co.uk", "EVIDENCE_VERIFIED", "Evaluating cloud-first site logistics and drawing collaboration systems."),
            ("Willmott Dixon", "willmottdixon.co.uk", "Main Building Contractor", "Letchworth, UK", 2300, 1200.0, "Mark French", "Chief Information Officer", "m.french@willmottdixon.co.uk", "PATTERN_CONFIRMED", "Focused on site carbon reduction and eliminating administrative project lag."),
            ("Mace Group", "macegroup.com", "Global Construction & Consultancy", "London, UK", 7300, 2000.0, "Stephen Jeffrey", "Chief Technical Officer", "s.jeffrey@macegroup.com", "EVIDENCE_VERIFIED", "Standardizing international pre-construction governance and real-time site metrics."),
            ("Sir Robert McAlpine", "srm.com", "Civil Engineering & Building", "Hemel Hempstead, UK", 1800, 950.0, "Karen Brookes", "Director of People & Operations", "k.brookes@srm.com", "PATTERN_CONFIRMED", "Driving digital site onboarding and multi-contractor collaboration."),
            ("ISG Ltd", "isgltd.com", "Fit-Out & Construction Services", "London, UK", 2800, 1400.0, "Richard Gould", "Head of Digital Delivery", "r.gould@isgltd.com", "EVIDENCE_VERIFIED", "Standardizing subcontractor drawing version control across fast-track commercial fitouts.")
        ]

        leads = []
        for i in range(count):
            base_co = companies[i % len(companies)]
            co_name = base_co[0] if i < len(companies) else f"{base_co[0]} - Division {i // len(companies) + 1}"
            domain = base_co[1]
            first_name, last_name = base_co[6].split(" ", 1)
            email_local = f"{first_name[0].lower()}.{last_name.lower()}{i if i >= len(companies) else ''}@{domain}"

            # Simulate small percentage of realistic edge cases (10% hard disquals, 5% exclusions)
            if i % 17 == 0 and i > 0:
                is_uk = False
                country = "France"
            else:
                is_uk = True
                country = "United Kingdom"

            if i % 23 == 0 and i > 0:
                is_const = False
                ind = "Pure Software Vendor"
            else:
                is_const = True
                ind = request.industries[0] if request.industries else "Commercial Construction"

            leads.append({
                "company_name": co_name,
                "company_domain": domain,
                "company_location": country,
                "country": country,
                "is_uk_operating": is_uk,
                "industry": ind,
                "is_construction_sector": is_const,
                "construction_type": "Main Contractor",
                "employee_count": base_co[4],
                "company_size": f"{base_co[4]} employees",
                "company_size_evidence": "VERIFIED",
                "revenue": f"£{base_co[5]}M",
                "contact_name": f"{first_name} {last_name}",
                "job_title": base_co[7],
                "email": email_local,
                "email_status": base_co[9],
                "linkedin_url": f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}",
                "relevant_signal": base_co[10],
                "relevant_signal_evidence": "VERIFIED",
                "pain_point": "Subcontractor document versioning delays and disconnected site manpower tracking.",
                "pain_point_evidence": "INFERRED",
                "is_active_crm_deal": (i % 31 == 0 and i > 0),
                "is_global_suppressed": False,
                "contacted_within_60_days": False
            })

        return {
            "status": "SUCCESS",
            "mode": "DRY_RUN_SIMULATION",
            "icp_id": request.icp_id,
            "campaign_id": request.campaign_id,
            "requested_count": count,
            "discovered_count": len(leads),
            "leads": leads,
            "api_calls_made": 0,
            "credits_consumed": 0
        }
