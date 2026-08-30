// Stage 1: Incident Intake — parses raw incident into a structured brief
import { StageShell } from './shared'
import { StatusIcon } from '../icons/StatusIcon'
import type { IncidentBrief } from '../../api/types'

const SEVERITY_STYLE: Record<IncidentBrief['severity'], string> = {
  P1: 'border-red-500/40 bg-red-500/10 text-red-400',
  P2: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  P3: 'border-zinc-600 bg-zinc-800/40 text-zinc-400',
}

interface Props { brief: IncidentBrief }

export default function IncidentIntakeStage({ brief }: Props) {
  return (
    <StageShell
      stageNumber={1}
      label="incident-intake skill"
      title="Incident Brief"
      description="Raw incident parsed into structured fields"
    >
      <div className="grid grid-cols-2 gap-2 rounded-md border border-zinc-800 bg-zinc-900/60 p-4 text-xs sm:grid-cols-3">
        <Field label="Incident ID"     value={brief.id} />
        <Field label="Service"         value={brief.service} />
        <Field label="Reported At"     value={brief.reportedAt} />
        <Field label="Endpoint"        value={brief.affectedEndpoint} />
        <Field label="Error Type"      value={brief.errorType} />
        <div className="col-span-2 sm:col-span-3">
          <span className="text-zinc-600">Message — </span>
          <code className="text-red-400">{brief.errorMessage}</code>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {brief.severity === 'P1' && <StatusIcon kind="failure" size="h-3.5 w-3.5" decorative />}
        {brief.severity === 'P2' && <StatusIcon kind="warning" size="h-3.5 w-3.5" decorative />}
        {brief.severity === 'P3' && <StatusIcon kind="success" size="h-3.5 w-3.5" decorative />}
        <span className="text-xs text-zinc-600">Severity</span>
        <span className={`rounded border px-2.5 py-0.5 font-mono text-xs font-bold ${SEVERITY_STYLE[brief.severity]}`}>
          {brief.severity}
        </span>
      </div>
    </StageShell>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-zinc-600">{label}</p>
      <p className="mt-0.5 font-mono text-zinc-300">{value}</p>
    </div>
  )
}
