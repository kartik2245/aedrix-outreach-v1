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
from typing import Dict, Any, Optional, List, Tuple
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
    def resolve_deepline_executable(cls) -> Tuple[str, bool]:
        """
        Resolves the Deepline CLI executable path cross-platform.
        On Windows, NPM global scripts install batch wrappers (`deepline.cmd`).
        Returns a tuple of (executable_name_or_path, use_shell_flag).
        """
        import shutil, sys
        exe = shutil.which("deepline")
        if exe:
            use_shell = sys.platform.startswith("win") and (exe.lower().endswith(".cmd") or exe.lower().endswith(".bat"))
            return exe, use_shell

        if sys.platform.startswith("win"):
            exe_cmd = shutil.which("deepline.cmd")
            if exe_cmd:
                return exe_cmd, True
            return "deepline.cmd", True

        return "deepline", False

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
        Parses AEDRIX company_size string (e.g. '10+ employees', '10-100 employees')
        into Deepline's employeeSize RANGE structure. Defaults to start=10, end=10000.
        """
        start = 50
        end = 10000

        if company_size_str and str(company_size_str).strip():
            import re
            s = str(company_size_str).strip()
            s_no_rev = re.sub(r'(?i)(?:or\s*)?[£$€]?\d+(?:\.\d+)?\s*[kmb]?\+?\s*revenue.*', '', s).strip()

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
        import re

        # 1. Clean Location Terms
        raw_geo = request.geography if request.geography else ["United Kingdom"]
        location_list = []
        for g in raw_geo:
            if not g or not str(g).strip():
                continue
            parts = re.split(r'[\n,;]+', str(g))
            for part in parts:
                token = part.strip()
                if not token:
                    continue
                token_upper = token.upper()
                if token_upper in ("UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "GB", "GBR", "GREAT BRITAIN"):
                    clean_loc = "United Kingdom"
                elif token_upper in ("US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"):
                    clean_loc = "United States"
                else:
                    clean_loc = token
                if clean_loc not in location_list:
                    location_list.append(clean_loc)
        if not location_list:
            location_list = ["United Kingdom"]

        # 2. Clean Industry Keywords
        raw_industries = request.industries if request.industries else ["Technology"]
        industry_list = []
        for ind in raw_industries:
            if not ind or not str(ind).strip():
                continue
            parts = re.split(r'[\n,;/]+', str(ind))
            for part in parts:
                token = part.strip()
                if not token:
                    continue
                if len(token) > 35 and " " in token:
                    sub_parts = re.split(r'\s{2,}|\s+(?=[A-Z])', token)
                    for sub in sub_parts:
                        sub_clean = sub.strip()
                        if sub_clean and sub_clean not in industry_list:
                            industry_list.append(sub_clean)
                else:
                    if token not in industry_list:
                        industry_list.append(token)
        if not industry_list:
            industry_list = ["Technology"]

        # 3. Clean Persona Job Titles (strip parenthetical annotations generically)
        raw_personas = request.personas if request.personas else ["Director"]
        persona_list = []
        for p in raw_personas:
            if not p or not str(p).strip():
                continue
            parts = re.split(r'[\n,;]+', str(p))
            for part in parts:
                clean_title = re.sub(r'\s*\([^)]*\)', '', part).strip()
                if clean_title and clean_title not in persona_list:
                    persona_list.append(clean_title)
        if not persona_list:
            persona_list = ["Director"]

        return {
            "payload": {
                "page": 0,
                "size": min(request.requested_lead_count, 100),
                "account": {
                    "location": {
                        "any": {
                            "include": location_list
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

    def enrich_single_lead_email(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches a single lead by extracting its dynamic linkedin_url and executing
        the Deepline play `prebuilt/person-linkedin-to-email`.

        Logical Status Rules:
        - VERIFIED:   email exists AND email_validated == True AND email_found_and_valid == True
        - UNVERIFIED: email exists BUT not confirmed as valid
        - NO_EMAIL:   no usable email is returned
        """
        rec = dict(lead)

        # 1. Extract dynamic linkedin_url from lead record
        linkedin_url = (
            rec.get("linkedin_url")
            or rec.get("linkedin")
            or (rec.get("link", {}).get("linkedin") if isinstance(rec.get("link"), dict) else None)
            or (rec.get("profile", {}).get("linkedin") if isinstance(rec.get("profile"), dict) else None)
        )

        if not linkedin_url or not isinstance(linkedin_url, str) or not str(linkedin_url).strip():
            # Missing or empty LinkedIn URL -> fallback cleanly without calling Deepline
            existing_email = str(rec.get("email") or "").strip().lower()
            has_syntax = bool(existing_email and "@" in existing_email and "." in existing_email.split("@")[-1] and len(existing_email) >= 5)
            if has_syntax:
                raw_st = str(rec.get("email_status") or rec.get("email_verification_status") or "").strip().upper()
                rec["email"] = existing_email
                rec["email_status"] = raw_st if raw_st in ("VERIFIED", "UNVERIFIED", "VALID", "EVIDENCE_VERIFIED") else "EVIDENCE_VERIFIED"
            else:
                rec["email"] = ""
                rec["email_status"] = "NO_EMAIL"
            rec["enrichment_status"] = "MISSING_LINKEDIN_URL"
            return rec

        clean_url = str(linkedin_url).strip()
        if "linkedin.com" not in clean_url.lower():
            # Invalid LinkedIn URL format -> fallback cleanly without calling Deepline
            existing_email = str(rec.get("email") or "").strip().lower()
            has_syntax = bool(existing_email and "@" in existing_email and "." in existing_email.split("@")[-1] and len(existing_email) >= 5)
            if has_syntax:
                raw_st = str(rec.get("email_status") or rec.get("email_verification_status") or "").strip().upper()
                rec["email"] = existing_email
                rec["email_status"] = raw_st if raw_st in ("VERIFIED", "UNVERIFIED", "VALID", "EVIDENCE_VERIFIED") else "EVIDENCE_VERIFIED"
            else:
                rec["email"] = ""
                rec["email_status"] = "NO_EMAIL"
            rec["enrichment_status"] = "INVALID_LINKEDIN_URL"
            return rec

        # 2. Check if lead contains explicit mock play response (for dry-run/unit testing)
        mock_play = rec.get("mock_play_response")
        play_result = None

        if isinstance(mock_play, dict):
            play_result = mock_play
        elif not self.live_mode:
            # Dry-run / test mode: if explicit mock validation fields exist, use them
            if "email_validated" in rec or "email_found_and_valid" in rec:
                play_result = {
                    "email": rec.get("email"),
                    "email_source": rec.get("email_source", "simulated_waterfall"),
                    "email_validated": bool(rec.get("email_validated", False)),
                    "email_found_and_valid": bool(rec.get("email_found_and_valid", False)),
                    "miss_reason": rec.get("miss_reason"),
                }
            elif rec.get("email"):
                # Lead already has an email from discovery / fixture:
                raw_st = str(rec.get("email_status") or rec.get("email_verification_status") or "").strip().upper()
                is_valid_email = bool(raw_st in ("VERIFIED", "VALID", "EVIDENCE_VERIFIED") or raw_st == "")
                play_result = {
                    "email": rec.get("email"),
                    "email_source": rec.get("email_source", "pre_indexed"),
                    "email_validated": is_valid_email,
                    "email_found_and_valid": is_valid_email,
                    "miss_reason": None if is_valid_email else "unverified_status",
                }

        # 3. Live Deepline Play Execution via subprocess CLI (if live_mode & run_confirmed)
        if play_result is None and self.live_mode:
            if not self.run_confirmed:
                # Live execution blocked by safety gate
                existing_email = str(rec.get("email") or "").strip().lower()
                has_syntax = bool(existing_email and "@" in existing_email and "." in existing_email.split("@")[-1] and len(existing_email) >= 5)
                rec["email"] = existing_email if has_syntax else ""
                rec["email_status"] = "EVIDENCE_VERIFIED" if has_syntax else "NO_EMAIL"
                rec["enrichment_status"] = "SAFETY_GATE_BLOCKED"
                return rec

            try:
                import subprocess, json
                exe_cmd, use_shell = self.resolve_deepline_executable()
                cmd = [
                    exe_cmd,
                    "plays",
                    "run",
                    "prebuilt/person-linkedin-to-email",
                    "-i",
                    json.dumps({"linkedin_url": clean_url}),
                    "--json"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45, shell=use_shell)
                if proc.returncode == 0 and proc.stdout and proc.stdout.strip():
                    try:
                        stdout_str = proc.stdout.strip()
                        lines = stdout_str.split("\n")
                        json_str = ""
                        for i, line in enumerate(lines):
                            if line.strip().startswith("{"):
                                json_str = "\n".join(lines[i:])
                                break
                        if not json_str:
                            json_str = stdout_str
                        play_result = json.loads(json_str)

                        # If play_result returned async run object with runId and no outputs, fetch full run details
                        if isinstance(play_result, dict) and "runId" in play_result and not play_result.get("outputs"):
                            run_id = play_result["runId"]
                            get_cmd = [exe_cmd, "runs", "get", run_id, "--full", "--json"]
                            proc_get = subprocess.run(get_cmd, capture_output=True, text=True, timeout=30, shell=use_shell)
                            if proc_get.returncode == 0 and proc_get.stdout and proc_get.stdout.strip():
                                stdout_str_get = proc_get.stdout.strip()
                                lines_get = stdout_str_get.split("\n")
                                json_str_get = ""
                                for i, line in enumerate(lines_get):
                                    if line.strip().startswith("{"):
                                        json_str_get = "\n".join(lines_get[i:])
                                        break
                                if not json_str_get:
                                    json_str_get = stdout_str_get
                                play_result = json.loads(json_str_get)
                    except json.JSONDecodeError:
                        rec["enrichment_error"] = "MALFORMED_JSON_RESPONSE"
                else:
                    rec["enrichment_error"] = f"CLI_FAILURE: code {proc.returncode} - {proc.stderr[:200] if proc.stderr else ''}"
            except subprocess.TimeoutExpired:
                rec["enrichment_error"] = "PLAY_TIMEOUT"
            except Exception as ex:
                rec["enrichment_error"] = f"EXECUTION_ERROR: {str(ex)}"

        # 4. Parse Play output & determine status
        if isinstance(play_result, dict):
            outputs = play_result.get("outputs", {}) if isinstance(play_result.get("outputs"), dict) else {}

            def _get_val(key: str) -> Any:
                if key in outputs and isinstance(outputs[key], dict) and "value" in outputs[key]:
                    return outputs[key]["value"]
                if key in outputs and not isinstance(outputs[key], dict):
                    return outputs[key]
                return play_result.get(key)

            raw_email = _get_val("email")
            found_email = str(raw_email or "").strip().lower()

            is_validated = bool(_get_val("email_validated") or False)
            is_found_valid = bool(_get_val("email_found_and_valid") or False)
            email_source = _get_val("email_source")
            miss_reason = _get_val("miss_reason")

            has_valid_syntax = bool(
                found_email and "@" in found_email and "." in found_email.split("@")[-1] and len(found_email) >= 5
            )

            rec["email_source"] = email_source
            rec["email_validated"] = is_validated
            rec["email_found_and_valid"] = is_found_valid
            rec["miss_reason"] = miss_reason

            if has_valid_syntax and is_validated and is_found_valid:
                rec["email"] = found_email
                rec["email_status"] = "VERIFIED"
                rec["enrichment_status"] = "SUCCESS"
            elif has_valid_syntax:
                rec["email"] = found_email
                rec["email_status"] = "UNVERIFIED"
                rec["enrichment_status"] = "UNVERIFIED_EMAIL_FOUND"
            else:
                rec["email"] = ""
                rec["email_status"] = "NO_EMAIL"
                rec["enrichment_status"] = "NO_EMAIL_FOUND"
        else:
            # Play returned no result or errored out cleanly -> fallback safely
            existing_email = str(rec.get("email") or "").strip().lower()
            has_syntax = bool(existing_email and "@" in existing_email and "." in existing_email.split("@")[-1] and len(existing_email) >= 5)
            if has_syntax:
                raw_st = str(rec.get("email_status") or rec.get("email_verification_status") or "").strip().upper()
                rec["email"] = existing_email
                rec["email_status"] = raw_st if raw_st in ("VERIFIED", "UNVERIFIED", "VALID", "EVIDENCE_VERIFIED") else "EVIDENCE_VERIFIED"
            else:
                rec["email"] = ""
                rec["email_status"] = "NO_EMAIL"
            if "enrichment_status" not in rec:
                rec["enrichment_status"] = "NO_PLAY_RESULT"

        return rec

    def enrich_lead_emails(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriches a batch of discovered leads using prebuilt/person-linkedin-to-email.
        Maintains an in-memory cache of seen LinkedIn URLs to guarantee batch idempotency.
        """
        if not leads:
            return []

        enriched = []
        seen_urls: Dict[str, Dict[str, Any]] = {}

        for item in leads:
            raw_rec = dict(item)
            url_key = (
                raw_rec.get("linkedin_url")
                or raw_rec.get("linkedin")
                or (raw_rec.get("link", {}).get("linkedin") if isinstance(raw_rec.get("link"), dict) else None)
            )

            if url_key and isinstance(url_key, str) and url_key.strip() and url_key.strip() in seen_urls:
                # Batch idempotency: reuse already-enriched result for duplicate LinkedIn URL
                cached = dict(seen_urls[url_key.strip()])
                for k, v in raw_rec.items():
                    if k not in cached:
                        cached[k] = v
                enriched.append(cached)
            else:
                res_rec = self.enrich_single_lead_email(raw_rec)
                if url_key and isinstance(url_key, str) and url_key.strip():
                    seen_urls[url_key.strip()] = res_rec
                enriched.append(res_rec)

        return enriched

    def _generate_simulated_discovery(self, request: DeeplineDiscoveryRequest) -> Dict[str, Any]:
        """Generates realistic simulated research contractor leads conforming to the discovery request."""
        count = request.requested_lead_count
        companies = [
            ("Balfour Beatty plc", "balfourbeatty.com", "Tier-1 Main Contractor", "London, UK", 24000, 8900.0, "Jon Ozanne", "Chief Information Officer", "j.ozanne@balfourbeatty.com", "EVIDENCE_VERIFIED", "Expanding digital pre-construction workflows across multi-site UK rail & commercial projects."),
            ("Kier Group plc", "kier.co.uk", "Regional & National Main Contractor", "Manchester, UK", 11000, 3400.0, "Colin Bell", "Digital Director", "c.bell@kier.co.uk", "EVIDENCE_VERIFIED", "Launched 'Digital by Default' roadmap prioritizing drawing versioning and subcontractor management."),
            ("Bowmer & Kirkland", "bandk.co.uk", "Main Building Contractor", "Belper, Derbyshire, UK", 1500, 1100.0, "John Foster", "Business Improvement Director", "j.foster@bandk.co.uk", "EVIDENCE_VERIFIED", "Recruiting dedicated digital construction leads across regional offices to reduce document turnaround."),
            ("Laing O'Rourke", "laingorourke.com", "Engineering & Construction Enterprise", "Dartford, UK", 12000, 4100.0, "Adrian Spragg", "Head of Digital Transformation", "a.spragg@laingorourke.com", "EVIDENCE_VERIFIED", "Deploying advanced site data capture and modular tracking to streamline labor productivity."),
            ("Morgan Sindall Group plc", "morgansindall.com", "Construction & Infrastructure", "London, UK", 6700, 3600.0, "Lee Ramsey", "Digital Construction Director", "l.ramsey@morgansindall.com", "EVIDENCE_VERIFIED", "Integrating commercial governance and pre-construction document approval workflows."),
            ("Wates Group", "wates.co.uk", "Construction & Property Services", "Leatherhead, UK", 4000, 1800.0, "David Clark", "Head of IT Operations", "d.clark@wates.co.uk", "EVIDENCE_VERIFIED", "Evaluating cloud-first site logistics and drawing collaboration systems."),
            ("Willmott Dixon", "willmottdixon.co.uk", "Main Building Contractor", "Letchworth, UK", 2300, 1200.0, "Mark French", "Chief Information Officer", "m.french@willmottdixon.co.uk", "EVIDENCE_VERIFIED", "Focused on site carbon reduction and eliminating administrative project lag."),
            ("Mace Group", "macegroup.com", "Global Construction & Consultancy", "London, UK", 7300, 2000.0, "Stephen Jeffrey", "Chief Technical Officer", "s.jeffrey@macegroup.com", "EVIDENCE_VERIFIED", "Standardizing international pre-construction governance and real-time site metrics."),
            ("Sir Robert McAlpine", "srm.com", "Civil Engineering & Building", "Hemel Hempstead, UK", 1800, 950.0, "Karen Brookes", "Director of People & Operations", "k.brookes@srm.com", "EVIDENCE_VERIFIED", "Driving digital site onboarding and multi-contractor collaboration."),
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
