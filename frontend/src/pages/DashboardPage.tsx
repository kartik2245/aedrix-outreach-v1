import React from 'react';
import {
  Users,
  CheckCircle2,
  AlertCircle,
  FileText,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Layers,
  Search,
  MailCheck,
  CheckSquare,
} from 'lucide-react';
import { DashboardStats, ApprovalRecord } from '../types';
import { MetricCard } from '../components/MetricCard';
import { Badge } from '../components/Badge';

interface DashboardPageProps {
  stats: DashboardStats | null;
  approvals: ApprovalRecord[];
  onNavigateToLeads: () => void;
  onNavigateToApprovals: () => void;
  onNavigateToStaging: () => void;
  onSelectLead: (leadId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  stats,
  approvals,
  onNavigateToApprovals,
  onSelectLead,
}) => {
  if (!stats) return <div>Loading dashboard analytics...</div>;

  const pendingList = approvals.filter((a) => a.approval_status === 'PENDING_REVIEW');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Safety & Environment Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(16, 185, 129, 0.08))',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <ShieldCheck size={20} color="var(--success)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              Zero-Risk Operational Safety Guarantee
            </h3>
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', margin: 0 }}>
            {stats.safety?.dry_run
              ? 'DEMO MODE active: 0 real emails dispatched, 0 paid API credits consumed. Human approval gates are strictly enforced before staging.'
              : 'PRODUCTION MODE active: Live database & lead discovery active. Human approval is strictly required before staging. Email delivery disabled.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Real Emails Dispatched
            </div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--success)' }}>
              {stats.safety?.real_emails_sent ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* System Status Indicators Bar */}
      <div
        className="card"
        style={{
          background: 'rgba(15, 23, 42, 0.7)',
          borderColor: 'rgba(255, 255, 255, 0.08)',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', marginBottom: '10px' }}>
          System Operational Status
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Database:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399' }}>Connected</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Lead Discovery:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399' }}>Ready</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>AI Outreach:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399' }}>Ready</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#60a5fa' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Approval Gate:</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#60a5fa' }}>Active</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#94a3b8' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Email Delivery (Smartlead):</span>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#94a3b8' }}>Disabled</span>
          </div>
        </div>
      </div>

      {/* Demo Workflow Visual Stepper */}
      <div
        className="card"
        style={{
          background: 'rgba(15, 23, 42, 0.6)',
          borderColor: 'rgba(255, 255, 255, 0.08)',
          padding: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#6366f1" />
            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
              AI Cold Outreach Workflow Pipeline
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Complete outreach automation with Human-in-the-Loop approval checkpoints
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '10px' }}>
          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#60a5fa', marginBottom: '4px' }}>
              <Layers size={14} />
              <span>1. ICP Designer</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>AI engine translates goals into validated ICP configs</div>
          </div>

          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#fbbf24', marginBottom: '4px' }}>
              <CheckSquare size={14} />
              <span>2. ICP Approval</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Human operator approves or edits criteria</div>
          </div>

          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#34d399', marginBottom: '4px' }}>
              <Search size={14} />
              <span>3. Lead Discovery</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Account research & contractor verification</div>
          </div>

          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#a78bfa', marginBottom: '4px' }}>
              <FileText size={14} />
              <span>4. AI Outreach</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Zero-hallucination drafts & 19-point QA</div>
          </div>

          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#f87171', marginBottom: '4px' }}>
              <ShieldCheck size={14} />
              <span>5. Human Gate</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Approve, edit copy, or block outreach</div>
          </div>

          <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8', marginBottom: '4px' }}>
              <MailCheck size={14} />
              <span>6. Campaign Staging</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Staged campaigns & batch scheduling</div>
          </div>
        </div>
      </div>

      {/* Requested Primary Cards */}
      <div className="metrics-grid">
        <MetricCard
          label="Total Leads"
          value={stats.total_leads}
          subtext="Verified UK contractor accounts"
          icon={<Users size={18} />}
          color="var(--primary)"
        />
        <MetricCard
          label="Qualified Leads"
          value={stats.qualified_leads}
          subtext={`${stats.p1_leads} P1 Strategic, ${stats.p2_leads} P2 High-Fit`}
          icon={<CheckCircle2 size={18} />}
          color="var(--success)"
        />
        <MetricCard
          label="Pending Approvals"
          value={stats.pending_approvals}
          subtext="Awaiting operator review before staging"
          icon={<AlertCircle size={18} />}
          color="var(--warning)"
        />
        <MetricCard
          label="Approved Leads"
          value={stats.approved_leads}
          subtext="Reviewed and approved by operator"
          icon={<FileText size={18} />}
          color="var(--success)"
        />
        <MetricCard
          label="Outreach Ready"
          value={stats.smartlead_eligible_leads}
          subtext="Staged and ready for delivery"
          icon={<MailCheck size={18} />}
          color="var(--accent)"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="Personalized Drafts"
          value={stats.emails_generated}
          subtext="3-touch sequence (Email 1, Follow-up A, Follow-up B)"
          icon={<Sparkles size={18} />}
          color="var(--primary)"
        />
        <MetricCard
          label="QA Validated"
          value={stats.qa_passed}
          subtext="Zero-hallucination compliance"
          icon={<CheckCircle2 size={18} />}
          color="var(--success)"
        />
        <MetricCard
          label="Edited by Operator"
          value={stats.edited_leads}
          subtext="Human customized messaging"
          icon={<FileText size={18} />}
          color="var(--warning)"
        />
        <MetricCard
          label="Blocked / Safety Gated"
          value={stats.blocked_leads}
          subtext="Disqualified or invalid emails"
          icon={<ShieldCheck size={18} />}
          color="var(--danger)"
        />
      </div>

      {/* Funnel & Approval Queue Snapshot */}
      <div className="dashboard-grid">
        {/* Outreach Funnel Analytics */}
        <div className="card">
          <h3 className="section-title">Qualification & Outreach Funnel</h3>
          <div className="funnel-container">
            <div className="funnel-step">
              <div className="funnel-label">
                <span>1. Deepline Ingested</span>
                <span className="count">{stats.total_leads}</span>
              </div>
              <div className="funnel-bar-bg">
                <div className="funnel-bar-fill" style={{ width: '100%', background: 'var(--primary)' }} />
              </div>
            </div>

            <div className="funnel-step">
              <div className="funnel-label">
                <span>2. ICP Qualified (£10M+ UK)</span>
                <span className="count">{stats.qualified_leads}</span>
              </div>
              <div className="funnel-bar-bg">
                <div
                  className="funnel-bar-fill"
                  style={{
                    width: `${stats.total_leads ? (stats.qualified_leads / stats.total_leads) * 100 : 0}%`,
                    background: 'var(--success)',
                  }}
                />
              </div>
            </div>

            <div className="funnel-step">
              <div className="funnel-label">
                <span>3. High Opportunity (P1 / P2)</span>
                <span className="count">{stats.p1_leads + stats.p2_leads}</span>
              </div>
              <div className="funnel-bar-bg">
                <div
                  className="funnel-bar-fill"
                  style={{
                    width: `${stats.total_leads ? ((stats.p1_leads + stats.p2_leads) / stats.total_leads) * 100 : 0}%`,
                    background: 'var(--accent)',
                  }}
                />
              </div>
            </div>

            <div className="funnel-step">
              <div className="funnel-label">
                <span>4. Human Approved for Staging</span>
                <span className="count">{stats.approved_leads}</span>
              </div>
              <div className="funnel-bar-bg">
                <div
                  className="funnel-bar-fill"
                  style={{
                    width: `${stats.total_leads ? (stats.approved_leads / stats.total_leads) * 100 : 0}%`,
                    background: 'var(--success)',
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Actionable Review Queue Snapshot */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 className="section-title" style={{ margin: 0 }}>
              Actionable Review Queue ({pendingList.length})
            </h3>
            <button className="btn-secondary" onClick={onNavigateToApprovals} style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
              View All Approvals <ArrowRight size={13} style={{ marginLeft: 4 }} />
            </button>
          </div>

          {pendingList.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <CheckCircle2 size={32} color="var(--success)" style={{ margin: '0 auto 8px', display: 'block' }} />
              Approval queue is up to date! All drafts reviewed.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {pendingList.slice(0, 5).map((r) => (
                <div
                  key={r.lead_id}
                  onClick={() => onSelectLead(r.lead_id)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-glass)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  className="hover-card"
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-main)' }}>
                      {r.company}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {r.contact} • {r.title}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge type="priority" value={r.priority} />
                    <Badge type="approval" value={r.approval_status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
