"""
research_pipeline.py
Master Research-to-Lead-Intelligence Ingestion Pipeline (Python 3.12).

Flow:
Deepline Export Sample (data/deepline_export_sample.json)
      ↓
Deepline Export Adapter (src/deepline_export_adapter.py)
      ↓
Research Leads Buffer (data/research_leads.json)
      ↓
Research Normalizer (src/research_normalizer.py)
      ↓
Evidence Validator (src/evidence_validator.py)
      ↓
Lead Intelligence Engine (src/lead_intelligence.py)
      ↓
Final Lead Intelligence Output (data/final_lead_intelligence.json)
"""

import json
import os
from typing import Dict, Any, List, Optional
from src.deepline_export_adapter import DeeplineExportAdapter
from src.research_normalizer import ResearchNormalizer
from src.evidence_validator import EvidenceValidator
from src.lead_intelligence import LeadIntelligenceEngine
from src.models import LeadIntelligenceOutput


class ResearchPipeline:
    def __init__(self):
        self.adapter = DeeplineExportAdapter()
        self.normalizer = ResearchNormalizer()
        self.validator = EvidenceValidator()
        self.intel_engine = LeadIntelligenceEngine()

    def process_dataset(self, raw_dataset: Any) -> List[LeadIntelligenceOutput]:
        """Executes the full pipeline on a raw Deepline export dataset."""
        adapted = self.adapter.adapt(raw_dataset)
        normalized = self.normalizer.normalize(adapted)
        validated = self.validator.validate(normalized)
        return [self.intel_engine.process_lead(record) for record in validated]

    def run_and_save(
        self,
        arg1: str,
        arg2: Optional[str] = None,
        arg3: Optional[str] = None
    ) -> List[LeadIntelligenceOutput]:
        """Reads raw Deepline JSON, processes through adapter and pipeline, and saves final_lead_intelligence.json."""
        deepline_export_path = arg1
        research_leads_buffer_path = arg2
        final_output_path = arg3

        if not final_output_path:
            final_output_path = arg2
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            research_leads_buffer_path = os.path.join(base_dir, "data", "research_leads.json")

        adapted_records = self.adapter.adapt(deepline_export_path, research_leads_buffer_path)
        final_dataset = self.process_dataset(adapted_records)

        os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump(by_alias=True, mode="json") for item in final_dataset], f, indent=2)

        return final_dataset
