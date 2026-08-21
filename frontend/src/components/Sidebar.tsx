import React from 'react';
import {
  LayoutDashboard,
  Users,
  Sparkles,
  Search,
  CheckSquare,
  GitBranch,
  ShieldCheck,
  Building2,
  Send,
} from 'lucide-react';
import { DashboardStats } from '../types';

export type NavTab =
  | 'dashboard'
  | 'leads'
  | 'icp-builder'
  | 'discovery'
  | 'approvals'
  | 'campaign'
  | 'staging'
  | 'system';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  stats?: DashboardStats;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  stats,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">
          <Building2 size={20} />
        </div>
        <div className="logo-text">
          <h1>Aedrix</h1>
          <span>AI Outreach Platform</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'icp-builder' ? 'active' : ''}`}
          onClick={() => onSelectTab('icp-builder')}
        >
          <Sparkles size={18} color="var(--primary)" />
          <span>ICP Builder</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'discovery' ? 'active' : ''}`}
          onClick={() => onSelectTab('icp-builder')}
        >
          <Search size={18} />
          <span>Lead Discovery</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'leads' ? 'active' : ''}`}
          onClick={() => onSelectTab('leads')}
        >
          <Users size={18} />
          <span>Leads</span>
          {stats && stats.total_leads > 0 && (
            <span className="nav-badge">{stats.total_leads}</span>
          )}
        </button>

        <button
          className={`nav-item ${activeTab === 'approvals' ? 'active' : ''}`}
          onClick={() => onSelectTab('approvals')}
        >
          <CheckSquare size={18} />
          <span>Email Approvals</span>
          {stats && stats.pending_approvals > 0 && (
            <span
              className="nav-badge"
              style={{ background: 'var(--warning)', color: '#000', fontWeight: 700 }}
            >
              {stats.pending_approvals}
            </span>
          )}
        </button>

        <button
          className={`nav-item ${activeTab === 'campaign' ? 'active' : ''}`}
          onClick={() => onSelectTab('campaign')}
        >
          <GitBranch size={18} />
          <span>Campaigns</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'staging' ? 'active' : ''}`}
          onClick={() => onSelectTab('staging')}
        >
          <Send size={18} />
          <span>Smartlead</span>
          {stats && stats.approved_leads > 0 && (
            <span
              className="nav-badge"
              style={{ background: 'var(--success)', color: '#000', fontWeight: 700 }}
            >
              {stats.approved_leads}
            </span>
          )}
        </button>

        <button
          className={`nav-item ${activeTab === 'system' ? 'active' : ''}`}
          onClick={() => onSelectTab('system')}
        >
          <ShieldCheck size={18} />
          <span>Settings</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className="mode-pill">
          <div>
            <span className="mode-dot"></span>
            <span style={{ fontWeight: 600 }}>{stats?.safety?.mode_display || 'DEMO / DRY RUN'}</span>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>v1.0</span>
        </div>
      </div>
    </aside>
  );
};
