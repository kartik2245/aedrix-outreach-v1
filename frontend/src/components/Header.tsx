import React, { useState, useEffect } from 'react';
import { Play, ShieldCheck, MailCheck, Loader2, Database, RotateCcw, SlidersHorizontal } from 'lucide-react';
import { api } from '../services/api';
import { SafetyIndicators, DatabaseHealthResponse, ModeConfigResponse } from '../types';
import { ModeSwitchModal } from './ModeSwitchModal';

interface HeaderProps {
  pageTitle: string;
  safety?: SafetyIndicators;
  onDemoCompleted: () => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', text: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  pageTitle,
  safety,
  onDemoCompleted,
  showToast,
}) => {
  const [isRunningDemo, setIsRunningDemo] = useState(false);
  const [isResettingDemo, setIsResettingDemo] = useState(false);
  const [dbHealth, setDbHealth] = useState<DatabaseHealthResponse | null>(null);
  const [modeConfig, setModeConfig] = useState<ModeConfigResponse | null>(null);
  const [isModeModalOpen, setIsModeModalOpen] = useState(false);

  const fetchStatus = async () => {
    try {
      const health = await api.getDatabaseHealth();
      setDbHealth(health);
    } catch (e) {
      console.warn('Database health check warning:', e);
    }

    try {
      const mode = await api.getAppMode();
      setModeConfig(mode);
    } catch (e) {
      console.warn('Mode config check warning:', e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleRunDemo = async () => {
    try {
      setIsRunningDemo(true);
      const res = await api.runFullDemo();
      showToast('success', res.message);
      onDemoCompleted();
      fetchStatus();
    } catch (err: any) {
      showToast('error', `Demo execution failed: ${err.message}`);
    } finally {
      setIsRunningDemo(false);
    }
  };

  const handleResetDemo = async () => {
    if (!window.confirm('Are you sure you want to reset demo data? Only demo leads will be reset; production data is never touched.')) {
      return;
    }
    try {
      setIsResettingDemo(true);
      const res = await api.resetDemo();
      showToast('info', res.message);
      onDemoCompleted();
      fetchStatus();
    } catch (err: any) {
      showToast('error', `Demo reset failed: ${err.message}`);
    } finally {
      setIsResettingDemo(false);
    }
  };

  const isDemo = modeConfig ? modeConfig.demo_mode : (safety?.dry_run || !safety?.send_emails);

  return (
    <>
      <header className="top-bar">
        <div className="top-left">
          <h2 className="page-title">{pageTitle}</h2>
        </div>

        <div className="top-right">
          {/* Mode Badge & Switch Trigger */}
          {isDemo ? (
            <button
              className="safety-tag"
              onClick={() => setIsModeModalOpen(true)}
              style={{
                background: 'rgba(245, 158, 11, 0.12)',
                color: '#fbbf24',
                borderColor: 'rgba(245, 158, 11, 0.25)',
                cursor: 'pointer',
              }}
              title="DEMO MODE: Safe simulation active (Zero real emails, zero credit expenditure). Click to manage mode."
            >
              <ShieldCheck size={14} />
              <span>DEMO MODE 🟡 SAFE SIMULATION</span>
              <SlidersHorizontal size={11} style={{ opacity: 0.7, marginLeft: '2px' }} />
            </button>
          ) : (
            <button
              className="safety-tag"
              onClick={() => setIsModeModalOpen(true)}
              style={{
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                borderColor: 'rgba(16, 185, 129, 0.3)',
                cursor: 'pointer',
              }}
              title="PRODUCTION MODE: Live database active with strict human approval gates. Click to manage mode."
            >
              <ShieldCheck size={14} />
              <span>PRODUCTION MODE 🟢 LIVE</span>
              <SlidersHorizontal size={11} style={{ opacity: 0.7, marginLeft: '2px' }} />
            </button>
          )}

          {/* Database Health Badge */}
          {dbHealth?.connected ? (
            <div
              className="safety-tag"
              style={{
                background: 'rgba(59, 130, 246, 0.12)',
                color: '#60a5fa',
                borderColor: 'rgba(59, 130, 246, 0.25)',
              }}
              title={`Supabase PostgreSQL Primary Database (${dbHealth.latency_ms ? `${dbHealth.latency_ms}ms` : 'Healthy'})`}
            >
              <Database size={13} />
              <span>SUPABASE POSTGRESQL — CONNECTED</span>
            </div>
          ) : (
            <div
              className="safety-tag"
              style={{
                background: 'rgba(148, 163, 184, 0.12)',
                color: '#94a3b8',
                borderColor: 'rgba(148, 163, 184, 0.25)',
              }}
              title="Database offline: Using local JSON fallback"
            >
              <Database size={13} />
              <span>OFFLINE JSON STORE</span>
            </div>
          )}

          {/* Real Emails Dispatched Counter */}
          <div className="zero-emails-tag" title="Verification: Exact count of real prospect emails dispatched">
            <MailCheck size={14} />
            <span>REAL EMAILS SENT: {modeConfig?.real_emails_sent ?? safety?.real_emails_sent ?? 0}</span>
          </div>

          {/* Reset Demo Button (in Demo mode) */}
          {isDemo && (
            <button
              className="btn-secondary"
              onClick={handleResetDemo}
              disabled={isResettingDemo || isRunningDemo}
              style={{
                padding: '0.4rem 0.75rem',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                color: '#94a3b8',
              }}
              title="Safely resets demo leads and state (Never touches production records)"
            >
              {isResettingDemo ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RotateCcw size={13} />
              )}
              <span>Reset Demo</span>
            </button>
          )}

          {/* Run Full Demo Button */}
          <button
            className="btn-demo-run"
            onClick={handleRunDemo}
            disabled={isRunningDemo || isResettingDemo}
            title="Executes the complete simulated outreach pipeline (Campaign -> ICP -> Discovery -> Intelligence -> Drafts -> QA -> Staging)"
          >
            {isRunningDemo ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Simulating...</span>
              </>
            ) : (
              <>
                <Play size={14} fill="currentColor" />
                <span>Run Full Demo</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Mode Switch Safety Modal */}
      <ModeSwitchModal
        isOpen={isModeModalOpen}
        currentMode={modeConfig?.mode || 'DEMO'}
        onClose={() => setIsModeModalOpen(false)}
        onSuccess={() => {
          fetchStatus();
          onDemoCompleted();
        }}
        showToast={showToast}
      />
    </>
  );
};
