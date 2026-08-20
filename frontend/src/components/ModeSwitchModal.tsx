import React, { useState } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2, X } from 'lucide-react';
import { api } from '../services/api';

interface ModeSwitchModalProps {
  isOpen: boolean;
  currentMode: string;
  onClose: () => void;
  onSuccess: () => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', text: string) => void;
}

export const ModeSwitchModal: React.FC<ModeSwitchModalProps> = ({
  isOpen,
  currentMode,
  onClose,
  onSuccess,
  showToast,
}) => {
  const [confirmText, setConfirmText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const isSwitchingToProd = currentMode !== 'PRODUCTION';

  const handleSwitch = async () => {
    if (isSwitchingToProd && confirmText.trim() !== 'ENABLE PRODUCTION') {
      showToast('error', 'You must type "ENABLE PRODUCTION" exactly to switch.');
      return;
    }

    try {
      setIsSubmitting(true);
      const targetMode = isSwitchingToProd ? 'PRODUCTION' : 'DEMO';
      await api.setAppMode(targetMode, confirmText.trim());
      showToast(
        'success',
        `Application mode switched to ${targetMode}. Human approval gates remain strictly active.`
      );
      setConfirmText('');
      onSuccess();
      onClose();
    } catch (err: any) {
      showToast('error', `Failed to switch mode: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-card"
        style={{ maxWidth: '520px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: isSwitchingToProd
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(245, 158, 11, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isSwitchingToProd ? '#f87171' : '#fbbf24',
              }}
            >
              {isSwitchingToProd ? <ShieldAlert size={20} /> : <AlertTriangle size={20} />}
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>
                {isSwitchingToProd ? 'Switch to PRODUCTION Mode' : 'Switch to DEMO Simulation Mode'}
              </h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
                Centralized environment mode management
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ padding: '1.25rem' }}>
          {isSwitchingToProd ? (
            <div>
              <div
                style={{
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1.25rem',
                }}
              >
                <div style={{ fontWeight: 600, color: '#fca5a5', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                  Safety Warnings for Production Mode:
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#cbd5e1', fontSize: '0.825rem', lineHeight: '1.5' }}>
                  <li>Real external services (Smartlead, Deepline, Claude) may become accessible if API keys are configured.</li>
                  <li><strong>Zero emails will be sent automatically.</strong> (<code>SEND_EMAILS=false</code> remains default).</li>
                  <li><strong>Human approval is still required</strong> for every campaign ICP and email draft.</li>
                  <li>Production database operations are committed directly to Supabase PostgreSQL.</li>
                </ul>
              </div>

              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, color: '#cbd5e1', marginBottom: '0.5rem' }}>
                Type <strong>ENABLE PRODUCTION</strong> to confirm:
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="ENABLE PRODUCTION"
                className="input-search"
                style={{
                  width: '100%',
                  borderColor: confirmText === 'ENABLE PRODUCTION' ? '#10b981' : 'rgba(255,255,255,0.15)',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                }}
                autoFocus
              />
            </div>
          ) : (
            <div>
              <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.5', margin: '0 0 1rem 0' }}>
                Switching to <strong>DEMO Mode</strong> activates full safe simulation:
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#94a3b8', fontSize: '0.825rem', lineHeight: '1.5' }}>
                <li>Zero real email sending</li>
                <li>Zero external paid API credits consumed</li>
                <li>Isolated demo dataset (UK construction contractor leads)</li>
                <li>Full UI workflow simulation preserved</li>
              </ul>
            </div>
          )}
        </div>

        <div
          className="modal-footer"
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.75rem',
            padding: '1rem 1.25rem',
            borderTop: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <button
            onClick={onClose}
            className="btn-secondary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSwitch}
            disabled={isSubmitting || (isSwitchingToProd && confirmText.trim() !== 'ENABLE PRODUCTION')}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '6px',
              border: 'none',
              background: isSwitchingToProd ? '#ef4444' : '#f59e0b',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: (isSwitchingToProd && confirmText.trim() !== 'ENABLE PRODUCTION') ? 'not-allowed' : 'pointer',
              opacity: (isSwitchingToProd && confirmText.trim() !== 'ENABLE PRODUCTION') ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <CheckCircle2 size={15} />
            <span>{isSwitchingToProd ? 'Activate Production Mode' : 'Activate Demo Mode'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
