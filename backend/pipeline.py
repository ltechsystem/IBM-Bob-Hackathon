"""
backend/pipeline.py — Orchestrates each stage of the debug pipeline.

This module is intentionally separate from the FastAPI app so that it can
be tested without spinning up an HTTP server.
"""

from __future__ import annotations

from typing import Dict, List

from backend import llm
from backend.models import (
    DiffHunk,
    EvidenceFile,
    IncidentBrief,
    LogLine,
    PipelineResult,
    RootCause,
    RunIncidentRequest,
    SubagentFinding,
    TestResult,
)


def run_pipeline(req: RunIncidentRequest) -> PipelineResult:
    """
    Execute all 8 pipeline stages in order and return the full result.

    Stages
    ------
    0. Parse raw log → list[LogLine]
    1. Build incident brief → IncidentBrief
    2. Collect evidence → list[EvidenceFile]
    3. Correlate evidence (4 subagents) → list[SubagentFinding]
    4. Analyse root cause → RootCause
    5. Recommend fix → DiffHunk
    6. Implement fix (same hunk, no additional LLM call needed)
    7. Validate tests → list[TestResult]
    """

    req_dict = req.model_dump()

    # Stage 0 — Log viewer
    raw_log_lines: list[dict] = llm.parse_log_lines(req.rawLog, req.logPath)
    log_lines = [LogLine(**l) for l in raw_log_lines]

    # Stage 1 — Incident intake
    brief_dict: dict = llm.build_incident_brief(req_dict)
    incident = IncidentBrief(**brief_dict)

    # Stage 2 — Evidence collector
    evidence_dicts: list[dict] = llm.collect_evidence(brief_dict, raw_log_lines)
    evidence_files = [EvidenceFile(**e) for e in evidence_dicts]

    # Stage 3 — Evidence correlator (×4 subagents)
    finding_dicts: list[dict] = llm.correlate_evidence(brief_dict, evidence_dicts)
    subagent_findings = [SubagentFinding(**f) for f in finding_dicts]

    # Stage 4 — Root cause analyser
    root_cause_dict: dict = llm.analyze_root_cause(brief_dict, finding_dicts)
    root_cause = RootCause(**root_cause_dict)

    # Stage 5 & 6 — Fix recommender + implementer (same diff hunk)
    hunk_dict: dict = llm.recommend_fix(root_cause_dict)
    diff_hunk = DiffHunk(**hunk_dict)

    # Stage 7 — Test validator
    test_result_dicts: list[dict] = llm.validate_tests(hunk_dict)
    test_results = [TestResult(**t) for t in test_result_dicts]

    return PipelineResult(
        incident=incident,
        logLines=log_lines,
        evidenceFiles=evidence_files,
        subagentFindings=subagent_findings,
        rootCause=root_cause,
        diffHunk=diff_hunk,
        testResults=test_results,
    )
