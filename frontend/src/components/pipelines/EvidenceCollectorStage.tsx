// Stage 2: Evidence Collector — lists relevant files found by the agent
import { StageShell } from './shared'
import type { EvidenceFile } from '../../api/types'

const REL_STYLE: Record<EvidenceFile['relevance'], string> = {
  HIGH:   'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  MEDIUM: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  LOW:    'text-zinc-400 bg-zinc-700/30 border-zinc-700',
}

interface Props { files: EvidenceFile[] }

export default function EvidenceCollectorStage({ files }: Props) {
  return (
    <StageShell
      stageNumber={2}
      label="evidence-collector skill"
      title="Evidence Manifest"
      description="Files identified as relevant to the incident"
    >
      <ul className="flex flex-col gap-1.5">
        {files.map((f) => (
          <li key={f.path} className="flex items-start gap-3 rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-2">
            <span className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase ${REL_STYLE[f.relevance]}`}>
              {f.relevance}
            </span>
            <div>
              <code className="text-xs text-zinc-200">{f.path}</code>
              <p className="mt-0.5 text-[11px] text-zinc-500">{f.reason}</p>
            </div>
          </li>
        ))}
      </ul>
    </StageShell>
  )
}
