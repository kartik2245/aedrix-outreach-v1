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

        self.api_key = api_key or os.getenv("DEEPLINE_API_KEY", "") or os.getenv("DEEPLINE_SESSION_TOKEN", "")
        self.base_url = (base_url or os.getenv("DEEPLINE_BASE_URL", "https://code.deepline.com/api/v2")).rstrip("/")
        self.v2_tool = os.getenv("DEEPLINE_V2_TOOL", "ai_ark_people_search")
        
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

    def parse_employee_range(self, company_size_str: Optional[str]) -> Dict[str, Any]:
        """
        Parses AEDRIX company_size string (e.g. '50+ employees', '50-500 employees', '50+ employees or £10M+ revenue')
        into Deepline's employeeSize RANGE structure. Defaults to start=50, end=10000.
        """
        start = 50
        end = 10000

        if company_size_str and str(company_size_str).strip():
            import re
            s = str(company_size_str).strip()
            # Strip revenue clause if present (e.g. 'or £10M+ revenue', 'or 10M revenue')
            s_no_rev = re.sub(r'(?i)(?:or\s*)?[£$€]?\d+(?:\.\d+)?\s*[kmb]?\+?\s*revenue.*', '', s).strip()

            # Check for range pattern: "50-500", "50 to 500"
            range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)', s_no_rev, re.IGNORECASE)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
            else:
                emp_match = re.search(r'(\d+)', s_no_rev)
                if emp_match:
                    start = int(emp_match.group(1))
                    end = 10000

        return {
            "type": "RANGE",
            "range": [
                {
                    "start": start,
                    "end": end
                }
            ]
        }

    def build_v2_payload(self, request: DeeplineDiscoveryRequest) -> Dict[str, Any]:
        """Maps AEDRIX ICP Discovery Request into official Deepline V2 ai_ark_people_search tool payload wrapper."""
        raw_geo = request.geography if request.geography else ["United Kingdom"]
        country_list = []
        for g in raw_geo:
            g_upper = g.upper()
            if g_upper in ("UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB", "GBR"):
                if "United Kingdom" not in country_list:
                    country_list.append("United Kingdom")
            elif g not in country_list:
                country_list.append(g)
        if not country_list:
            country_list = ["United Kingdom"]

        industry_list = request.industries if request.industries else ["Commercial Construction"]
        persona_list = request.personas if request.personas else ["Director"]

        return {
            "payload": {
                "page": 0,
                "size": min(request.requested_lead_count, 100),
                "account": {
                    "location": {
                        "any": {
                            "include": country_list
                        }
                    },
                    "employeeSize": self.parse_employee_range(request.company_size),
                    "keyword": {
                        "any": {
                            "include": {
                                "content": industry_list,
                                "sources": [
                                    {
                                        "mode": "SMART",
                                        "source": "INDUSTRY"
                                    }
                                ]
                            }
                        }
                    }
                },
                "contact": {
                    "keyword": {
                        "any": {
                            "include": {
                                "content": persona_list,
                                "sources": [
                                    {
                                        "mode": "SMART",
                                        "source": "HEADLINE"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

    def discover_leads(self, request: DeeplineDiscoveryRequest) -> Dict[str, Any]:
        """
        Executes lead discovery against Deepline V2.
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

        if "/v1" in self.base_url:
            endpoint = f"{self.base_url}/leads/discover"
            v2_payload = request.model_dump()
        else:
            endpoint = f"{self.base_url}/integrations/{self.v2_tool}/execute"
            v2_payload = self.build_v2_payload(request)

        payload_bytes = json.dumps(v2_payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Aedrix-ColdOutreach-DeeplineClient/2.0",
            "x-deepline-execute-response-contract": "v2-tool-response",
            "x-deepline-tool-error-schema": "1",
            "x-deepline-execute-response-intent": "raw",
        }

        req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30.0) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                
                # Extract leads array from V2 tool output or legacy wrapper
                leads_extracted = []
                if isinstance(data, dict):
                    if "leads" in data and isinstance(data["leads"], list):
                        leads_extracted = data["leads"]
                    elif "toolResponse" in data and isinstance(data["toolResponse"], dict):
                        raw = data["toolResponse"].get("raw", {})
                        if isinstance(raw, dict) and "content" in raw and isinstance(raw["content"], list):
                            leads_extracted = raw["content"]
                        elif "content" in data["toolResponse"] and isinstance(data["toolResponse"]["content"], list):
                            leads_extracted = data["toolResponse"]["content"]
                    elif "toolExecutionResult" in data:
                        extracted = data.get("toolExecutionResult", {}).get("extractedLists", [])
                        if isinstance(extracted, list) and extracted:
                            leads_extracted = extracted[0].get("items", [])
                    elif "result" in data and isinstance(data["result"], dict):
                        if "content" in data["result"] and isinstance(data["result"]["content"], list):
                            leads_extracted = data["result"]["content"]
                    elif "content" in data and isinstance(data["content"], list):
                        leads_extracted = data["content"]

                return {
                    "status": "SUCCESS",
                    "mode": "LIVE_API_V2",
                    "icp_id": request.icp_id,
                    "campaign_id": request.campaign_id,
                    "requested_count": request.requested_lead_count,
                    "discovered_count": len(leads_extracted),
                    "leads": leads_extracted,
                    "raw_response": data,
                    "api_calls_made": 1,
                    "credits_consumed": round(len(leads_extracted) * 0.07, 3),
                }
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code in (401, 403):
                raise DeeplineAuthError(f"Deepline Authentication Failed: HTTP {e.code} - {error_body}")

            error_msg = f"Deepline API Error: HTTP {e.code} - {e.reason}"
            if error_body:
                error_msg += f" - Response Body: {error_body}"
            raise DeeplineAPIError(error_msg)
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
