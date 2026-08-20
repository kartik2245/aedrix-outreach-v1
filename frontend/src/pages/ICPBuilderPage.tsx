import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle,
  XCircle,
  Edit3,
  Search,
  Layers,
  ArrowRight,
  ShieldCheck,
  Loader2,
  FileText,
  Plus,
  Trash2,
  SlidersHorizontal,
} from 'lucide-react';
import { api } from '../services/api';
import {
  ICPApprovalRecord,
  DeeplineDiscoveryPreviewResponse,
  DeeplineRunResultResponse,
} from '../types';
import { Modal } from '../components/Modal';

interface ICPBuilderPageProps {
  onNavigateToLeads: (campaignId?: string) => void;
  showToast: (type: 'success' | 'error' | 'warning' | 'info', text: string) => void;
}

export const ICPBuilderPage: React.FC<ICPBuilderPageProps> = ({
  onNavigateToLeads,
  showToast,
}) => {
  // Mode Selector: 'claude' vs 'manual'
  const [creationMode, setCreationMode] = useState<'claude' | 'manual'>('claude');

  // --- Claude Form State ---
  const [campaignName, setCampaignName] = useState('UK Construction Enterprise Digital');
  const [campaignObjective, setCampaignObjective] = useState(
    'I want to target medium and large construction companies in the UK that could benefit from Aedrix. Focus on companies with digital transformation initiatives and target Digital Directors, IT Directors, Operations Directors and Business Improvement Directors.'
  );
  const [productContext, setProductContext] = useState(
    'Aedrix is a modular construction management SaaS platform for UK main contractors covering pre-construction document control, drawing versioning, site manpower tracking, and commercial control.'
  );
  const [geography, setGeography] = useState('United Kingdom');
  const [industry, setIndustry] = useState('Commercial Construction, Building, Civil Engineering, Infrastructure');
  const [companySize, setCompanySize] = useState('50+ employees or £10M+ revenue');
  const [minEmployees, setMinEmployees] = useState(50);
  const [minRevenue, setMinRevenue] = useState(10.0);
  const [personas, setPersonas] = useState(
    'Digital Director, IT Director, Operations Director, Business Improvement Director, Chief Information Officer (CIO)'
  );
  const [positiveSignals, setPositiveSignals] = useState(
    'Active digital transformation roadmap, BIM adoption, multi-site regional projects'
  );
  const [negativeSignals, setNegativeSignals] = useState(
    'Single-site residential micro-subcontractor, pure software vendor'
  );
  const [hardDisqualifiers, setHardDisqualifiers] = useState(
    'Outside United Kingdom, Non-construction sector, Under 50 employees and <£10M revenue'
  );
  const [campaignExclusions, setCampaignExclusions] = useState(
    'Active CRM deal, Global suppression opt-out, Contacted within past 60 days'
  );
  const [vocContext, setVocContext] = useState(
    'Pre-construction document control and drawing versioning latency across regional sites.'
  );

  // --- Manual Form State ---
  const [manualCampaignName, setManualCampaignName] = useState('UK Tier 1 & 2 Main Contractors (Direct)');
  const [manualObjective, setManualObjective] = useState(
    'Target UK main contractors with active commercial project pipelines to drive adoption of Aedrix pre-construction risk control.'
  );
  const [manualIndustry, setManualIndustry] = useState('Commercial Construction, Civil Engineering, Infrastructure');
  const [manualGeography, setManualGeography] = useState('United Kingdom');
  const [manualMinEmployees, setManualMinEmployees] = useState(50);
  const [manualMaxEmployees, setManualMaxEmployees] = useState<number | undefined>(undefined);
  const [manualMinRevenue, setManualMinRevenue] = useState(10.0);
  const [manualMaxRevenue, setManualMaxRevenue] = useState<number | undefined>(undefined);
  const [manualTechnologies, setManualTechnologies] = useState('BIM, Autodesk Construction Cloud, Procore, Viewpoint');

  // Dynamic lists for manual form
  const [manualPersonas, setManualPersonas] = useState<Array<{ title: string; seniority: string }>>([
    { title: 'Head of Pre-Construction', seniority: 'Head / Director' },
    { title: 'Commercial Director', seniority: 'Director' },
    { title: 'Operations Director', seniority: 'Director' },
    { title: 'Managing Director', seniority: 'Executive / C-Level' },
  ]);

  const [manualQualRules, setManualQualRules] = useState<string[]>([
    'Active commercial project pipeline with regional delivery',
    'Tier 1 or Tier 2 UK main contractor scale',
    'Document control and drawing versioning latency challenges',
  ]);

  const [manualHardDisqualifiers, setManualHardDisqualifiers] = useState<string[]>([
    'Operating exclusively outside United Kingdom',
    'Non-construction sector or pure residential domestic micro-builder',
    'Company size under 50 employees and under £10M turnover',
  ]);

  const [manualExclusions, setManualExclusions] = useState<string[]>([
    'Active opportunity currently in CRM sales pipeline',
    'Global email suppression or opt-out match',
    'Contacted by sales team within past 60 days',
  ]);

  const [manualVocAngle, setManualVocAngle] = useState(
    'Pre-construction document control, drawing revision risk, and commercial milestone disputes across multi-site teams.'
  );
  const [manualAdditionalNotes, setManualAdditionalNotes] = useState(
    'Manually authored ICP for direct commercial outreach pilot.'
  );

  // Flow State
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);
  const [activeRecord, setActiveRecord] = useState<ICPApprovalRecord | null>(null);
  const [requestedCount, setRequestedCount] = useState(100);
  const [previewData, setPreviewData] = useState<DeeplineDiscoveryPreviewResponse | null>(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [isRunningDiscovery, setIsRunningDiscovery] = useState(false);
  const [runResult, setRunResult] = useState<DeeplineRunResultResponse | null>(null);

  // Edit Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editMinEmployees, setEditMinEmployees] = useState(50);
  const [editMinRevenue, setEditMinRevenue] = useState(10.0);
  const [editPersonas, setEditPersonas] = useState('');
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  // Load existing active ICP if present
  useEffect(() => {
    const loadLatest = async () => {
      try {
        const list = await api.getICPs();
        if (list && list.length > 0) {
          setActiveRecord(list[list.length - 1]);
        }
      } catch (err) {
        console.error('Failed to load ICPs:', err);
      }
    };
    loadLatest();
  }, []);

  const handleGenerateClaudeICP = async () => {
    try {
      setIsGenerating(true);
      setRunResult(null);
      const personaList = personas.split(',').map((p) => p.trim()).filter(Boolean);
      const posList = positiveSignals.split(',').map((s) => s.trim()).filter(Boolean);
      const negList = negativeSignals.split(',').map((s) => s.trim()).filter(Boolean);
      const hardList = hardDisqualifiers.split(',').map((s) => s.trim()).filter(Boolean);
      const exclList = campaignExclusions.split(',').map((s) => s.trim()).filter(Boolean);

      const res = await api.generateICP({
        campaign_name: campaignName,
        campaign_objective: campaignObjective,
        product_context: productContext,
        geography,
        industry,
        company_size: companySize,
        target_personas: personaList,
        minimum_employees: minEmployees,
        minimum_revenue: minRevenue,
        positive_signals: posList,
        negative_signals: negList,
        hard_disqualifiers: hardList,
        campaign_exclusions: exclList,
        voc_context: vocContext,
      });

      setActiveRecord(res.record);
      showToast('success', res.message);
    } catch (err: any) {
      showToast('error', `ICP Generation failed: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateManualICP = async () => {
    if (!manualCampaignName.trim()) {
      showToast('error', 'Campaign Name is required.');
      return;
    }
    if (!manualObjective.trim()) {
      showToast('error', 'Campaign Objective is required.');
      return;
    }

    try {
      setIsSubmittingManual(true);
      setRunResult(null);

      const personaTitles = manualPersonas
        .map((p) => (p.seniority ? `${p.title} (${p.seniority})` : p.title).trim())
        .filter(Boolean);

      const seniorityList = Array.from(
        new Set(manualPersonas.map((p) => p.seniority).filter(Boolean))
      );

      const techList = manualTechnologies
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const indList = manualIndustry
        .split(',')
        .map((i) => i.trim())
        .filter(Boolean);

      const res = await api.createManualICP({
        campaign_name: manualCampaignName,
        campaign_objective: manualObjective,
        industry: manualIndustry,
        industries: indList,
        geography: manualGeography,
        minimum_employees: manualMinEmployees,
        maximum_employees: manualMaxEmployees,
        minimum_revenue: manualMinRevenue,
        maximum_revenue: manualMaxRevenue,
        target_personas: personaTitles,
        seniority_levels: seniorityList,
        technologies: techList,
        qualification_rules: manualQualRules.filter((r) => r.trim().length > 0),
        hard_disqualification_rules: manualHardDisqualifiers.filter((r) => r.trim().length > 0),
        campaign_exclusion_rules: manualExclusions.filter((r) => r.trim().length > 0),
        additional_notes: manualAdditionalNotes,
        voc_context: manualVocAngle,
      });

      setActiveRecord(res.record);
      showToast('success', res.message);
    } catch (err: any) {
      showToast('error', `Manual ICP Creation failed: ${err.message}`);
    } finally {
      setIsSubmittingManual(false);
    }
  };

  const handleApproveICP = async () => {
    if (!activeRecord) return;
    try {
      const updated = await api.approveICP(activeRecord.icp_id, 'HUMAN_OPERATOR');
      setActiveRecord(updated);
      showToast('success', `ICP '${activeRecord.name}' approved! Ready for Deepline discovery.`);
    } catch (err: any) {
      showToast('error', `Approval failed: ${err.message}`);
    }
  };

  const handleRejectICP = async () => {
    if (!activeRecord) return;
    try {
      const updated = await api.rejectICP(activeRecord.icp_id, rejectReason || 'Operator rejected', 'HUMAN_OPERATOR');
      setActiveRecord(updated);
      setRejectModalOpen(false);
      showToast('warning', `ICP marked REJECTED.`);
    } catch (err: any) {
      showToast('error', `Rejection failed: ${err.message}`);
    }
  };

  const openEditModal = () => {
    if (!activeRecord) return;
    setEditMinEmployees(activeRecord.effective_icp.minimum_employees || 50);
    setEditMinRevenue(activeRecord.effective_icp.minimum_revenue || 10.0);
    setEditPersonas(activeRecord.effective_icp.target_personas.join(', '));
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!activeRecord) return;
    try {
      const personaList = editPersonas.split(',').map((p) => p.trim()).filter(Boolean);
      const updated = await api.editICP(
        activeRecord.icp_id,
        {
          minimum_employees: editMinEmployees,
          minimum_revenue: editMinRevenue,
          target_personas: personaList,
        },
        'HUMAN_OPERATOR'
      );
      setActiveRecord(updated);
      setEditModalOpen(false);
      showToast('warning', `ICP updated. Status changed to EDITED (Requires re-approval).`);
    } catch (err: any) {
      showToast('error', `Edit failed: ${err.message}`);
    }
  };

  const handlePreviewDeepline = async () => {
    if (!activeRecord) return;
    try {
      const preview = await api.previewDeeplineDiscovery(activeRecord.icp_id, requestedCount);
      setPreviewData(preview);
      setPreviewModalOpen(true);
    } catch (err: any) {
      showToast('error', `Preview failed: ${err.message}`);
    }
  };

  const handleRunDeepline = async () => {
    if (!activeRecord) return;
    try {
      setIsRunningDiscovery(true);
      setRunResult(null);
      const res = await api.runDeeplineDiscovery(activeRecord.icp_id, requestedCount);
      setRunResult(res);
      showToast('success', res.message);
    } catch (err: any) {
      showToast('error', `Deepline discovery failed: ${err.message}`);
    } finally {
      setIsRunningDiscovery(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.14), rgba(168, 85, 247, 0.08))',
          borderColor: 'rgba(99, 102, 241, 0.3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <Sparkles size={22} color="var(--primary)" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>
            Dynamic ICP Designer & Deepline Discovery
          </h2>
        </div>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', margin: 0 }}>
          Create targeting criteria either through AI assistance or direct manual definition.
          Both converge into the same structured profile, human review gate, and automated Deepline discovery pipeline.
        </p>
      </div>

      {/* Creation Mode Switcher */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          background: 'rgba(15, 23, 42, 0.6)',
          padding: '8px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          width: 'fit-content',
        }}
      >
        <button
          onClick={() => setCreationMode('claude')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '0.86rem',
            fontWeight: 700,
            cursor: 'pointer',
            background:
              creationMode === 'claude'
                ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                : 'transparent',
            color: creationMode === 'claude' ? '#ffffff' : 'var(--text-muted)',
            transition: 'all 0.2s ease',
          }}
        >
          <Sparkles size={16} />
          <span>✨ Generate with Claude</span>
        </button>

        <button
          onClick={() => setCreationMode('manual')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '0.86rem',
            fontWeight: 700,
            cursor: 'pointer',
            background:
              creationMode === 'manual'
                ? 'linear-gradient(135deg, #0ea5e9, #06b6d4)'
                : 'transparent',
            color: creationMode === 'manual' ? '#ffffff' : 'var(--text-muted)',
            transition: 'all 0.2s ease',
          }}
        >
          <SlidersHorizontal size={16} />
          <span>✏️ Create Manually</span>
        </button>
      </div>

      {/* Main Grid: Builder Form (Left) & Proposed Output (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '20px' }}>
        {/* Left: Active Creation Form */}
        {creationMode === 'claude' ? (
          /* Claude AI Form */
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                AI-Assisted ICP Generation
              </h3>
              <span style={{ fontSize: '0.74rem', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                CLAUDE AI
              </span>
            </div>

            {/* Section 1: Campaign */}
            <div>
              <span style={{ fontSize: '0.74rem', color: 'var(--primary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section 1 — Campaign Context
              </span>
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label className="form-label">Campaign Name</label>
                  <input
                    type="text"
                    className="form-input"
                    value={campaignName}
                    onChange={(e) => setCampaignName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Campaign Objective (Natural Language Requirement)</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={campaignObjective}
                    onChange={(e) => setCampaignObjective(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Product / Service Context (Aedrix Value Prop)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={productContext}
                    onChange={(e) => setProductContext(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Target */}
            <div>
              <span style={{ fontSize: '0.74rem', color: 'var(--info)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section 2 — Geography, Sector & Scale
              </span>
              <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label className="form-label">Target Geography</label>
                  <input
                    type="text"
                    className="form-input"
                    value={geography}
                    onChange={(e) => setGeography(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Target Industries</label>
                  <input
                    type="text"
                    className="form-input"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Company Size Descriptors</label>
                  <input
                    type="text"
                    className="form-input"
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Min Employees</label>
                  <input
                    type="number"
                    className="form-input"
                    value={minEmployees}
                    onChange={(e) => setMinEmployees(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="form-label">Min Revenue (£M)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={minRevenue}
                    onChange={(e) => setMinRevenue(Number(e.target.value))}
                  />
                </div>
              </div>
              <div style={{ marginTop: '10px' }}>
                <label className="form-label">Target Decision-Maker Personas</label>
                <input
                  type="text"
                  className="form-input"
                  value={personas}
                  onChange={(e) => setPersonas(e.target.value)}
                />
              </div>
            </div>

            {/* Section 3: Signals & Exclusions */}
            <div>
              <span style={{ fontSize: '0.74rem', color: 'var(--warning)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section 3 — Signals, Disqualifiers & Exclusions
              </span>
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label className="form-label">Positive Signals (Boost Priority)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={positiveSignals}
                    onChange={(e) => setPositiveSignals(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Negative Signals (Reduce Priority)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={negativeSignals}
                    onChange={(e) => setNegativeSignals(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Hard Disqualification Rules</label>
                  <input
                    type="text"
                    className="form-input"
                    value={hardDisqualifiers}
                    onChange={(e) => setHardDisqualifiers(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Campaign Exclusion Rules</label>
                  <input
                    type="text"
                    className="form-input"
                    value={campaignExclusions}
                    onChange={(e) => setCampaignExclusions(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Section 4: VoC */}
            <div>
              <span style={{ fontSize: '0.74rem', color: '#a855f7', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section 4 — Voice of Customer Research Angle
              </span>
              <div style={{ marginTop: '8px' }}>
                <textarea
                  className="form-textarea"
                  rows={2}
                  value={vocContext}
                  onChange={(e) => setVocContext(e.target.value)}
                />
              </div>
            </div>

            <button
              className="btn btn-demo-run"
              style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
              onClick={handleGenerateClaudeICP}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Designing ICP with Claude...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate Structured ICP with Claude</span>
                </>
              )}
            </button>
          </div>
        ) : (
          /* Structured Manual Form */
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
                Manual ICP Specification Form
              </h3>
              <span style={{ fontSize: '0.74rem', background: 'rgba(14, 165, 233, 0.15)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                MANUAL AUTHORING
              </span>
            </div>

            {/* Section A: Campaign */}
            <div>
              <span style={{ fontSize: '0.74rem', color: 'var(--primary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section A — Campaign Definition
              </span>
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label className="form-label">Campaign Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={manualCampaignName}
                    onChange={(e) => setManualCampaignName(e.target.value)}
                    placeholder="e.g. UK Tier 1 & 2 Main Contractors"
                  />
                </div>
                <div>
                  <label className="form-label">Campaign Objective *</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={manualObjective}
                    onChange={(e) => setManualObjective(e.target.value)}
                    placeholder="Target contractors with active project delivery pipelines..."
                  />
                </div>
              </div>
            </div>

            {/* Section B: Company Profile */}
            <div>
              <span style={{ fontSize: '0.74rem', color: 'var(--info)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section B — Target Company Profile
              </span>
              <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label className="form-label">Target Industry</label>
                  <input
                    type="text"
                    className="form-input"
                    value={manualIndustry}
                    onChange={(e) => setManualIndustry(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Target Geography</label>
                  <input
                    type="text"
                    className="form-input"
                    value={manualGeography}
                    onChange={(e) => setManualGeography(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Min Employees</label>
                  <input
                    type="number"
                    className="form-input"
                    value={manualMinEmployees}
                    onChange={(e) => setManualMinEmployees(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="form-label">Max Employees (Optional)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={manualMaxEmployees || ''}
                    onChange={(e) => setManualMaxEmployees(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="No upper limit"
                  />
                </div>
                <div>
                  <label className="form-label">Min Turnover (£M)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={manualMinRevenue}
                    onChange={(e) => setManualMinRevenue(Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="form-label">Max Turnover (£M) (Optional)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={manualMaxRevenue || ''}
                    onChange={(e) => setManualMaxRevenue(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="No upper limit"
                  />
                </div>
              </div>
              <div style={{ marginTop: '10px' }}>
                <label className="form-label">Target Technologies / Keywords</label>
                <input
                  type="text"
                  className="form-input"
                  value={manualTechnologies}
                  onChange={(e) => setManualTechnologies(e.target.value)}
                  placeholder="e.g. BIM, Procore, Autodesk, Viewpoint"
                />
              </div>
            </div>

            {/* Section C: Target Personas */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: '#10b981', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Section C — Decision-Maker Personas
                </span>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                  onClick={() => setManualPersonas([...manualPersonas, { title: '', seniority: 'Director' }])}
                >
                  <Plus size={12} /> Add Persona
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {manualPersonas.map((p, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Job Title (e.g. Head of Pre-Construction)"
                      value={p.title}
                      onChange={(e) => {
                        const updated = [...manualPersonas];
                        updated[idx].title = e.target.value;
                        setManualPersonas(updated);
                      }}
                      style={{ flex: 2 }}
                    />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Seniority (e.g. Director)"
                      value={p.seniority}
                      onChange={(e) => {
                        const updated = [...manualPersonas];
                        updated[idx].seniority = e.target.value;
                        setManualPersonas(updated);
                      }}
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '6px 8px', color: '#f87171' }}
                      onClick={() => setManualPersonas(manualPersonas.filter((_, i) => i !== idx))}
                      disabled={manualPersonas.length <= 1}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Section D: Qualification Rules */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Section D — Qualification Rules (Positive Signals)
                </span>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                  onClick={() => setManualQualRules([...manualQualRules, ''])}
                >
                  <Plus size={12} /> Add Rule
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {manualQualRules.map((rule, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      type="text"
                      className="form-input"
                      value={rule}
                      onChange={(e) => {
                        const updated = [...manualQualRules];
                        updated[idx] = e.target.value;
                        setManualQualRules(updated);
                      }}
                      placeholder="e.g. Active commercial project pipeline with regional delivery"
                    />
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '6px 8px', color: '#f87171' }}
                      onClick={() => setManualQualRules(manualQualRules.filter((_, i) => i !== idx))}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Section E: Hard Disqualification Rules */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: '#f87171', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Section E — Hard Disqualification Rules
                </span>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                  onClick={() => setManualHardDisqualifiers([...manualHardDisqualifiers, ''])}
                >
                  <Plus size={12} /> Add Disqualifier
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {manualHardDisqualifiers.map((rule, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      type="text"
                      className="form-input"
                      value={rule}
                      onChange={(e) => {
                        const updated = [...manualHardDisqualifiers];
                        updated[idx] = e.target.value;
                        setManualHardDisqualifiers(updated);
                      }}
                      placeholder="e.g. Operating exclusively outside United Kingdom"
                    />
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '6px 8px', color: '#f87171' }}
                      onClick={() => setManualHardDisqualifiers(manualHardDisqualifiers.filter((_, i) => i !== idx))}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Section F: Campaign Exclusions */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--warning)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Section F — Campaign Exclusions
                </span>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                  onClick={() => setManualExclusions([...manualExclusions, ''])}
                >
                  <Plus size={12} /> Add Exclusion
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {manualExclusions.map((rule, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input
                      type="text"
                      className="form-input"
                      value={rule}
                      onChange={(e) => {
                        const updated = [...manualExclusions];
                        updated[idx] = e.target.value;
                        setManualExclusions(updated);
                      }}
                      placeholder="e.g. Active opportunity currently in CRM sales pipeline"
                    />
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{ padding: '6px 8px', color: '#f87171' }}
                      onClick={() => setManualExclusions(manualExclusions.filter((_, i) => i !== idx))}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Section G: Additional Notes & VoC Angle */}
            <div>
              <span style={{ fontSize: '0.74rem', color: '#c084fc', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Section G — Voice of Customer Angle & Notes
              </span>
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label className="form-label">Voice of Customer Angle / Pain Points</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={manualVocAngle}
                    onChange={(e) => setManualVocAngle(e.target.value)}
                    placeholder="Document control latency, drawing versioning risks, subcontractor billing disputes..."
                  />
                </div>
                <div>
                  <label className="form-label">Operator Notes</label>
                  <input
                    type="text"
                    className="form-input"
                    value={manualAdditionalNotes}
                    onChange={(e) => setManualAdditionalNotes(e.target.value)}
                    placeholder="Additional context or campaign tags..."
                  />
                </div>
              </div>
            </div>

            <button
              className="btn btn-primary"
              style={{
                width: '100%',
                justifyContent: 'center',
                padding: '12px',
                background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
              }}
              onClick={handleCreateManualICP}
              disabled={isSubmittingManual}
            >
              {isSubmittingManual ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Enrolling Manual ICP...</span>
                </>
              ) : (
                <>
                  <SlidersHorizontal size={16} />
                  <span>Create & Enroll Manual ICP</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Right: Proposed ICP Review Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {activeRecord ? (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>{activeRecord.effective_icp.name}</h3>

                    {/* Source Origin Badge */}
                    <span
                      style={{
                        fontSize: '0.72rem',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)',
                        background:
                          activeRecord.source === 'MANUAL' || activeRecord.effective_icp.source === 'MANUAL'
                            ? 'rgba(14, 165, 233, 0.15)'
                            : 'rgba(99, 102, 241, 0.15)',
                        color:
                          activeRecord.source === 'MANUAL' || activeRecord.effective_icp.source === 'MANUAL'
                            ? '#38bdf8'
                            : '#818cf8',
                        border: '1px solid rgba(255,255,255,0.1)',
                        fontWeight: 700,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {activeRecord.source === 'MANUAL' || activeRecord.effective_icp.source === 'MANUAL' ? (
                        <>
                          <SlidersHorizontal size={11} />
                          <span>MANUAL</span>
                        </>
                      ) : (
                        <>
                          <Sparkles size={11} />
                          <span>CLAUDE AI</span>
                        </>
                      )}
                    </span>

                    {/* Status Badge */}
                    <span
                      style={{
                        fontSize: '0.72rem',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)',
                        background:
                          activeRecord.status === 'APPROVED'
                            ? 'rgba(16, 185, 129, 0.15)'
                            : activeRecord.status === 'PENDING_REVIEW'
                            ? 'rgba(245, 158, 11, 0.15)'
                            : activeRecord.status === 'EDITED'
                            ? 'rgba(168, 85, 247, 0.15)'
                            : 'rgba(239, 68, 68, 0.15)',
                        color:
                          activeRecord.status === 'APPROVED'
                            ? '#34d399'
                            : activeRecord.status === 'PENDING_REVIEW'
                            ? '#fbbf24'
                            : activeRecord.status === 'EDITED'
                            ? '#c084fc'
                            : '#f87171',
                        border: '1px solid rgba(255,255,255,0.1)',
                        fontWeight: 700,
                      }}
                    >
                      {activeRecord.status.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      v{activeRecord.version}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                    {activeRecord.effective_icp.campaign_description}
                  </p>
                </div>

                {/* Approval Actions */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  {activeRecord.status !== 'APPROVED' && (
                    <button className="btn btn-success" onClick={handleApproveICP}>
                      <CheckCircle size={14} />
                      <span>Approve ICP</span>
                    </button>
                  )}
                  <button className="btn btn-outline" onClick={openEditModal}>
                    <Edit3 size={14} />
                    <span>Edit Criteria</span>
                  </button>
                  {activeRecord.status !== 'REJECTED' && (
                    <button className="btn btn-outline" onClick={() => setRejectModalOpen(true)}>
                      <XCircle size={14} />
                      <span>Reject</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Criteria Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', fontSize: '0.8rem' }}>
                <div style={{ background: 'var(--bg-input)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', textTransform: 'uppercase' }}>Geography</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{activeRecord.effective_icp.geography?.primary_country || 'United Kingdom'}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', textTransform: 'uppercase' }}>Scale Threshold</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                    {activeRecord.effective_icp.minimum_employees || 50}+ Emp / £{activeRecord.effective_icp.minimum_revenue || 10}M+
                  </div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', textTransform: 'uppercase' }}>Target Industries</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.76rem' }}>
                    {activeRecord.effective_icp.industries?.slice(0, 2).join(', ') || 'Commercial Construction'}
                  </div>
                </div>
              </div>

              {/* Personas */}
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Target Personas</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                  {activeRecord.effective_icp.target_personas.map((p, idx) => (
                    <span key={idx} style={{ fontSize: '0.76rem', background: 'rgba(99, 102, 241, 0.12)', color: '#818cf8', padding: '3px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(99, 102, 241, 0.25)' }}>
                      {p}
                    </span>
                  ))}
                </div>
              </div>

              {/* Signals & Rules */}
              <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>
                  <strong>Positive Signals:</strong> {activeRecord.effective_icp.positive_signals?.join(' • ') || 'None specified'}
                </div>
                <div>
                  <strong>Hard Disqualifiers:</strong> {activeRecord.effective_icp.hard_disqualifiers?.map((d) => d.description).join(' • ') || 'None specified'}
                </div>
                {activeRecord.effective_icp.voc_context && (
                  <div>
                    <strong>VoC Angle:</strong> <span style={{ color: 'var(--text-muted)' }}>{activeRecord.effective_icp.voc_context}</span>
                  </div>
                )}
                {activeRecord.effective_icp.reasoning && (
                  <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '10px', borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)', fontSize: '0.78rem', lineHeight: 1.5 }}>
                    <strong>Origin Context:</strong> {activeRecord.effective_icp.reasoning}
                  </div>
                )}
              </div>

              {/* Post-Approval Deepline Discovery Launch Panel */}
              {activeRecord.status === 'APPROVED' && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '16px',
                    background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.08))',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                    <ShieldCheck size={18} color="var(--success)" />
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#34d399' }}>
                      ICP Approved — Ready for Deepline Lead Discovery
                    </h4>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '14px' }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Target Volume:</span>
                    {[100, 250, 500, 1000].map((cnt) => (
                      <button
                        key={cnt}
                        className={`btn ${requestedCount === cnt ? 'btn-primary' : 'btn-outline'}`}
                        style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                        onClick={() => setRequestedCount(cnt)}
                      >
                        {cnt} Leads
                      </button>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button className="btn btn-outline" onClick={handlePreviewDeepline}>
                      <Search size={14} />
                      <span>Preview Deepline Run</span>
                    </button>
                    <button
                      className="btn btn-success"
                      onClick={handleRunDeepline}
                      disabled={isRunningDiscovery}
                    >
                      {isRunningDiscovery ? (
                        <>
                          <Loader2 size={14} className="animate-spin" />
                          <span>Discovering Leads...</span>
                        </>
                      ) : (
                        <>
                          <Layers size={14} />
                          <span>Run Deepline Discovery ({requestedCount} Leads)</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: '64px', color: 'var(--text-dim)' }}>
              <FileText size={32} style={{ margin: '0 auto 12px auto', opacity: 0.4 }} />
              <p>No ICP generated yet. Choose either "Generate with Claude" or "Create Manually" to create an ICP for review.</p>
            </div>
          )}

          {/* Discovery Run Results */}
          {runResult && (
            <div className="card" style={{ borderColor: 'var(--success)', animation: 'modalIn 0.2s ease-out' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle size={20} color="var(--success)" />
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 800 }}>Deepline Discovery Complete</h3>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => onNavigateToLeads(runResult.result.campaign_id)}
                >
                  <span>View Discovered Leads</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', textAlign: 'center' }}>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Discovered</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{runResult.result.summary.discovered}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>ICP Qualified</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--success)' }}>{runResult.result.summary.qualified}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>P1 Priority</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f87171' }}>{runResult.result.summary.p1_count}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>P2 Priority</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fbbf24' }}>{runResult.result.summary.p2_count}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>P3 Priority</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#94a3b8' }}>{runResult.result.summary.p3_count}</div>
                </div>
              </div>

              <div style={{ marginTop: '12px', fontSize: '0.76rem', color: 'var(--text-dim)' }}>
                Run ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{runResult.result.run_id}</span> • Safety Mode: {runResult.result.safety_mode}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit ICP Configuration"
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setEditModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSaveEdit}>
              Save & Require Re-Approval
            </button>
          </>
        }
      >
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          Modifying criteria invalidates prior approval, increments version, and resets status to <strong>EDITED</strong>.
        </p>

        <div>
          <label className="form-label">Minimum Employee Count</label>
          <input
            type="number"
            className="form-input"
            value={editMinEmployees}
            onChange={(e) => setEditMinEmployees(Number(e.target.value))}
          />
        </div>

        <div>
          <label className="form-label">Minimum Revenue (£M)</label>
          <input
            type="number"
            className="form-input"
            value={editMinRevenue}
            onChange={(e) => setEditMinRevenue(Number(e.target.value))}
          />
        </div>

        <div>
          <label className="form-label">Target Personas (comma-separated)</label>
          <input
            type="text"
            className="form-input"
            value={editPersonas}
            onChange={(e) => setEditPersonas(e.target.value)}
          />
        </div>
      </Modal>

      {/* Reject Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject ICP"
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setRejectModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={handleRejectICP}>
              Confirm Rejection
            </button>
          </>
        }
      >
        <label className="form-label">Reason for Rejection</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. Scope too broad, target personas misaligned"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      </Modal>

      {/* Preview Modal */}
      <Modal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        title="Deepline Discovery Specification Preview"
        footer={
          <button className="btn btn-primary" onClick={() => setPreviewModalOpen(false)}>
            Close Preview
          </button>
        }
      >
        {previewData && (
          <pre
            style={{
              background: 'var(--bg-input)',
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              overflowX: 'auto',
              maxHeight: '380px',
            }}
          >
            {JSON.stringify(previewData, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
};
