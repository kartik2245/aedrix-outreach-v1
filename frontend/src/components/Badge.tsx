import React from 'react';

interface BadgeProps {
  type: 'priority' | 'approval' | 'qa' | 'icp' | 'personalization' | 'evidence';
  value: string;
}

export const Badge: React.FC<BadgeProps> = ({ type, value }) => {
  let className = 'badge ';

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
  }

  return <span className={className}>{value.replace('_', ' ')}</span>;
};
