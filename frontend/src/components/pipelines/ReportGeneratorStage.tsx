// Stage 8: Report Generator — final incident report summary
import { StageShell, ConfidenceBadge } from './shared'
import type { IncidentBrief, RootCause } from '../../mockdata/incident'

interface Props { brief: IncidentBrief; rootCause: RootCause }

export default function ReportGeneratorStage({ brief, rootCause }: Props) {
  return (
    <StageShell
      stageNumber={8}
      label="report-generator skill"
      title="Incident Report"
      description="incident-report.md — generated"
    >
      <div className="flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-900/50 p-4 text-xs">
        <Row label="Incident"    value={`${brief.id} — ${brief.title}`} />
        <Row label="Service"     value={brief.service} />
        <Row label="Severity"    value={brief.severity} />
        <Row label="Endpoint"    value={brief.affectedEndpoint} />
        <Row label="Error"       value={brief.errorMessage} />
        <div className="flex items-center gap-2 border-t border-zinc-800 pt-3">
          <span className="text-zinc-600">Root Cause Confidence</span>
          <ConfidenceBadge level={rootCause.confidence} />
        </div>
        <Row label="Fix"         value="+2 lines — app/main.py:13 — added None-check + HTTP 404" />
        <Row label="Regression"  value="tests/test_users_fixed.py — ALL 4 PASSED" />
        <Row label="Status"      value="RESOLVED" valueClass="text-emerald-400 font-semibold" />
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
