// Stage 3: Evidence Correlator — merges findings from 4 parallel subagents
import { StageShell, ConfidenceBadge, StatusBadge } from './shared'
import type { SubagentFinding } from '../../api/types'

interface Props { findings: SubagentFinding[] }

export default function EvidenceCorrelatorStage({ findings }: Props) {
  return (
    <StageShell
      stageNumber={3}
      label="evidence-correlator skill"
      title="Subagent Findings"
      description="4 subagents ran in parallel (explore mode — read-only)"
    >
      <div className="flex flex-col gap-2">
        {findings.map((f) => (
          <div
            key={f.agent}
            className="rounded-md border border-zinc-800 bg-zinc-900/50 p-3"
          >
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <p className="font-mono text-xs font-semibold text-zinc-200">{f.agent}</p>
              <div className="flex items-center gap-2">
                <StatusBadge status="done" />
                <ConfidenceBadge level={f.confidence} />
              </div>
            </div>
            <p className="text-[11px] text-zinc-500">
              <span className="text-zinc-600">Focus: </span>{f.focus}
            </p>
            <p className="mt-1 text-xs text-zinc-300">{f.finding}</p>
          </div>
        ))}
      </div>
    </StageShell>
  )
}
