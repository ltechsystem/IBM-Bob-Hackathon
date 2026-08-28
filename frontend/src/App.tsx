import { logLines } from './mockdata/logLines'
import {
  incidentBrief,
  evidenceFiles,
  subagentFindings,
  rootCause,
  diffHunk,
  testResults,
} from './mockdata/incident'

import StepTracker from './components/pipelines/stepTracker'
import { Connector } from './components/pipelines/shared'
import LogViewerStage from './components/pipelines/LogViewerStage'
import IncidentIntakeStage from './components/pipelines/IncidentIntakeStage'
import EvidenceCollectorStage from './components/pipelines/EvidenceCollectorStage'
import EvidenceCorrelatorStage from './components/pipelines/EvidenceCorrelatorStage'
import RootCauseStage from './components/pipelines/RootCauseStage'
import FixRecommenderStage from './components/pipelines/FixRecommenderStage'
import FixImplementerStage from './components/pipelines/FixImplementerStage'
import TestValidatorStage from './components/pipelines/TestValidatorStage'
import ReportGeneratorStage from './components/pipelines/ReportGeneratorStage'
import type { Step } from './components/pipelines/stepTracker'
import type { AgentStatus } from './components/pipelines/shared'

const PIPELINE_STEPS: Step[] = [
  { id: 'log-viewer',          label: 'Log Viewer' },
  { id: 'incident-intake',     label: 'Incident Intake' },
  { id: 'evidence-collector',  label: 'Evidence Collector' },
  { id: 'evidence-correlator', label: 'Evidence Correlator (×4 subagents)' },
  { id: 'root-cause',          label: 'Root Cause Analyzer' },
  { id: 'fix-recommender',     label: 'Fix Recommender' },
  { id: 'fix-implementer',     label: 'Fix Implementer' },
  { id: 'test-validator',      label: 'Test Validator' },
  { id: 'report-generator',    label: 'Report Generator' },
]

const ALL_DONE: Record<string, AgentStatus> = Object.fromEntries(
  PIPELINE_STEPS.map((s) => [s.id, 'done'])
)

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 p-6 font-mono text-zinc-100">
      {/* Header */}
      <header className="mx-auto mb-8 max-w-5xl">
        <p className="font-mono text-xs uppercase tracking-widest text-zinc-600">
          Bob Debug Agent · Python + FastAPI + SQLite
        </p>
        <h1 className="mt-1 text-2xl font-bold text-zinc-100">
          Incident Pipeline
          <span className="ml-3 rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 font-mono text-sm text-red-400">
            INC-2024-001
          </span>
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          GET /users/&#123;user_id&#125; → AttributeError: 'NoneType' object has no attribute 'name'
        </p>
      </header>

      <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[220px_1fr]">
        {/* Sidebar: step tracker */}
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <StepTracker steps={PIPELINE_STEPS} statuses={ALL_DONE} />
        </aside>

        {/* Pipeline stages */}
        <main className="flex flex-col gap-2">
          <LogViewerStage logPath="app/logs/app.log" lines={logLines} />
          <Connector />
          <IncidentIntakeStage brief={incidentBrief} />
          <Connector />
          <EvidenceCollectorStage files={evidenceFiles} />
          <Connector />
          <EvidenceCorrelatorStage findings={subagentFindings} />
          <Connector />
          <RootCauseStage rootCause={rootCause} />
          <Connector />
          <FixRecommenderStage hunk={diffHunk} />
          <Connector />
          <FixImplementerStage hunk={diffHunk} />
          <Connector />
          <TestValidatorStage results={testResults} />
          <Connector />
          <ReportGeneratorStage brief={incidentBrief} rootCause={rootCause} />
        </main>
      </div>
    </div>
  )
}
