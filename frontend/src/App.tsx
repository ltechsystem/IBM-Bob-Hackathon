import { useEffect, useState } from 'react'
import type {
  IncidentBrief,
  EvidenceFile,
  SubagentFinding,
  RootCause,
  DiffHunk,
  TestResult,
} from './mockdata/incident'
import type { LogLine } from './components/pipelines/LogViewerStage'

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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineResult {
  incident: IncidentBrief
  logLines: LogLine[]
  evidenceFiles: EvidenceFile[]
  subagentFindings: SubagentFinding[]
  rootCause: RootCause
  diffHunk: DiffHunk
  testResults: TestResult[]
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

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

const ALL_PENDING: Record<string, AgentStatus> = Object.fromEntries(
  PIPELINE_STEPS.map((s) => [s.id, 'pending'])
)

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchOrRunIncident(id: string): Promise<PipelineResult> {
  // Try to load an existing stored result first
  const existing = await fetch(`/api/incidents/${id}`)
  if (existing.ok) {
    return existing.json() as Promise<PipelineResult>
  }

  // Not found — run the pipeline
  const res = await fetch('/api/incidents/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id,
      title: "GET /users/{user_id} crashes with AttributeError",
      severity: 'P1',
      service: 'user-service',
      errorType: 'AttributeError',
      errorMessage: "'NoneType' object has no attribute 'name'",
      affectedEndpoint: 'GET /users/{user_id}',
      logPath: 'app/logs/app.log',
      rawLog: '',
    }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Pipeline failed: ${res.status} ${text}`)
  }
  return res.json() as Promise<PipelineResult>
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const INCIDENT_ID = 'INC-2024-001'

  const [data, setData] = useState<PipelineResult | null>(null)
  const [statuses, setStatuses] = useState<Record<string, AgentStatus>>(ALL_PENDING)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Animate steps to "running" then fetch
    setStatuses(ALL_PENDING)

    fetchOrRunIncident(INCIDENT_ID)
      .then((result) => {
        setData(result)
        setStatuses(ALL_DONE)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err))
      })
  }, [])

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
            {INCIDENT_ID}
          </span>
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          GET /users/&#123;user_id&#125; → AttributeError: 'NoneType' object has no attribute 'name'
        </p>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mx-auto mb-6 max-w-5xl rounded border border-red-500/40 bg-red-500/10 px-4 py-3">
          <p className="font-mono text-sm text-red-400">⚠ Backend error: {error}</p>
          <p className="mt-1 font-mono text-xs text-zinc-500">
            Make sure the FastAPI server is running:{' '}
            <code className="text-amber-400">uvicorn backend.app:app --reload</code>
          </p>
        </div>
      )}

      {/* Loading state */}
      {!data && !error && (
        <div className="mx-auto mb-6 max-w-5xl rounded border border-sky-500/30 bg-sky-500/10 px-4 py-3">
          <p className="font-mono text-sm text-sky-400 animate-pulse">⟳ Running pipeline…</p>
        </div>
      )}

      <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[220px_1fr]">
        {/* Sidebar: step tracker */}
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <StepTracker steps={PIPELINE_STEPS} statuses={statuses} />
        </aside>

        {/* Pipeline stages — rendered only after data arrives */}
        {data && (
          <main className="flex flex-col gap-2">
            <LogViewerStage logPath="app/logs/app.log" lines={data.logLines} />
            <Connector />
            <IncidentIntakeStage brief={data.incident} />
            <Connector />
            <EvidenceCollectorStage files={data.evidenceFiles} />
            <Connector />
            <EvidenceCorrelatorStage findings={data.subagentFindings} />
            <Connector />
            <RootCauseStage rootCause={data.rootCause} />
            <Connector />
            <FixRecommenderStage hunk={data.diffHunk} />
            <Connector />
            <FixImplementerStage hunk={data.diffHunk} />
            <Connector />
            <TestValidatorStage results={data.testResults} />
            <Connector />
            <ReportGeneratorStage brief={data.incident} rootCause={data.rootCause} />
          </main>
        )}
      </div>
    </div>
  )
}
