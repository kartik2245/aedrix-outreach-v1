import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  Clock,
  CheckCircle2,
  CornerDownRight,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { CampaignFlowResponse } from '../types';

export const CampaignFlowPage: React.FC = () => {
  const [data, setData] = useState<CampaignFlowResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const res = await api.getCampaignFlow();
        setData(res);
      } catch (err) {
        console.error('Failed to load campaign flow:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div>Loading campaign flow visualizer...</div>;
  if (!data) return <div>Failed to load campaign flow.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Title Card */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <GitBranch size={22} color="var(--primary)" />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800 }}>{data.name}</h2>
        </div>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>{data.description}</p>
      </div>

      {/* Sequence Timeline Diagram */}
      <div className="card">
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '20px' }}>
          Sequence Timing & Behavior Logic (2-Day Initial Wait Enforced)
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', position: 'relative' }}>
          {/* Step 1: Email 1 */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '16px',
              padding: '16px',
              background: 'var(--bg-input)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'var(--primary)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '0.9rem',
                flexShrink: 0,
              }}
            >
              1
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Email 1 (Initial Cold Outreach)</h4>
                <span style={{ fontSize: '0.74rem', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontWeight: 600 }}>
                  Day 0 (Immediate upon approval)
                </span>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Evidence-grounded initial email (Max 120 words). Focuses on verified pre-construction document versioning pain points.
              </p>
            </div>
          </div>

          {/* Step 2: 2-Day Wait */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '12px 18px',
              background: 'rgba(245, 158, 11, 0.08)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(245, 158, 11, 0.25)',
              marginLeft: '20px',
            }}
          >
            <Clock size={20} color="var(--warning)" />
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#fbbf24' }}>
                Wait Period: 2 Days (48 Hours)
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                System monitors Smartlead webhook events (email opens, clicks, replies, bounces).
              </div>
            </div>
          </div>

          {/* Branch Decisions */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginLeft: '20px' }}>
            {/* Branch A: Opened */}
            <div
              style={{
                padding: '16px',
                background: 'rgba(16, 185, 129, 0.06)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} color="var(--success)" />
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#34d399' }}>
                  Branch A: Opened Email 1
                </h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Follow-up A (Max 90 words). Scheduled <strong>1 day (24h)</strong> after the open event. References open context with deeper proof points.
              </p>
            </div>

            {/* Branch B: Unopened */}
            <div
              style={{
                padding: '16px',
                background: 'rgba(168, 85, 247, 0.06)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CornerDownRight size={18} color="#c084fc" />
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c084fc' }}>
                  Branch B: Unopened after 48h
                </h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Follow-up B (Max 90 words). Triggered after the full <strong>2-day timeout</strong>. Pivots angle to real-time site manpower & financial tracking.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Event Actions */}
      <div className="card">
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '16px' }}>
          Smartlead Webhook Event Handling Matrix
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {data.event_branches.map((b, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--bg-input)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                flexWrap: 'wrap',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Zap size={16} color="var(--primary)" />
                <span style={{ fontWeight: 700, fontSize: '0.86rem' }}>{b.event}</span>
              </div>

              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{b.action}</div>

              <span
                style={{
                  fontSize: '0.72rem',
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: 'white',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {b.target_state}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* State Machine 17 States */}
      <div className="card">
        <h3 style={{ fontSize: '0.98rem', fontWeight: 700, marginBottom: '12px' }}>
          Managed Outreach States ({data.all_states.length})
        </h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {data.all_states.map((st) => (
            <span
              key={st}
              style={{
                fontSize: '0.72rem',
                padding: '4px 9px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {st}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
