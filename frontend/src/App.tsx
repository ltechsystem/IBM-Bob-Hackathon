import { useEffect, useState } from 'react'
import type { PipelineResult } from './api/types'
import { fetchOrRunIncident } from './api/client'

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
import { BobAvatar } from './components/icons/StatusIcon'

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

// Default incident request — used when no stored result is found
const DEFAULT_REQUEST = {
  id: 'INC-2024-001',
  title: "GET /users/{user_id} crashes with AttributeError",
  severity: 'P1' as const,
  service: 'user-service',
  errorType: 'AttributeError',
  errorMessage: "'NoneType' object has no attribute 'name'",
  affectedEndpoint: 'GET /users/{user_id}',
  logPath: 'app/logs/app.log',
  rawLog: '',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Animate step statuses sequentially to show the pipeline "running". */
function animateSteps(
  setStatuses: React.Dispatch<React.SetStateAction<Record<string, AgentStatus>>>,
  onDone: () => void
) {
  const stepIds = PIPELINE_STEPS.map((s) => s.id)
  let i = 0
  const interval = setInterval(() => {
    if (i >= stepIds.length) {
      clearInterval(interval)
      onDone()
      return
    }
    const currentId = stepIds[i]
    setStatuses((prev) => ({ ...prev, [currentId]: 'running' }))
    i++
  }, 200)
  return interval
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [data, setData] = useState<PipelineResult | null>(null)
  const [statuses, setStatuses] = useState<Record<string, AgentStatus>>(ALL_PENDING)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setStatuses(ALL_PENDING)

    // Animate steps to 'running' while we wait for the API
    const interval = animateSteps(setStatuses, () => {
      // If all steps animated to running but API hasn't resolved yet, keep running
    })

    fetchOrRunIncident(DEFAULT_REQUEST)
      .then((result) => {
        clearInterval(interval)
        setData(result)
        setStatuses(ALL_DONE)
      })
      .catch((err: unknown) => {
        clearInterval(interval)
        setStatuses(ALL_PENDING)
        setError(err instanceof Error ? err.message : String(err))
      })

    return () => clearInterval(interval)
  }, [])

  // Use dynamic incident data from the API response when available, otherwise fall back
  const incidentId = data?.incident.id ?? DEFAULT_REQUEST.id
  const incidentTitle = data?.incident.title ?? DEFAULT_REQUEST.title
  const incidentSeverity = data?.incident.severity ?? DEFAULT_REQUEST.severity

  return (
    <div className="min-h-screen bg-zinc-950 p-6 font-mono text-zinc-100">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="mx-auto mb-8 max-w-5xl">
        {/* Top brand bar */}
        <div className="flex items-center gap-3 mb-4">
          <img
            src="/logos/logo-compact.svg"
            alt="Victim Application"
            width={48}
            height={48}
            className="h-12 w-12 shrink-0"
            style={{ display: 'block' }}
          />
          <div>
            <div className="flex items-center gap-2">
              <span
                className="font-mono text-xl font-bold tracking-tight"
                style={{
                  background: 'linear-gradient(90deg, #00f2fe 0%, #818cf8 55%, #4facfe 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                Victim Application
              </span>
              <span className="font-mono text-xs text-zinc-500 uppercase tracking-widest pt-0.5">
                · Debug Agent
              </span>
            </div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600 mt-0.5">
              Python · FastAPI · SQLite · IBM Granite
            </p>
          </div>

          <div className="flex-1" />

          {/* Bob avatar + live indicator */}
          <div className="flex items-center gap-2">
            <BobAvatar size="h-8 w-8" />
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 font-mono text-xs text-cyan-400">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
              LIVE
            </span>
          </div>
        </div>

        {/* Divider */}
        <div
          className="h-px w-full mb-4 rounded"
          style={{ background: 'linear-gradient(90deg, #06b6d4 0%, #6366f1 60%, transparent 100%)', opacity: 0.3 }}
        />

        {/* Incident title + badge — driven by API data once available */}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-lg font-bold text-zinc-100">
            Incident Pipeline
          </h1>
          <span className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 font-mono text-sm text-red-400">
            {incidentId}
          </span>
          <span className="rounded border border-zinc-700 bg-zinc-800/60 px-2 py-0.5 font-mono text-xs text-zinc-400">
            {incidentSeverity}
          </span>
        </div>
        <p className="mt-1 font-mono text-sm text-zinc-500">
          {incidentTitle}
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
            <LogViewerStage logPath={DEFAULT_REQUEST.logPath ?? 'app/logs/app.log'} lines={data.logLines} />
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
            <ReportGeneratorStage
              brief={data.incident}
              rootCause={data.rootCause}
              diffHunk={data.diffHunk}
              testResults={data.testResults}
            />
          </main>
        )}
      </div>
    </div>
  )
}
