export interface SafetyIndicators {
  dry_run: boolean;
  send_emails: boolean;
  smartlead_live: boolean;
  production_send_confirmation: boolean;
  mode_display: string;
  real_emails_sent: number;
}

export interface DashboardStats {
  total_leads: number;
  qualified_leads: number;
  p1_leads: number;
  p2_leads: number;
  p3_leads: number;
  pending_approvals: number;
  approved_leads: number;
  rejected_leads: number;
  edited_leads: number;
  blocked_leads: number;
  smartlead_eligible_leads: number;
  emails_generated: number;
  qa_passed: number;
  qa_failed: number;
  safety: SafetyIndicators;
}

export interface LeadSummaryItem {
  lead_id: string;
  company: string;
  contact: string;
  title: string;
  email: string;
  qualification_status: string;
  opportunity_score: number;
  accessibility_score: number;
  outreach_priority_index: number;
  priority: string;
  personalization_status: string;
  approval_status: string;
  smartlead_eligible: boolean;
  qa_status: string;
}

export interface LeadsListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: LeadSummaryItem[];
}

export interface LeadDetailResponse {
  lead_id: string;
  company: string;
  contact: string;
  title: string;
  email: string;
  website?: string;
  linkedin_url?: string;
  qualification_status: string;
  disqualification_reason?: string;
  opportunity_score: number;
  accessibility_score: number;
  outreach_priority_index: number;
  priority: string;
  evidence_levels: Record<string, string>;
  personalization_status: string;
  personalization_note: string;
  voc_angle: string;
  research_signals?: string;
  email_1: string;
  followup_a: string;
  followup_b: string;
  email_1_original: string;
  followup_a_original: string;
  followup_b_original: string;
  edited_email_1?: string;
  edited_followup_a?: string;
  edited_followup_b?: string;
  qa_status: string;
  qa_reasons: string[];
  approval_status: string;
  reviewer?: string;
  reviewed_at?: string;
  smartlead_eligible: boolean;
  blocked_reason?: string;
  flag_no_strong_signal: boolean;
  metadata?: Record<string, any>;
}

export interface ApprovalRecord {
  lead_id: string;
  company: string;
  contact: string;
  title: string;
  email: string;
  qualification_status: string;
  opportunity_score: number;
  accessibility_score: number;
  outreach_priority_index: number;
  priority: string;
  personalization_status: string;
  personalization_note: string;
  voc_angle: string;
  email_1_original: string;
  followup_a_original: string;
  followup_b_original: string;
  qa_status: string;
  qa_reasons: string[];
  approval_status: string;
  reviewer?: string;
  reviewed_at?: string;
  edited_email_1?: string;
  edited_followup_a?: string;
  edited_followup_b?: string;
  smartlead_eligible: boolean;
  blocked_reason?: string;
  flag_no_strong_signal: boolean;
  campaign_id?: string;
  icp_id?: string;
  icp_version?: string;
  metadata: Record<string, any>;
}

export type ICPSource = 'CLAUDE_GENERATED' | 'MANUAL';

export interface ICPConfig {
  id: string;
  campaign_id: string;
  name: string;
  version: string;
  campaign_description: string;
  source?: ICPSource;
  geography: {
    primary_country: string;
    allowed_country_keywords: string[];
    require_target_country_operating: boolean;
  };
  industries: string[];
  company_size: string;
  minimum_employees?: number;
  maximum_employees?: number;
  minimum_revenue?: number;
  maximum_revenue?: number;
  target_personas: string[];
  positive_signals: string[];
  negative_signals: string[];
  hard_disqualifiers: Array<{
    code: string;
    description: string;
    field: string;
  }>;
  campaign_exclusions: Array<{
    code: string;
    description: string;
    fields: string[];
  }>;
  required_conditions: string[];
  preferred_conditions: string[];
  reasoning?: string;
  voc_context?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ICPApprovalRecord {
  icp_id: string;
  campaign_id: string;
  name: string;
  version: string;
  status: string;
  source?: ICPSource;
  original_claude_icp?: ICPConfig | null;
  effective_icp: ICPConfig;
  reviewer?: string;
  reviewed_at?: string;
  rejection_reason?: string;
  blocked_reason?: string;
  deepline_eligible: boolean;
  deepline_run_ids: string[];
  edit_history: any[];
  audit_trail: any[];
}

export interface ManualICPCreateRequest {
  campaign_name: string;
  campaign_objective: string;
  industry?: string;
  industries?: string[];
  geography?: string;
  allowed_country_keywords?: string[];
  minimum_employees?: number;
  maximum_employees?: number;
  minimum_revenue?: number;
  maximum_revenue?: number;
  company_size?: string;
  target_personas?: string[];
  seniority_levels?: string[];
  technologies?: string[];
  qualification_rules?: string[];
  hard_disqualification_rules?: string[];
  campaign_exclusion_rules?: string[];
  additional_notes?: string;
  voc_context?: string;
  campaign_id?: string;
}

export interface DeeplineDiscoveryPreviewResponse {
  icp_id: string;
  campaign_id: string;
  approval_status: string;
  deepline_eligible: boolean;
  discovery_request: {
    icp_id: string;
    campaign_id: string;
    campaign_name: string;
    geography: string[];
    industries: string[];
    company_size: string;
    personas: string[];
    positive_signals: string[];
    exclusions: string[];
    requested_lead_count: number;
    batch_size: number;
  };
  estimated_batches: number;
  safety_mode: string;
}

export interface DeeplineRunResultResponse {
  ok: boolean;
  message: string;
  result: {
    run_id: string;
    icp_id: string;
    campaign_id: string;
    summary: {
      discovered: number;
      valid: number;
      qualified: number;
      hard_disqualified: number;
      campaign_excluded: number;
      p1_count: number;
      p2_count: number;
      p3_count: number;
    };
    run_artifacts_path: string;
    safety_mode: string;
  };
}

export interface CampaignStep {
  step_number: number;
  name: string;
  delay_display: string;
  delay_days: number;
  description: string;
  condition: string;
}

export interface CampaignFlowResponse {
  name: string;
  description: string;
  steps: CampaignStep[];
  event_branches: Array<{
    event: string;
    action: string;
    target_state: string;
    badge_color: string;
  }>;
  all_states: string[];
}

export interface SmartleadBatch {
  batch_index: number;
  batch_size: number;
  leads: Array<{
    email: string;
    first_name: string;
    last_name: string;
    company_name: string;
    website?: string;
    linkedin_profile?: string;
    custom_fields: Record<string, any>;
  }>;
}

export interface SmartleadStagingPlan {
  mode: string;
  safety_status: {
    dry_run: boolean;
    send_emails: boolean;
    smartlead_live: boolean;
    api_calls_made: number;
    real_emails_sent: number;
    production_ready: boolean;
  };
  summary: {
    total_queue_records: number;
    approved_eligible_count: number;
    excluded_count: number;
    batch_size: number;
    total_batches: number;
  };
  campaign_payload: {
    name: string;
    status: string;
    client_id?: string | null;
    track_settings: {
      open_tracking: boolean;
      click_tracking: boolean;
    };
  };
  sequence_configuration: Array<{
    seq_number: number;
    seq_delay_details: { delay_in_days: number };
    subject: string;
    body: string;
    step_type: string;
    trigger_condition?: string;
  }>;
  batches: SmartleadBatch[];
  excluded_leads: Array<{
    lead_id: string;
    company: string;
    contact: string;
    email: string;
    approval_status: string;
    smartlead_eligible: boolean;
    reason: string;
  }>;
}

export interface IntegrationStatus {
  name: string;
  status: string;
  mode: string;
  description: string;
}

export interface SystemStatusResponse {
  integrations: IntegrationStatus[];
  safety_flags: Record<string, any>;
  masked_env: Record<string, string>;
  recent_logs: any[];
}

export interface DemoRunResponse {
  ok: boolean;
  message: string;
  summary: {
    records_processed: number;
    qualified_leads: number;
    p1_leads: number;
    p2_leads: number;
    p3_leads: number;
    emails_generated: number;
    qa_passed: number;
    pending_approvals: number;
    approved_leads: number;
    api_calls_made: number;
    real_emails_sent: number;
    safety_mode: string;
  };
}

export interface DatabaseHealthResponse {
  database: string;
  connected: boolean;
  latency_ms: number | null;
  database_enabled: boolean;
  status: string;
}

export interface ModeConfigResponse {
  mode: string;
  demo_mode: boolean;
  production_mode: boolean;
  database: string;
  database_connected: boolean;
  database_latency_ms: number | null;
  claude_mode: string;
  deepline_mode: string;
  smartlead_mode: string;
  real_emails_enabled: boolean;
  smartlead_live: boolean;
  deepline_live: boolean;
  real_emails_sent: number;
  safety_summary: string;
}

export interface ReadinessResponse {
  application: string;
  mode: string;
  database: string;
  frontend: string;
  claude: string;
  deepline: string;
  smartlead: string;
  email: string;
  details: Record<string, any>;
}

export interface DemoActionResponse {
  ok: boolean;
  message: string;
  summary: Record<string, any>;
}
