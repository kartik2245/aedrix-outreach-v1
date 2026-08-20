import React, { useEffect } from 'react';
import { CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  text: string;
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  );
};

const ToastItem: React.FC<{ toast: ToastMessage; onDismiss: () => void }> = ({
  toast,
  onDismiss,
}) => {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle size={18} color="var(--success)" />;
      case 'error':
        return <XCircle size={18} color="var(--danger)" />;
      case 'warning':
        return <AlertTriangle size={18} color="var(--warning)" />;
      default:
        return <Info size={18} color="var(--info)" />;
    }
  };

  return (
    <div
      className="toast"
      style={{
        borderLeft: `4px solid ${
          toast.type === 'success'
            ? 'var(--success)'
            : toast.type === 'error'
            ? 'var(--danger)'
            : toast.type === 'warning'
            ? 'var(--warning)'
            : 'var(--info)'
        }`,
      }}
      onClick={onDismiss}
    >
      {getIcon()}
      <span>{toast.text}</span>
    </div>
  );
};
