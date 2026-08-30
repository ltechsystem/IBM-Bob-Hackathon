// Stage 8: Report Generator — final incident report summary
import { StageShell, ConfidenceBadge } from './shared'
import { StatusIcon } from '../icons/StatusIcon'
import type { IncidentBrief, RootCause, DiffHunk, TestResult } from '../../api/types'

interface Props {
  brief: IncidentBrief
  rootCause: RootCause
  diffHunk: DiffHunk
  testResults: TestResult[]
}

export default function ReportGeneratorStage({ brief, rootCause, diffHunk, testResults }: Props) {
  const addedLines = diffHunk.after.length - diffHunk.before.length
  const passed = testResults.filter((r) => r.status === 'PASSED').length
  const failed = testResults.filter((r) => r.status === 'FAILED').length
  const allPassed = failed === 0

  return (
    <StageShell
      stageNumber={8}
      label="report-generator skill"
      title="Incident Report"
      description="incident-report.md — generated"
    >
      {/* ── Hero banner: primary logo (Placement Matrix: Incident Brief Header) ── */}
      <div className="flex items-center justify-between rounded-md border border-zinc-800 bg-zinc-900/60 px-4 py-3">
        <img
          src="/logos/logo-primary.svg"
          alt="Victim Application — AI-Powered Debug Agent"
          width={320}
          height={68}
          className="h-12 w-auto shrink-0"
          style={{ display: 'block', maxWidth: '100%' }}
        />
        <div className="flex items-center gap-2 shrink-0">
          <StatusIcon kind={allPassed ? 'success' : 'warning'} size="h-4 w-4" decorative />
          <span className={`font-mono text-xs font-semibold ${allPassed ? 'text-emerald-400' : 'text-amber-400'}`}>
            {allPassed ? 'RESOLVED' : 'NEEDS REVIEW'}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-900/50 p-4 text-xs">
        <Row label="Incident"   value={`${brief.id} — ${brief.title}`} />
        <Row label="Service"    value={brief.service} />
        <Row label="Severity"   value={brief.severity} />
        <Row label="Endpoint"   value={brief.affectedEndpoint} />
        <Row label="Error"      value={brief.errorMessage} />
        <Row label="Reported"   value={brief.reportedAt} />
        <div className="flex items-center gap-2 border-t border-zinc-800 pt-3">
          <span className="text-zinc-600">Root Cause Confidence</span>
          <ConfidenceBadge level={rootCause.confidence} />
        </div>
        <Row
          label="Root Cause"
          value={`${rootCause.file}:${rootCause.line} — ${rootCause.summary}`}
        />
        <Row
          label="Fix"
          value={`+${addedLines} line${addedLines !== 1 ? 's' : ''} — ${diffHunk.file}:${diffHunk.lineNumber}`}
        />
        <Row
          label="Tests"
          value={`${passed} passed${failed > 0 ? `, ${failed} failed` : ' — ALL PASSED'}`}
          valueClass={allPassed ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}
        />
        <Row
          label="Status"
          value={allPassed ? 'RESOLVED' : 'NEEDS REVIEW'}
          valueClass={allPassed ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}
        />
      </div>
      <div className="flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        <p className="font-mono text-xs text-emerald-300">incident-report.md written successfully</p>
      </div>
    </StageShell>
  )
}

function Row({ label, value, valueClass = 'text-zinc-300' }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex gap-2">
      <span className="w-28 shrink-0 text-zinc-600">{label}</span>
      <span className={`font-mono ${valueClass}`}>{value}</span>
    </div>
  )
}
