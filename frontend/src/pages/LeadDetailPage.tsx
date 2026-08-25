import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Building,
  User,
  Mail,
  ShieldCheck,
  CheckCircle,
  XCircle,
  Edit3,
  Ban,
  Sparkles,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { LeadDetailResponse } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

interface LeadDetailPageProps {
  leadId: string;
  onBack: () => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', text: string) => void;
}

export const LeadDetailPage: React.FC<LeadDetailPageProps> = ({
  leadId,
  onBack,
  showToast,
}) => {
  const [lead, setLead] = useState<LeadDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'email_1' | 'followup_a' | 'followup_b'>('email_1');

  // Modals
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [blockModalOpen, setBlockModalOpen] = useState(false);

  // Edit form state
  const [editEmail1, setEditEmail1] = useState('');
  const [editFollowupA, setEditFollowupA] = useState('');
  const [editFollowupB, setEditFollowupB] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [blockReason, setBlockReason] = useState('');

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const res = await api.getLeadDetail(leadId);
      setLead(res);
      setEditEmail1(res.email_1);
      setEditFollowupA(res.followup_a);
      setEditFollowupB(res.followup_b);
    } catch (err: any) {
      showToast('error', `Failed to load lead: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [leadId]);

  const handleApprove = async () => {
    try {
      const res = await api.approveLead(leadId, 'HUMAN_OPERATOR');
      showToast('success', res.message);
      fetchDetail();
    } catch (err: any) {
      showToast('error', `Approval failed: ${err.message}`);
    }
  };

  const handleApproveEmailStatus = async () => {
    try {
      const res = await api.approveEmailStatus(leadId, 'HUMAN_OPERATOR');
      showToast('success', res.message);
      fetchDetail();
    } catch (err: any) {
      showToast('error', `Email status approval failed: ${err.message}`);
    }
  };

  const handleReject = async () => {
    try {
      const res = await api.rejectLead(leadId, rejectReason || 'Operator rejected');
      showToast('success', res.message);
      setRejectModalOpen(false);
      fetchDetail();
    } catch (err: any) {
      showToast('error', `Rejection failed: ${err.message}`);
    }
  };

  const handleBlock = async () => {
    try {
      const res = await api.blockLead(leadId, blockReason || 'Operator blocked');
      showToast('success', res.message);
      setBlockModalOpen(false);
      fetchDetail();
    } catch (err: any) {
      showToast('error', `Block failed: ${err.message}`);
    }
  };

  const handleSaveEdit = async () => {
    try {
      const res = await api.editLeadDraft(
        leadId,
        {
          email_1: editEmail1,
          followup_a: editFollowupA,
        },
        'HUMAN_OPERATOR'
      );
      showToast('warning', res.message);
      setEditModalOpen(false);
      fetchDetail();
    } catch (err: any) {
      showToast('error', `Edit failed: ${err.message}`);
    }
  };

  if (loading) return <div>Loading lead intelligence dossier...</div>;
  if (!lead) return <div>Lead not found.</div>;

  const rawEmailStatus = (lead.email_status || lead.metadata?.email_status || (lead.email && lead.email.includes('@') ? 'VERIFIED' : 'NO_EMAIL')).toUpperCase();
  const isNoEmail = rawEmailStatus === 'NO_EMAIL' || rawEmailStatus === 'NO_EMAIL_PERSISTED' || !lead.email;
  const isUnverified = rawEmailStatus === 'UNVERIFIED' || rawEmailStatus === 'PATTERN_CONFIRMED' || rawEmailStatus === 'CATCHALL_UNVERIFIED';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Action Nav */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button className="btn btn-outline" onClick={onBack}>
          <ArrowLeft size={14} />
          <span>Back to List</span>
        </button>

        <div style={{ display: 'flex', gap: '10px' }}>
          {(lead.approval_stage === 'EMAIL_STATUS_APPROVAL' || isUnverified) && lead.approval_status !== 'APPROVED' && lead.approval_status !== 'REJECTED' && (
            <button className="btn btn-warning" style={{ background: '#f59e0b', borderColor: '#d97706', color: '#fff' }} onClick={handleApproveEmailStatus}>
              <CheckCircle size={14} />
              <span>Approve Email & Generate Copy</span>
            </button>
          )}

          {lead.approval_stage !== 'EMAIL_STATUS_APPROVAL' && !isNoEmail && lead.approval_status !== 'APPROVED' && (
            <button className="btn btn-success" onClick={handleApprove}>
              <CheckCircle size={14} />
              <span>Approve Draft</span>
            </button>
          )}

          <button className="btn btn-outline" onClick={() => setEditModalOpen(true)}>
            <Edit3 size={14} />
            <span>Edit Copy</span>
          </button>

          {lead.approval_status !== 'REJECTED' && (
            <button className="btn btn-outline" onClick={() => setRejectModalOpen(true)}>
              <XCircle size={14} />
              <span>Reject</span>
            </button>
          )}

          {lead.approval_status !== 'BLOCKED' && (
            <button className="btn btn-outline" style={{ color: 'var(--danger)' }} onClick={() => setBlockModalOpen(true)}>
              <Ban size={14} />
              <span>Block</span>
            </button>
          )}
        </div>
      </div>

      {/* Header Info Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{lead.company}</h2>
              <Badge type="icp" value={lead.qualification_status} />
              <Badge type="email_status" value={rawEmailStatus} />
              <Badge type="priority" value={lead.priority} />
              <Badge type="approval" value={lead.approval_status} />
              {lead.metadata?.role_track && (
                <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', background: '#312e81', color: '#a5b4fc', border: '1px solid #4338ca' }}>
                  Track: {lead.metadata.role_track}
                </span>
              )}
              {lead.metadata?.subject_variant && (
                <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', background: '#0891b2', color: '#ecfeff', border: '1px solid #0e7490' }}>
                  Subject Variant: {lead.metadata.subject_variant}
                </span>
              )}
              {lead.metadata?.branch_mode && (
                <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', background: '#db2777', color: '#fdf2f8', border: '1px solid #9d174d' }}>
                  Branch Mode: {lead.metadata.branch_mode}
                </span>
              )}
            </div>

            {isNoEmail && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', color: '#9ca3af', margin: '6px 0 8px 0', fontWeight: 600 }}>
                <span>Delivery Safety Block: <strong>{lead.blocked_reason || 'No usable work email discovered'}</strong></span>
              </div>
            )}

            {!isNoEmail && lead.approval_status === 'BLOCKED' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', color: '#ef4444', margin: '6px 0 8px 0', fontWeight: 600 }}>
                <span>Delivery Safety Block: <strong>{lead.blocked_reason || 'Email address invalid/bounced or compliance blocked'}</strong></span>
              </div>
            )}

            {isUnverified && lead.approval_status !== 'APPROVED' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', color: '#f59e0b', margin: '6px 0 8px 0', fontWeight: 600 }}>
                <span>Approval required before AI email generation</span>
              </div>
            )}

            {lead.approval_status !== 'BLOCKED' && lead.qualification_status !== 'QUALIFIED' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem', color: '#f59e0b', margin: '6px 0 8px 0', fontWeight: 600 }}>
                <span>ICP Qualification Status: <strong>{lead.qualification_status}</strong> {lead.disqualification_reason ? `— ${lead.disqualification_reason}` : ''}</span>
              </div>
            )}

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '18px', color: 'var(--text-muted)', fontSize: '0.86rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <User size={15} color="var(--primary)" />
                <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{lead.contact}</span>
                <span>({lead.title})</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Mail size={15} color="var(--primary)" />
                {isNoEmail ? (
                  <span style={{ color: 'var(--text-dim)', fontStyle: 'italic' }}>No usable work email discovered</span>
                ) : (
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{lead.email}</span>
                )}
              </div>
              {lead.website && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Building size={15} color="var(--primary)" />
                  <span>{lead.website}</span>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '14px', background: 'var(--bg-input)', padding: '10px 18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Opportunity</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>{lead.opportunity_score.toFixed(0)}</div>
            </div>
            <div style={{ width: '1px', background: 'var(--border-subtle)' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Accessibility</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>{lead.accessibility_score.toFixed(0)}</div>
            </div>
            <div style={{ width: '1px', background: 'var(--border-subtle)' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Outreach Index</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--primary)' }}>{lead.outreach_priority_index.toFixed(1)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Evidence Dossier & Email Preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* Left: Intelligence & Evidence */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Research & Personalization Note */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Sparkles size={18} color="var(--primary)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Personalization Signal</h3>
              <div style={{ marginLeft: 'auto' }}>
                <Badge type="personalization" value={lead.personalization_status} />
              </div>
            </div>

            <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '14px', fontSize: '0.86rem', lineHeight: 1.6 }}>
              "{lead.personalization_note}"
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <strong>VoC Angle:</strong> {lead.voc_angle}
            </div>
          </div>

          {/* Evidence Quality Breakdown */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Layers size={18} color="var(--info)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Evidence Level Audit</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.84rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Corporate Signal Level</span>
                <Badge type="evidence" value={lead.evidence_levels.signal || 'UNKNOWN'} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Company Scale Level</span>
                <Badge type="evidence" value={lead.evidence_levels.company_size || 'ESTIMATED'} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pain Point Inference</span>
                <Badge type="evidence" value={lead.evidence_levels.pain_point || 'INFERRED'} />
              </div>
            </div>
          </div>

          {/* QA Validation Results */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <ShieldCheck size={18} color="var(--success)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Zero-Hallucination QA Guard</h3>
              <div style={{ marginLeft: 'auto' }}>
                <Badge type="qa" value={lead.qa_status} />
              </div>
            </div>

            {lead.qa_reasons && lead.qa_reasons.length > 0 ? (
              <div style={{ fontSize: '0.8rem', color: '#f87171' }}>
                <strong>Issues Flagged:</strong> {lead.qa_reasons.join(', ')}
              </div>
            ) : (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                All 10-point anti-hallucination checks passed: verified facts only, word count limits strictly enforced, zero invented initiatives.
              </div>
            )}
          </div>
        </div>

        {/* Right: Email Drafts & Sequences */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700 }}>Generated Outreach Sequence</h3>
            {lead.edited_email_1 && (
              <span style={{ fontSize: '0.72rem', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                Human-Edited Copy Active
              </span>
            )}
          </div>

          {/* Email Tabs */}
          <div className="tabs-nav" style={{ flexWrap: 'wrap', gap: '4px' }}>
            <button
              className={`tab-btn ${activeTab === 'email_1' ? 'active' : ''}`}
              onClick={() => setActiveTab('email_1')}
            >
              Email 1 (Initial)
            </button>
            <button
              className={`tab-btn ${activeTab === 'followup_a' ? 'active' : ''}`}
              onClick={() => setActiveTab('followup_a')}
            >
              Follow-up A (Opened)
            </button>
            <button
              className={`tab-btn ${activeTab === 'followup_b' ? 'active' : ''}`}
              onClick={() => setActiveTab('followup_b')}
            >
              Follow-up B (Unopened)
            </button>
          </div>

          {/* Active Email Display */}
          <div style={{ flex: 1, background: 'var(--bg-input)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', whiteSpace: 'pre-wrap', fontSize: '0.86rem', lineHeight: 1.7, color: 'var(--text-main)', overflowY: 'auto' }}>
            {activeTab === 'email_1' && lead.email_1}
            {activeTab === 'followup_a' && lead.followup_a}
            {activeTab === 'followup_b' && lead.followup_b}
          </div>

          {/* Word Count / Footer */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', fontSize: '0.76rem', color: 'var(--text-dim)' }}>
            <span>
              Length:{' '}
              {activeTab === 'email_1'
                ? `${lead.email_1.split(/\s+/).length} words (Limit: 90)`
                : activeTab === 'followup_a'
                  ? `${lead.followup_a.split(/\s+/).length} words (Limit: 90)`
                  : `${lead.followup_b.split(/\s+/).length} words (Limit: 90)`}
            </span>
            <span>
              Timing:{' '}
              {activeTab === 'email_1'
                ? 'Day 0'
                : activeTab === 'followup_a'
                  ? '+1 Day after Open'
                  : '+2 Days after No Open'}
            </span>
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title={`Edit Outreach Drafts: ${lead.company}`}
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setEditModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSaveEdit}>
              Save & Mark for Re-Approval
            </button>
          </>
        }
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
          Editing email copy preserves the original AI draft in the audit history and resets status to{' '}
          <strong>EDITED</strong>, requiring explicit human re-approval before staging.
        </p>

        <div>
          <label className="form-label">Email 1 (Max 90 words)</label>
          <textarea
            className="form-textarea"
            rows={5}
            value={editEmail1}
            onChange={(e) => setEditEmail1(e.target.value)}
          />
        </div>

        <div>
          <label className="form-label">Follow-up A - Opened Email 1 (Max 90 words)</label>
          <textarea
            className="form-textarea"
            rows={5}
            value={editFollowupA}
            onChange={(e) => setEditFollowupA(e.target.value)}
          />
        </div>

        <div>
          <label className="form-label">Follow-up B - Unopened Email 1 (Max 90 words)</label>
          <textarea
            className="form-textarea"
            rows={5}
            value={editFollowupB}
            onChange={(e) => setEditFollowupB(e.target.value)}
          />
        </div>

      </Modal>

      {/* Reject Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Lead Draft"
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setRejectModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={handleReject}>
              Confirm Rejection
            </button>
          </>
        }
      >
        <label className="form-label">Rejection Reason</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. Out of current quarter scope, invalid contact tier"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      </Modal>

      {/* Block Modal */}
      <Modal
        isOpen={blockModalOpen}
        onClose={() => setBlockModalOpen(false)}
        title="Block Lead"
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setBlockModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={handleBlock}>
              Confirm Block
            </button>
          </>
        }
      >
        <label className="form-label">Blocking Reason</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. Confirmed active pipeline deal, suppression list"
          value={blockReason}
          onChange={(e) => setBlockReason(e.target.value)}
        />
      </Modal>
    </div>
  );
};
