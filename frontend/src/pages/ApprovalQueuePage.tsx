import React, { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Edit3,
  Ban,
  Eye,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { ApprovalRecord } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

interface ApprovalQueuePageProps {
  approvals: ApprovalRecord[];
  onRefresh: () => void;
  onSelectLead: (leadId: string) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', text: string) => void;
}

export const ApprovalQueuePage: React.FC<ApprovalQueuePageProps> = ({
  approvals,
  onRefresh,
  onSelectLead,
  showToast,
}) => {
  const [statusFilter, setStatusFilter] = useState('PENDING_REVIEW');
  const [selectedRecord, setSelectedRecord] = useState<ApprovalRecord | null>(null);

  // Edit Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editEmail1, setEditEmail1] = useState('');
  const [editFollowupA, setEditFollowupA] = useState('');
  const [editFollowupB, setEditFollowupB] = useState('');

  // Reject / Block Modal State
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [blockModalOpen, setBlockModalOpen] = useState(false);
  const [reasonText, setReasonText] = useState('');

  const filtered = approvals.filter((r) => {
    if (statusFilter === 'ALL') return true;
    return r.approval_status === statusFilter;
  });

  const handleApprove = async (leadId: string) => {
    try {
      const res = await api.approveLead(leadId, 'HUMAN_OPERATOR');
      showToast('success', res.message);
      onRefresh();
    } catch (err: any) {
      showToast('error', `Approval failed: ${err.message}`);
    }
  };

  const openEditModal = (r: ApprovalRecord) => {
    setSelectedRecord(r);
    setEditEmail1(r.edited_email_1 || r.email_1_original);
    setEditFollowupA(r.edited_followup_a || r.followup_a_original);
    setEditFollowupB(r.edited_followup_b || r.followup_b_original);
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedRecord) return;
    try {
      const res = await api.editLeadDraft(
        selectedRecord.lead_id,
        {
          email_1: editEmail1,
          followup_a: editFollowupA,
          followup_b: editFollowupB,
        },
        'HUMAN_OPERATOR'
      );
      showToast('warning', res.message);
      setEditModalOpen(false);
      onRefresh();
    } catch (err: any) {
      showToast('error', `Edit failed: ${err.message}`);
    }
  };

  const openRejectModal = (r: ApprovalRecord) => {
    setSelectedRecord(r);
    setReasonText('');
    setRejectModalOpen(true);
  };

  const handleReject = async () => {
    if (!selectedRecord) return;
    try {
      const res = await api.rejectLead(selectedRecord.lead_id, reasonText || 'Rejected by operator');
      showToast('success', res.message);
      setRejectModalOpen(false);
      onRefresh();
    } catch (err: any) {
      showToast('error', `Rejection failed: ${err.message}`);
    }
  };

  const openBlockModal = (r: ApprovalRecord) => {
    setSelectedRecord(r);
    setReasonText('');
    setBlockModalOpen(true);
  };

  const handleBlock = async () => {
    if (!selectedRecord) return;
    try {
      const res = await api.blockLead(selectedRecord.lead_id, reasonText || 'Blocked manually');
      showToast('success', res.message);
      setBlockModalOpen(false);
      onRefresh();
    } catch (err: any) {
      showToast('error', `Block failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Filter Tabs */}
      <div className="tabs-nav" style={{ marginBottom: 0 }}>
        {['PENDING_REVIEW', 'APPROVED', 'EDITED', 'REJECTED', 'BLOCKED', 'ALL'].map((st) => {
          const count =
            st === 'ALL'
              ? approvals.length
              : approvals.filter((r) => r.approval_status === st).length;
          return (
            <button
              key={st}
              className={`tab-btn ${statusFilter === st ? 'active' : ''}`}
              onClick={() => setStatusFilter(st)}
            >
              {st.replace('_', ' ')} ({count})
            </button>
          );
        })}
      </div>

      {/* Queue Items */}
      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-dim)' }}>
          No records currently in status: <strong>{statusFilter}</strong>.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filtered.map((record) => {
            const activeEmail1 = record.edited_email_1 || record.email_1_original;
            const isEdited = !!record.edited_email_1;

            return (
              <div key={record.lead_id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                      <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{record.company}</span>
                      <Badge type="priority" value={record.priority} />
                      <Badge type="approval" value={record.approval_status} />
                      <Badge type="personalization" value={record.personalization_status} />
                      {record.smartlead_eligible && (
                        <span style={{ fontSize: '0.72rem', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.3)', fontWeight: 600 }}>
                          Smartlead Eligible
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      <strong>{record.contact}</strong> ({record.title}) • <span style={{ fontFamily: 'var(--font-mono)' }}>{record.email}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {record.approval_status !== 'APPROVED' && (
                      <button className="btn btn-success" onClick={() => handleApprove(record.lead_id)}>
                        <CheckCircle size={14} />
                        <span>Approve</span>
                      </button>
                    )}

                    <button className="btn btn-outline" onClick={() => openEditModal(record)}>
                      <Edit3 size={14} />
                      <span>Edit</span>
                    </button>

                    {record.approval_status !== 'REJECTED' && (
                      <button className="btn btn-outline" onClick={() => openRejectModal(record)}>
                        <XCircle size={14} />
                        <span>Reject</span>
                      </button>
                    )}

                    {record.approval_status !== 'BLOCKED' && (
                      <button className="btn btn-outline" style={{ color: 'var(--danger)' }} onClick={() => openBlockModal(record)}>
                        <Ban size={14} />
                        <span>Block</span>
                      </button>
                    )}

                    <button className="btn btn-outline" onClick={() => onSelectLead(record.lead_id)}>
                      <Eye size={14} />
                      <span>Dossier</span>
                    </button>
                  </div>
                </div>

                {/* Email 1 Preview */}
                <div style={{ background: 'var(--bg-input)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', fontSize: '0.84rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-main)' }}>
                  {activeEmail1}
                </div>

                {/* Footer notes */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.76rem', color: 'var(--text-dim)', flexWrap: 'wrap', gap: '8px' }}>
                  <div>
                    <strong>VoC Angle:</strong> {record.voc_angle}
                  </div>
                  {isEdited && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#c084fc' }}>
                      <AlertTriangle size={12} />
                      <span>Draft edited by human reviewer (Requires re-approval)</span>
                    </div>
                  )}
                  {record.reviewer && (
                    <div>
                      Reviewed by: <strong>{record.reviewer}</strong>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title={`Edit Draft Copy: ${selectedRecord?.company}`}
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setEditModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSaveEdit}>
              Save & Require Re-Approval
            </button>
          </>
        }
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Editing copy preserves the original AI draft in the audit logs and transitions the lead status to <strong>EDITED</strong> (smartlead_eligible=False).
        </p>

        <div>
          <label className="form-label">Email 1 (Max 120 words)</label>
          <textarea
            className="form-textarea"
            rows={5}
            value={editEmail1}
            onChange={(e) => setEditEmail1(e.target.value)}
          />
        </div>

        <div>
          <label className="form-label">Follow-up A (Max 90 words)</label>
          <textarea
            className="form-textarea"
            rows={4}
            value={editFollowupA}
            onChange={(e) => setEditFollowupA(e.target.value)}
          />
        </div>

        <div>
          <label className="form-label">Follow-up B (Max 90 words)</label>
          <textarea
            className="form-textarea"
            rows={4}
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
        <label className="form-label">Reason for Rejection</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. Not in current outreach focus, duplicate account"
          value={reasonText}
          onChange={(e) => setReasonText(e.target.value)}
        />
      </Modal>

      {/* Block Modal */}
      <Modal
        isOpen={blockModalOpen}
        onClose={() => setBlockModalOpen(false)}
        title="Block Lead Draft"
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
        <label className="form-label">Reason for Blocking</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. Active CRM deal in progress, account suppression"
          value={reasonText}
          onChange={(e) => setReasonText(e.target.value)}
        />
      </Modal>
    </div>
  );
};
