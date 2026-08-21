import React, { useState, useEffect } from 'react';
import { Sidebar, NavTab } from './components/Sidebar';
import { Header } from './components/Header';
import { ToastContainer, ToastMessage } from './components/Toast';
import { DashboardPage } from './pages/DashboardPage';
import { LeadsPage } from './pages/LeadsPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { ICPBuilderPage } from './pages/ICPBuilderPage';
import { ApprovalQueuePage } from './pages/ApprovalQueuePage';
import { CampaignFlowPage } from './pages/CampaignFlowPage';
import { SmartleadStagingPage } from './pages/SmartleadStagingPage';
import { SystemSafetyPage } from './pages/SystemSafetyPage';
import { api } from './services/api';
import { DashboardStats, ApprovalRecord } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (type: 'success' | 'error' | 'warning' | 'info', text: string) => {
    const id = `${Date.now()}_${Math.random()}`;
    setToasts((prev) => [...prev, { id, type, text }]);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const refreshAllData = async () => {
    try {
      const [statsRes, approvalsRes] = await Promise.all([
        api.getDashboardStats(),
        api.getApprovals(),
      ]);
      setStats(statsRes);
      setApprovals(approvalsRes);
    } catch (err) {
      console.error('Failed to refresh data:', err);
    }
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  const getPageTitle = () => {
    if (selectedLeadId) return 'Lead Intelligence Dossier';
    switch (activeTab) {
      case 'dashboard':
        return 'Outreach Operations Dashboard';
      case 'leads':
        return 'Leads Directory';
      case 'icp-builder':
        return 'ICP Builder & Lead Discovery';
      case 'approvals':
        return 'Email Approvals';
      case 'campaign':
        return 'Outreach Campaigns';
      case 'staging':
        return 'Smartlead Delivery Staging';
      case 'system':
        return 'System Settings';
      default:
        return 'Aedrix';
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setSelectedLeadId(null);
          setActiveTab(tab);
          refreshAllData();
        }}
        stats={stats || undefined}
      />

      <div className="main-wrapper">
        <Header
          pageTitle={getPageTitle()}
          safety={stats?.safety}
          onDemoCompleted={refreshAllData}
          showToast={showToast}
        />

        <main className="content-body">
          {selectedLeadId ? (
            <LeadDetailPage
              leadId={selectedLeadId}
              onBack={() => setSelectedLeadId(null)}
              showToast={showToast}
            />
          ) : activeTab === 'dashboard' ? (
            <DashboardPage
              stats={stats}
              approvals={approvals}
              onNavigateToLeads={() => setActiveTab('leads')}
              onNavigateToApprovals={() => setActiveTab('approvals')}
              onNavigateToStaging={() => setActiveTab('staging')}
              onSelectLead={(id) => setSelectedLeadId(id)}
            />
          ) : activeTab === 'leads' ? (
            <LeadsPage onSelectLead={(id) => setSelectedLeadId(id)} />
          ) : activeTab === 'icp-builder' ? (
            <ICPBuilderPage
              onNavigateToLeads={() => {
                setActiveTab('leads');
                refreshAllData();
              }}
              showToast={showToast}
            />
          ) : activeTab === 'approvals' ? (
            <ApprovalQueuePage
              approvals={approvals}
              onRefresh={refreshAllData}
              onSelectLead={(id) => setSelectedLeadId(id)}
              showToast={showToast}
            />
          ) : activeTab === 'campaign' ? (
            <CampaignFlowPage />
          ) : activeTab === 'staging' ? (
            <SmartleadStagingPage />
          ) : (
            <SystemSafetyPage />
          )}
        </main>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};
