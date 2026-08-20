import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Server,
  Lock,
  FileCode,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { SystemStatusResponse } from '../types';

export const SystemSafetyPage: React.FC = () => {
  const [data, setData] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const res = await api.getSystemStatus();
        setData(res);
      } catch (err) {
        console.error('Failed to load system status:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div>Loading system safety status...</div>;
  if (!data) return <div>Failed to load system status.</div>;

  const isLiveSending = data.safety_flags['SEND_EMAILS'] && data.safety_flags['PRODUCTION_SEND_CONFIRMATION'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Safety Alert Header */}
      {isLiveSending ? (
        <div
          className="card"
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            borderColor: 'rgba(239, 68, 68, 0.4)',
            color: '#fca5a5',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <AlertTriangle size={20} color="var(--danger)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f87171' }}>
              WARNING: Production Sending Unlocked
            </h3>
          </div>
          <p style={{ fontSize: '0.84rem' }}>
            SEND_EMAILS=true and PRODUCTION_SEND_CONFIRMATION=true. Live prospect outreach is enabled in Smartlead.
          </p>
        </div>
      ) : (
        <div
          className="card"
          style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(99, 102, 241, 0.08))',
            borderColor: 'rgba(16, 185, 129, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <ShieldCheck size={20} color="var(--success)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              Production Safety Gates Enforced
            </h3>
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
            SEND_EMAILS is disabled. The system will not send live emails or activate Smartlead campaigns without explicit operator confirmation.
          </p>
        </div>
      )}

      {/* Integration Matrix */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Server size={18} color="var(--primary)" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Integration Status Matrix</h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {data.integrations.map((item, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{item.name}</span>
                <span style={{ fontSize: '0.7rem', padding: '2px 7px', borderRadius: 'var(--radius-sm)', background: item.status === 'CONNECTED' || item.status === 'CONFIGURED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)', color: item.status === 'CONNECTED' || item.status === 'CONFIGURED' ? '#34d399' : '#fbbf24', fontWeight: 600 }}>
                  {item.status}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                MODE: {item.mode}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Safety Flags & Masked Configuration */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        {/* Safety Flags */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Lock size={18} color="var(--warning)" />
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700 }}>Active Safety Flags</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.84rem' }}>
            {Object.entries(data.safety_flags).map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{k}</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: v === true ? 'var(--success)' : v === false ? '#94a3b8' : 'var(--primary)',
                  }}
                >
                  {String(v).toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Masked Secrets & Environment */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <FileCode size={18} color="var(--info)" />
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700 }}>Masked Configuration Audit</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
            {Object.entries(data.masked_env).map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{k}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: '#818cf8', fontWeight: 600 }}>
                  {v}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Audit Log Stream */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <Activity size={18} color="var(--primary)" />
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700 }}>Recent Structured Audit Logs</h3>
        </div>

        {data.recent_logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
            No audit logs recorded yet. Run a demo pipeline or approval action to generate entries.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '360px', overflowY: 'auto' }}>
            {data.recent_logs.map((log, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.78rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                  </span>
                  <span style={{ fontWeight: 700, color: log.status === 'SUCCESS' ? 'var(--success)' : log.status === 'ERROR' ? 'var(--danger)' : 'var(--primary)' }}>
                    {log.action}
                  </span>
                  {log.company && (
                    <span style={{ color: 'var(--text-muted)' }}>({log.company})</span>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '10px', color: 'var(--text-dim)' }}>
                  <span>Status: <strong>{log.status}</strong></span>
                  {log.reviewer && <span>Reviewer: {log.reviewer}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
