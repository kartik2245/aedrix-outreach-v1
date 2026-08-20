import React, { useState, useEffect } from 'react';
import { Search, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../services/api';
import { LeadsListResponse } from '../types';
import { Badge } from '../components/Badge';

interface LeadsPageProps {
  onSelectLead: (leadId: string) => void;
}

export const LeadsPage: React.FC<LeadsPageProps> = ({ onSelectLead }) => {
  const [data, setData] = useState<LeadsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [icpStatus, setIcpStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [approvalStatus, setApprovalStatus] = useState('');
  const [personalizationStatus, setPersonalizationStatus] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('outreach_priority_index');
  const [sortOrder, setSortOrder] = useState('desc');

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const res = await api.getLeads({
        search,
        icp_status: icpStatus,
        priority,
        approval_status: approvalStatus,
        personalization_status: personalizationStatus,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: 15,
      });
      setData(res);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [search, icpStatus, priority, approvalStatus, personalizationStatus, page, sortBy, sortOrder]);

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Controls Bar */}
      <div className="controls-bar">
        <div className="search-box">
          <Search size={16} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search company, contact, email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="filter-group">
          <select
            className="filter-select"
            value={icpStatus}
            onChange={(e) => {
              setIcpStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All ICP Statuses</option>
            <option value="QUALIFIED">QUALIFIED</option>
            <option value="HARD_DISQUALIFIED">HARD_DISQUALIFIED</option>
            <option value="CAMPAIGN_EXCLUDED">CAMPAIGN_EXCLUDED</option>
          </select>

          <select
            className="filter-select"
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Priorities</option>
            <option value="P1">P1 (Tier 1 Strategic)</option>
            <option value="P2">P2 (High Priority)</option>
            <option value="P3">P3 (Medium Priority)</option>
          </select>

          <select
            className="filter-select"
            value={approvalStatus}
            onChange={(e) => {
              setApprovalStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Approvals</option>
            <option value="PENDING_REVIEW">PENDING_REVIEW</option>
            <option value="APPROVED">APPROVED</option>
            <option value="EDITED">EDITED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="BLOCKED">BLOCKED</option>
          </select>

          <select
            className="filter-select"
            value={personalizationStatus}
            onChange={(e) => {
              setPersonalizationStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Signals</option>
            <option value="SIGNAL_VERIFIED">SIGNAL_VERIFIED</option>
            <option value="NO_STRONG_SIGNAL">NO_STRONG_SIGNAL</option>
          </select>
        </div>
      </div>

      {/* Leads Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('company')}>Company</th>
              <th onClick={() => handleSort('contact')}>Decision Maker</th>
              <th onClick={() => handleSort('qualification_status')}>ICP Status</th>
              <th onClick={() => handleSort('opportunity_score')}>Opp</th>
              <th onClick={() => handleSort('accessibility_score')}>Acc</th>
              <th onClick={() => handleSort('outreach_priority_index')}>Index</th>
              <th onClick={() => handleSort('priority')}>Priority</th>
              <th>Personalization</th>
              <th>Approval</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '32px' }}>
                  Loading leads...
                </td>
              </tr>
            ) : !data || data.items.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)' }}>
                  No leads matching search or filter criteria.
                </td>
              </tr>
            ) : (
              data.items.map((lead) => (
                <tr
                  key={lead.lead_id}
                  onClick={() => onSelectLead(lead.lead_id)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontWeight: 600 }}>{lead.company}</td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{lead.contact}</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)' }}>{lead.title}</div>
                  </td>
                  <td>
                    <Badge type="icp" value={lead.qualification_status} />
                  </td>
                  <td style={{ fontWeight: 600 }}>{lead.opportunity_score.toFixed(0)}</td>
                  <td style={{ fontWeight: 600 }}>{lead.accessibility_score.toFixed(0)}</td>
                  <td>
                    <span style={{ fontWeight: 700, color: 'var(--primary)' }}>
                      {lead.outreach_priority_index.toFixed(1)}
                    </span>
                  </td>
                  <td>
                    <Badge type="priority" value={lead.priority} />
                  </td>
                  <td>
                    <Badge type="personalization" value={lead.personalization_status} />
                  </td>
                  <td>
                    <Badge type="approval" value={lead.approval_status} />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '4px 10px', fontSize: '0.76rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectLead(lead.lead_id);
                      }}
                    >
                      <Eye size={13} />
                      <span>Dossier</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {(page - 1) * data.page_size + 1}–
            {Math.min(page * data.page_size, data.total)} of {data.total} leads
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-outline"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft size={14} />
              <span>Previous</span>
            </button>
            <button
              className="btn btn-outline"
              disabled={page >= data.total_pages}
              onClick={() => setPage(page + 1)}
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
