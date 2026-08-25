"""
lead_repository.py
Repository for high-performance paginated search, multi-filter queries, and lead dossiers in PostgreSQL.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, and_, desc, asc

from src.database.models.campaign import Campaign
from src.database.models.lead import Lead, LeadResearch, LeadEvidence, VoCContext
from src.database.models.email import EmailDraft, EmailApproval


class LeadRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, lead_id: str) -> Optional[Lead]:
        stmt = (
            select(Lead)
            .options(
                joinedload(Lead.research),
                joinedload(Lead.evidence_items),
                joinedload(Lead.voc),
                joinedload(Lead.email_draft),
                joinedload(Lead.email_approval),
            )
            .where(Lead.id == lead_id)
        )
        return self.session.scalar(stmt)

    def list_leads(
        self,
        search: Optional[str] = None,
        icp_status: Optional[str] = None,
        priority: Optional[str] = None,
        approval_status: Optional[str] = None,
        personalization_status: Optional[str] = None,
        campaign_id: Optional[str] = None,
        environment: Optional[str] = None,
        sort_by: str = "outreach_priority_index",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 15,
    ) -> Tuple[List[Lead], int]:
        """
        Database-level indexed filtering and pagination for high performance (10,000+ leads).
        """
        stmt = select(Lead).options(
            joinedload(Lead.email_draft),
            joinedload(Lead.email_approval),
        )

        conditions = []

        if environment:
            conditions.append(Lead.environment == environment.upper())

        if search:
            s_term = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(Lead.company_name).like(s_term),
                    func.lower(Lead.contact_name).like(s_term),
                    func.lower(Lead.email).like(s_term),
                    func.lower(Lead.job_title).like(s_term),
                )
            )

        if icp_status:
            conditions.append(Lead.qualification_status == icp_status.upper())

        if priority:
            conditions.append(Lead.priority_level == priority.upper())

        if personalization_status:
            conditions.append(Lead.personalization_status == personalization_status.upper())

        if campaign_id:
            conditions.append(Lead.campaign_id == campaign_id)

        if approval_status:
            stmt = stmt.join(EmailApproval, Lead.id == EmailApproval.lead_id)
            conditions.append(EmailApproval.approval_status == approval_status.upper())

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Count total matches
        count_stmt = select(func.count(func.distinct(Lead.id)))
        if approval_status:
            count_stmt = count_stmt.join(EmailApproval, Lead.id == EmailApproval.lead_id)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        total = self.session.scalar(count_stmt) or 0

        # Sorting
        sort_col = getattr(Lead, sort_by, Lead.outreach_priority_index)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(asc(sort_col))
        else:
            stmt = stmt.order_by(desc(sort_col))

        # Pagination
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        items = list(self.session.scalars(stmt).unique().all())
        return items, total

    def upsert_lead(
        self,
        lead_id: str,
        campaign_id: str,
        company_name: str,
        company_domain: str,
        contact_name: str,
        job_title: str,
        email: str,
        email_status: str = "PATTERN_CONFIRMED",
        linkedin_url: Optional[str] = None,
        company_size: Optional[str] = None,
        industry: Optional[str] = None,
        opportunity_score: float = 0.0,
        accessibility_score: float = 0.0,
        outreach_priority_index: float = 0.0,
        priority_level: str = "P3",
        qualification_status: str = "QUALIFIED",
        disqualification_reason: Optional[str] = None,
        personalization_status: str = "SIGNAL_VERIFIED",
        personalization_note: Optional[str] = None,
        voc_angle: Optional[str] = None,
        environment: str = "PRODUCTION",
        icp_id: Optional[str] = None,
        icp_version: str = "1.0.0",
    ) -> Lead:
        # Ensure campaign exists
        campaign = self.session.scalar(select(Campaign).where(Campaign.id == campaign_id))
        if not campaign:
            campaign = Campaign(id=campaign_id, name=f"Campaign {campaign_id}", environment=environment)
            self.session.add(campaign)
            self.session.flush()

        lead = self.session.scalar(select(Lead).where(Lead.id == lead_id))
        if lead:
            lead.campaign_id = campaign_id
            lead.icp_id = icp_id
            lead.icp_version = icp_version
            lead.company_name = company_name
            lead.company_domain = company_domain
            lead.contact_name = contact_name
            lead.job_title = job_title
            lead.email = email
            lead.email_status = email_status
            lead.linkedin_url = linkedin_url
            lead.company_size = company_size
            lead.industry = industry
            lead.opportunity_score = opportunity_score
            lead.accessibility_score = accessibility_score
            lead.outreach_priority_index = outreach_priority_index
            lead.priority_level = priority_level
            lead.qualification_status = qualification_status
            lead.disqualification_reason = disqualification_reason
            lead.personalization_status = personalization_status
            lead.personalization_note = personalization_note
            lead.voc_angle = voc_angle[:255] if voc_angle else None
            lead.environment = environment
            self.session.flush()
            return lead

        lead = Lead(
            id=lead_id,
            campaign_id=campaign_id,
            icp_id=icp_id,
            icp_version=icp_version,
            company_name=company_name,
            company_domain=company_domain,
            contact_name=contact_name,
            job_title=job_title,
            email=email,
            email_status=email_status,
            linkedin_url=linkedin_url,
            company_size=company_size,
            industry=industry,
            opportunity_score=opportunity_score,
            accessibility_score=accessibility_score,
            outreach_priority_index=outreach_priority_index,
            priority_level=priority_level,
            qualification_status=qualification_status,
            disqualification_reason=disqualification_reason,
            personalization_status=personalization_status,
            personalization_note=personalization_note,
            voc_angle=voc_angle[:255] if voc_angle else None,
            environment=environment,
        )
        self.session.add(lead)
        self.session.flush()
        return lead
