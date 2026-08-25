import React from 'react';

interface BadgeProps {
  type: 'priority' | 'approval' | 'qa' | 'icp' | 'personalization' | 'evidence' | 'email_safety' | 'email_status';
  value: string;
}

export const Badge: React.FC<BadgeProps> = ({ type, value }) => {
  let className = 'badge ';

  if (type === 'email_status') {
    const norm = (value || '').toUpperCase();
    if (norm === 'VERIFIED' || norm === 'VALID' || norm === 'EVIDENCE_VERIFIED') {
      return <span className="badge badge-verified">🟢 Verified</span>;
    } else if (norm === 'UNVERIFIED' || norm === 'PATTERN_CONFIRMED' || norm === 'CATCHALL_UNVERIFIED') {
      return <span className="badge badge-p2">🟡 Unverified</span>;
    } else if (norm === 'NO_EMAIL' || norm === 'NO_EMAIL_PERSISTED' || norm === 'INVALID') {
      return <span className="badge badge-nosignal">⚪ No Email Found</span>;
    } else {
      return <span className="badge badge-p2">🟡 {value.replace('_', ' ')}</span>;
    }
  }

  if (type === 'priority') {
    if (value === 'P1') className += 'badge-p1';
    else if (value === 'P2') className += 'badge-p2';
    else className += 'badge-p3';
  } else if (type === 'approval') {
    if (value === 'APPROVED') className += 'badge-approved';
    else if (value === 'PENDING_REVIEW') className += 'badge-pending';
    else if (value === 'EDITED') className += 'badge-edited';
    else if (value === 'REJECTED') className += 'badge-rejected';
    else className += 'badge-blocked';
  } else if (type === 'qa') {
    if (value === 'PASS') className += 'badge-approved';
    else className += 'badge-rejected';
  } else if (type === 'icp') {
    if (value === 'QUALIFIED') className += 'badge-qualified';
    else className += 'badge-disqualified';
  } else if (type === 'personalization') {
    if (value === 'SIGNAL_VERIFIED') className += 'badge-verified';
    else className += 'badge-nosignal';
  } else if (type === 'evidence') {
    if (value === 'VERIFIED') className += 'badge-verified';
    else if (value === 'ESTIMATED') className += 'badge-p2';
    else if (value === 'INFERRED') className += 'badge-edited';
    else className += 'badge-nosignal';
  } else if (type === 'email_safety') {
    if (value === 'VALID' || value === 'VERIFIED' || value === 'PATTERN_CONFIRMED' || value === 'EVIDENCE_VERIFIED') className += 'badge-verified';
    else if (value === 'INVALID' || value === 'MALFORMED') className += 'badge-rejected';
    else if (value === 'BOUNCED' || value === 'INVALID_BOUNCED') className += 'badge-blocked';
    else if (value === 'SUPPRESSED' || value === 'OPT_OUT') className += 'badge-blocked';
    else className += 'badge-p2';
  }

  return <span className={className}>{value.replace('_', ' ')}</span>;
};
