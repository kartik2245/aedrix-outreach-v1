import {
  DashboardStats,
  LeadsListResponse,
  LeadDetailResponse,
  ApprovalRecord,
  CampaignFlowResponse,
  SmartleadStagingPlan,
  SystemStatusResponse,
  DemoRunResponse,
  ICPConfig,
  ICPApprovalRecord,
  DeeplineDiscoveryPreviewResponse,
  DeeplineRunResultResponse,
  DatabaseHealthResponse,
  ModeConfigResponse,
  ReadinessResponse,
  DemoActionResponse,
} from '../types';

const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getDashboardStats: () => fetchJson<DashboardStats>('/dashboard/stats'),

  getLeads: (params?: {
    search?: string;
    icp_status?: string;
    priority?: string;
    approval_status?: string;
    personalization_status?: string;
    campaign_id?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          query.set(k, String(v));
        }
      });
    }
    const qs = query.toString();
    return fetchJson<LeadsListResponse>(`/leads${qs ? `?${qs}` : ''}`);
  },

  getLeadDetail: (leadId: string) => fetchJson<LeadDetailResponse>(`/leads/${leadId}`),

  getApprovals: (status?: string, campaignId?: string) => {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (campaignId) query.set('campaign_id', campaignId);
    const qs = query.toString();
    return fetchJson<ApprovalRecord[]>(`/approvals${qs ? `?${qs}` : ''}`);
  },

  getApprovalRecord: (leadId: string) => fetchJson<ApprovalRecord>(`/approvals/${leadId}`),

  approveLead: (leadId: string, reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<{ ok: boolean; message: string; record: ApprovalRecord }>(`/approvals/${leadId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewer }),
    }),

  rejectLead: (leadId: string, reason = 'Rejected by operator', reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<{ ok: boolean; message: string; record: ApprovalRecord }>(`/approvals/${leadId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason, reviewer }),
    }),

  blockLead: (leadId: string, reason = 'Blocked by operator', reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<{ ok: boolean; message: string; record: ApprovalRecord }>(`/approvals/${leadId}/block`, {
      method: 'POST',
      body: JSON.stringify({ reason, reviewer }),
    }),

  editDraft: (
    leadId: string,
    email1?: string,
    followupA?: string,
    followupB?: string,
    reviewer = 'HUMAN_OPERATOR'
  ) =>
    fetchJson<{ ok: boolean; message: string; record: ApprovalRecord }>(`/approvals/${leadId}/edit`, {
      method: 'POST',
      body: JSON.stringify({
        email_1: email1,
        followup_a: followupA,
        followup_b: followupB,
        reviewer,
      }),
    }),

  editLeadDraft: (
    leadId: string,
    drafts: {
      email_1?: string;
      followup_a?: string;
      followup_b?: string;
    },
    reviewer = 'HUMAN_OPERATOR'
  ) =>
    fetchJson<{ ok: boolean; message: string; record: ApprovalRecord }>(`/approvals/${leadId}/edit`, {
      method: 'POST',
      body: JSON.stringify({
        email_1: drafts.email_1,
        followup_a: drafts.followup_a,
        followup_b: drafts.followup_b,
        reviewer,
      }),
    }),

  // ICP Designer & Approval endpoints
  generateICP: (payload: {
    campaign_name: string;
    campaign_objective: string;
    product_context?: string;
    geography?: string;
    industry?: string;
    company_size?: string;
    target_personas?: string[];
    minimum_employees?: number;
    maximum_employees?: number;
    minimum_revenue?: number;
    maximum_revenue?: number;
    positive_signals?: string[];
    negative_signals?: string[];
    hard_disqualifiers?: string[];
    campaign_exclusions?: string[];
    voc_context?: string;
    campaign_id?: string;
  }) =>
    fetchJson<{
      ok: boolean;
      message: string;
      icp_id: string;
      campaign_id: string;
      status: string;
      icp: ICPConfig;
      record: ICPApprovalRecord;
    }>('/icp/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  createManualICP: (payload: {
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
  }) =>
    fetchJson<{
      ok: boolean;
      message: string;
      icp_id: string;
      campaign_id: string;
      status: string;
      source: string;
      icp: ICPConfig;
      record: ICPApprovalRecord;
    }>('/icp/manual', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listICPs: (status?: string, campaignId?: string) => {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (campaignId) query.set('campaign_id', campaignId);
    const qs = query.toString();
    return fetchJson<ICPApprovalRecord[]>(`/icp${qs ? `?${qs}` : ''}`);
  },

  getICPs: (status?: string, campaignId?: string) => {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (campaignId) query.set('campaign_id', campaignId);
    const qs = query.toString();
    return fetchJson<ICPApprovalRecord[]>(`/icp${qs ? `?${qs}` : ''}`);
  },

  getICPRecord: (icpId: string) => fetchJson<ICPApprovalRecord>(`/icp/${icpId}`),

  approveICP: (icpId: string, reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<ICPApprovalRecord>(`/icp/${icpId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewer }),
    }),

  rejectICP: (icpId: string, reason: string, reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<ICPApprovalRecord>(`/icp/${icpId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason, reviewer }),
    }),

  editICP: (icpId: string, updatedData: Record<string, any>, reviewer = 'HUMAN_OPERATOR') =>
    fetchJson<ICPApprovalRecord>(`/icp/${icpId}`, {
      method: 'PUT',
      body: JSON.stringify({ updated_data: updatedData, reviewer }),
    }),

  previewDeeplineDiscovery: (icpId: string, requestedCount = 100) =>
    fetchJson<DeeplineDiscoveryPreviewResponse>(`/icp/${icpId}/deepline-preview`, {
      method: 'POST',
      body: JSON.stringify({ requested_count: requestedCount }),
    }),

  runDeeplineDiscovery: (icpId: string, requestedCount = 100) =>
    fetchJson<DeeplineRunResultResponse>(`/icp/${icpId}/deepline-run`, {
      method: 'POST',
      body: JSON.stringify({ requested_count: requestedCount }),
    }),

  getCampaignFlow: () => fetchJson<CampaignFlowResponse>('/campaign'),

  getSmartleadStaging: () => fetchJson<SmartleadStagingPlan>('/smartlead/staging'),

  getSystemStatus: () => fetchJson<SystemStatusResponse>('/system/status'),

  getDatabaseHealth: () => fetchJson<DatabaseHealthResponse>('/system/database-health'),

  getAppMode: () => fetchJson<ModeConfigResponse>('/system/mode'),

  setAppMode: (mode: string, confirmation?: string) =>
    fetchJson<ModeConfigResponse>('/system/mode', {
      method: 'POST',
      body: JSON.stringify({ mode, confirmation }),
    }),

  getReadiness: () => fetchJson<ReadinessResponse>('/system/readiness'),

  seedDemo: () =>
    fetchJson<DemoActionResponse>('/demo/seed', {
      method: 'POST',
    }),

  resetDemo: () =>
    fetchJson<DemoActionResponse>('/demo/reset', {
      method: 'POST',
    }),

  runFullDemo: () =>
    fetchJson<DemoActionResponse>('/demo/run', {
      method: 'POST',
    }),

  runDemoPipeline: () =>
    fetchJson<DemoRunResponse>('/demo/run', {
      method: 'POST',
    }),
};
