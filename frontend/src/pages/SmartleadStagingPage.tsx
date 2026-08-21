import React, { useState, useEffect } from 'react';
import {
  Send,
  ShieldCheck,
  CheckCircle,
  Layers,
  Code2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../services/api';
import { SmartleadStagingPlan } from '../types';
import { MetricCard } from '../components/MetricCard';

export const SmartleadStagingPage: React.FC = () => {
  const [plan, setPlan] = useState<SmartleadStagingPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [showRawJson, setShowRawJson] = useState(false);
  const [expandedBatch, setExpandedBatch] = useState<number | null>(1);

  const fetchStaging = async () => {
    try {
      setLoading(true);
      const res = await api.getSmartleadStaging();
      setPlan(res);
    } catch (err) {
      console.error('Failed to load Smartlead staging:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStaging();
  }, []);

  if (loading) return <div>Loading Smartlead staging plan...</div>;
  if (!plan) return <div>Failed to load staging plan.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Safety Verification Header */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(6, 182, 212, 0.08))',
          borderColor: 'rgba(16, 185, 129, 0.3)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={20} color="var(--success)" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                Smartlead Delivery Staging & Integration Planner
              </h3>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.74rem', padding: '3px 8px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', fontWeight: 700 }}>
                Status: DISABLED
              </span>
              <span style={{ fontSize: '0.74rem', padding: '3px 8px', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)', fontWeight: 700 }}>
                Mode: STAGING ONLY
              </span>
              <span style={{ fontSize: '0.74rem', padding: '3px 8px', borderRadius: '4px', background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.3)', fontWeight: 700 }}>
                Live Sending: OFF
              </span>
            </div>
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', margin: 0 }}>
            This plan contains the exact payloads, custom variables, and sequences prepared for Smartlead.
            <strong> Live Smartlead delivery is disabled (SMARTLEAD_LIVE=false). 0 real API calls made. 0 real emails sent.</strong>
          </p>
        </div>

        <button
          className="btn btn-outline"
          onClick={() => setShowRawJson(!showRawJson)}
          style={{ fontSize: '0.82rem' }}
        >
          <Code2 size={14} />
          <span>{showRawJson ? 'Hide Raw JSON' : 'Inspect Staging JSON'}</span>
        </button>
      </div>

      {/* Raw JSON View */}
      {showRawJson && (
        <div className="card">
          <pre
            style={{
              background: 'var(--bg-input)',
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              overflowX: 'auto',
              maxHeight: '400px',
            }}
          >
            {JSON.stringify(plan, null, 2)}
          </pre>
        </div>
      )}

      {/* Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="Approved & Staged Leads"
          value={plan.summary.approved_eligible_count}
          subtext="Eligible for Smartlead upload"
          icon={<CheckCircle size={18} />}
          color="var(--success)"
        />
        <MetricCard
          label="Excluded / Non-Approved"
          value={plan.summary.excluded_count}
          subtext="Pending, rejected, or blocked"
          icon={<Send size={18} />}
          color="var(--warning)"
        />
        <MetricCard
          label="Batch Size"
          value={plan.summary.batch_size}
          subtext="Configurable BATCH_SIZE (400)"
          icon={<Layers size={18} />}
          color="var(--primary)"
        />
        <MetricCard
          label="Batches Prepared"
          value={plan.summary.total_batches}
          subtext="Chunked for rate-limited upload"
          icon={<Send size={18} />}
          color="var(--info)"
        />
      </div>

      {/* Staged Batches */}
      <div className="card">
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '16px' }}>
          Staged Batches ({plan.batches.length})
        </h3>

        {plan.batches.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)', fontSize: '0.86rem' }}>
            No approved leads currently staged. Approve leads in the Approval Queue to stage them for Smartlead.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {plan.batches.map((b) => (
              <div
                key={b.batch_index}
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    padding: '14px 18px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    background: 'rgba(0, 0, 0, 0.2)',
                  }}
                  onClick={() =>
                    setExpandedBatch(expandedBatch === b.batch_index ? null : b.batch_index)
                  }
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      Batch {b.batch_index} ({b.batch_size} Lead{b.batch_size > 1 ? 's' : ''})
                    </span>
                    <span style={{ fontSize: '0.72rem', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontWeight: 600 }}>
                      Ready for Staging
                    </span>
                  </div>

                  {expandedBatch === b.batch_index ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>

                {expandedBatch === b.batch_index && (
                  <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {b.leads.map((lead, lIdx) => (
                      <div
                        key={lIdx}
                        style={{
                          background: 'var(--bg-card)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '14px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <div>
                            <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{lead.company_name}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: '8px' }}>
                              {lead.first_name} {lead.last_name} &lt;{lead.email}&gt;
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '8px', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                          <div><strong>Job Title:</strong> {lead.custom_fields.job_title}</div>
                          <div><strong>Priority:</strong> {lead.custom_fields.priority} (Index: {lead.custom_fields.outreach_priority_index})</div>
                          <div><strong>VoC Angle:</strong> {lead.custom_fields.voc_angle}</div>
                          <div><strong>Personalization Status:</strong> {lead.custom_fields.personalization_status}</div>
                        </div>

                        <div style={{ marginTop: '10px', fontSize: '0.78rem', background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                            Email 1 Subject: {lead.custom_fields.email_1_subject}
                          </div>
                          <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                            {lead.custom_fields.email_1_body}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Excluded Leads */}
      {plan.excluded_leads.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, marginBottom: '14px' }}>
            Excluded Leads from Staging ({plan.excluded_leads.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {plan.excluded_leads.map((exc) => (
              <div
                key={exc.lead_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.82rem',
                }}
              >
                <div>
                  <span style={{ fontWeight: 600 }}>{exc.company}</span> ({exc.contact})
                </div>
                <div style={{ color: 'var(--text-dim)' }}>
                  Status: <strong>{exc.approval_status}</strong> — {exc.reason}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
