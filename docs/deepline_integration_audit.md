# Deepline Technical Integration Audit & Credit Safety Analysis (Phase 3)

This audit report documents the technical capabilities, credit safety parameters, data mapping contracts, and integration architecture for connecting **Deepline / Apollo GTM tools** into the **Aedrix Lead Intelligence Layer**.

> **SAFETY NOTICE**: No paid APIs were called, zero credits were spent, and zero live connections were established during this audit.

---

## A. Available Deepline Capabilities

* **CLI Infrastructure**: Deepline CLI `v0.2.46` installed globally and authenticated (`preflight` status: `claimed`, 25 Deepline Credits active).
* **Provider Catalog**: Access to 707 atomic GTM tools across 40+ providers including Apollo, AI Ark, Lusha, LimaData, Hunter, Apify, AdYntel, Exa/Google Search.
* **Play Runner**: TypeScript workflow runner (`definePlay`) with state persistence, dataset transforms, and retry management.
* **Structured Output Engine**: Native JSON output support (`--json` flag) across all CLI inspection and execution commands.

---

## B. Apollo Capabilities Exposed Through Deepline

1. **`apollo_company_search`**:
   - **Capabilities**: Search global company database by domain list (`q_organization_domains_list`), company name (`q_organization_name`), location (`organization_locations`), employee count ranges (`organization_num_employees_ranges`), revenue range (`revenue_range`), industry tag IDs (`organization_industry_tag_ids`), and hiring titles (`q_organization_job_titles`).
   - **Credentials**: Requires personal Apollo API key configured in workspace settings.

2. **`apollo_search_people` (Free Preview Mode)**:
   - **Capabilities**: People discovery preview filtering by `person_titles`, `person_seniorities` (`c_suite`, `head`, `director`, `vp`), `person_locations` (`UK`), `organization_locations`, and employee ranges.
   - **Credit Impact**: **0 Apollo credits** / **0 Deepline credits**. Intentionally obfuscates last names to prevent uncredited extraction.

3. **`apollo_search_people_with_match` (Full Identity Mode)**:
   - **Capabilities**: People discovery with automatic bulk-match enrichment returning full matched names, emails, titles, and LinkedIn profiles.
   - **Credit Impact**: **Consumes Apollo / Deepline credits**.

4. **`apollo_organization_enrich` / `apollo_bulk_organization_enrichment`**:
   - **Capabilities**: Enriches full company profile from a domain name.

5. **`apollo_people_match` / `apollo_reveal_person`**:
   - **Capabilities**: Resolves single person identity into a verified email address and LinkedIn profile.

6. **`apollo_news_articles_search`**:
   - **Capabilities**: Searches recent company news articles for digital transformation signals (Consumes **1 Apollo credit per page**).

---

## C. Available Research Fields (Company Level)

| Research Field | Availability in Deepline/Apollo | Field Status |
| :--- | :--- | :--- |
| `company_name` | Direct match from `organization_name` / `name` | **VERIFIED** |
| `company_domain` | Direct match from `primary_domain` / `domain` | **VERIFIED** |
| `company_location` | HQ location from `organization_locations` | **VERIFIED** |
| `industry` | Primary industry tag from `industry_tag_hash` | **VERIFIED** |
| `company_size` | Employee count range from `organization_num_employees_ranges` | **ESTIMATED** |
| `digital_transformation_signals` | News search `apollo_news_articles_search` / Job postings `q_organization_job_titles` | **VERIFIED** (if URL present) |
| `leadership_changes` | News & executive appointment press releases | **VERIFIED** (if URL present) |

---

## D. Available Contact / Decision-Maker Fields (Person Level)

| Contact Field | Availability in Deepline/Apollo | Field Status |
| :--- | :--- | :--- |
| Target Titles (*CIO, Digital Director, IT Director, Head of Digital Construction, Business Improvement Director*) | Matched via `person_titles` & `person_seniorities` | **VERIFIED** |
| `contact_name` | `first_name` + `last_name` from `apollo_search_people_with_match` | **VERIFIED** |
| `job_title` | `title` from Apollo person profile | **VERIFIED** |
| `email` | `email` from Apollo contact record | **VERIFIED** / `PATTERN_CONFIRMED` |
| `email_status` | `contact_email_status` (`verified` / `guessed`) | **VERIFIED** |
| `linkedin_url` | `linkedin_url` / `linkedin` | **VERIFIED** |

---

## E. Credit & Usage Risks

* **Current Balance**: Workspace currently holds **25 Deepline Credits** ($2.50 USD value).
* **Credential Dependency**: Deepline **does not provide platform-managed Apollo API keys**. All Apollo operations require the user's personal API key.
* **Credit-Consuming Operations**:
  - `apollo_search_people_with_match` & `apollo_people_match`: Consumes Apollo enrichment credits per contact revealed.
  - `apollo_news_articles_search`: Consumes 1 Apollo credit per page (up to 25 news results).
  - Third-party enrichments (e.g. Lusha: 0.7 credits/result, LimaData: 0.28-0.56 credits/call).

---

## F. Credit Safety & Permission Matrix

| Operation | Available in CLI? | Requires Personal Credentials? | Credits Required? | Safe to Test Now? |
| :--- | :---: | :---: | :---: | :---: |
| `deepline preflight` / `doctor` | Yes | No | 0 Credits | **YES (Free)** |
| `deepline tools list` / `search` / `describe` | Yes | No | 0 Credits | **YES (Free)** |
| `deepline plays search` / `describe` | Yes | No | 0 Credits | **YES (Free)** |
| `apollo_company_search` | Yes | Own Apollo Key | 0 Deepline Credits (Check Apollo Plan) | **NO (Needs Key & Approval)** |
| `apollo_search_people` (Preview) | Yes | Own Apollo Key | 0 Apollo Credits (Obfuscated Last Names) | **NO (Needs Key & Approval)** |
| `apollo_search_people_with_match` | Yes | Own Apollo Key | **Consumes Apollo Credits** | **NO (Paid Operation)** |
| `apollo_organization_enrich` | Yes | Own Apollo Key | 0-1 Credits | **NO (Needs Approval)** |
| `apollo_people_match` / `reveal_person` | Yes | Own Apollo Key | **Consumes Apollo Credits** | **NO (Paid Operation)** |
| `apollo_news_articles_search` | Yes | Own Apollo Key | **1 Apollo Credit per page** | **NO (Paid Operation)** |

---

## G. Recommended Integration Architecture

```text
Deepline Play / CLI Export (JSON)
          ↓
File Buffer: data/research_leads.json
          ↓
Research Normalizer (src/research_normalizer.js)
          ↓
Evidence Validator (src/evidence_validator.js)
          ↓
Lead Intelligence Engine (src/lead_intelligence.js)
          ↓
Output Dataset: data/final_lead_intelligence.json
          ↓
n8n Orchestration → Claude AI Copy Generator → Smartlead ESP Simulator
```

**Why CLI JSON File Buffer Integration?**
1. **Zero Risk**: Ensures complete human or policy inspection before passing records into scoring and outreach.
2. **Audit Compliance**: Allows `EvidenceValidator` to audit every field and enforce `NO_STRONG_SIGNAL` fallbacks before any campaign enrollment.
3. **Decoupled Architecture**: Keeps API discovery separate from lead intelligence scoring.

---

## H. Exact Data Mapping to Lead Intelligence Schema

| Deepline / Apollo Source Field | Target Field in `lead_schema.json` | Evidence Level Rule |
| :--- | :--- | :--- |
| `organization_name` / `name` | `company_name` | `VERIFIED` |
| `primary_domain` / `domain` | `company_domain` | `VERIFIED` |
| `organization_locations[0]` | `company_location` | `VERIFIED` |
| `industry` / `industry_tag_hash` | `industry` | `VERIFIED` |
| `organization_num_employees_ranges` | `company_size` | `ESTIMATED` |
| `full_name` (`first_name` + `last_name`) | `contact_name` | `VERIFIED` |
| `title` | `job_title` | `VERIFIED` |
| `email` | `email` | `EVIDENCE_VERIFIED` / `PATTERN_CONFIRMED` |
| `linkedin_url` / `linkedin` | `linkedin_url` | `VERIFIED` |
| `news_articles` / `job_postings` | `research_signals` | `VERIFIED` (if URL present) else `INFERRED` |
| `article_url` / `source_url` | `research_sources` | `VERIFIED` |
| Derived from sources | `evidence_levels` | `VERIFIED` / `ESTIMATED` / `INFERRED` / `UNKNOWN` |
| Computed by `LeadIntelligenceEngine` | `opportunity_score` | Calculated (0-100) |
| Computed by `LeadIntelligenceEngine` | `accessibility_score` | Calculated (0-100) |
| Computed by `LeadIntelligenceEngine` | `outreach_priority_index` | Calculated (0.60*Opp + 0.40*Acc) |
| Computed by `LeadIntelligenceEngine` | `priority` | `P1` / `P2` / `P3` |
| Computed by `LeadIntelligenceEngine` | `qualification_status` | `QUALIFIED` / `CAMPAIGN_EXCLUDED` / `HARD_DISQUALIFIED` |
| Computed by `LeadIntelligenceEngine` | `campaign_exclusion_reason` | Reason string or `null` |
| `contact_email_status` (`verified` / `guessed`) | `email_status` | `EVIDENCE_VERIFIED` / `PATTERN_CONFIRMED` |
| Generated by Personalization Engine | `personalization_note` | 2-sentence note or Baseline Fallback |
| Evaluated by Personalization Engine | `personalization_note_status` | `SIGNAL_VERIFIED` or `NO_STRONG_SIGNAL` |
| Computed by `LeadIntelligenceEngine` | `decision_maker_reason` | Persona rationale string |

---

## I. What We Can Test for FREE
1. CLI tool contract inspection (`deepline tools describe <toolId>`).
2. Local pipeline execution (`node src/test_research_pipeline.js` & `node src/poc_runner.js`).
3. JSON schema validation against mock research data (`data/research_leads.json`).

---

## J. What Requires Approval Before Execution
1. Setting a personal Apollo API key in Deepline settings.
2. Executing any live API search query (`apollo_company_search` or `apollo_search_people_with_match`).
3. Running email/phone reveal operations (`apollo_people_match` / `apollo_reveal_person`).

---

## K. What Remains Unknown / Requires Verification
* `UNKNOWN / REQUIRES VERIFICATION`: The exact monthly query limit and credit balance of the user's personal Apollo API plan.
* `UNKNOWN / REQUIRES VERIFICATION`: Whether Apollo's internal industry taxonomy tag IDs (`organization_industry_tag_ids`) contain a single specific tag for "UK Main Contractors" versus generic "Construction".
