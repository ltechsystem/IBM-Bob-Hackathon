// Stage 4: Root Cause Analyzer
import { StageShell, ConfidenceBadge } from './shared'
import type { RootCause } from '../../mockdata/incident'

interface Props { rootCause: RootCause }

export default function RootCauseStage({ rootCause }: Props) {
  return (
    <StageShell
      stageNumber={4}
      label="root-cause-analyzer skill"
      title="Root Cause Analysis"
      description="Determined from correlated evidence"
    >
      <div className="rounded-md border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="mb-3 flex items-center gap-3">
          <ConfidenceBadge level={rootCause.confidence} />
          <span className="font-mono text-sm font-semibold text-zinc-100">
            {rootCause.summary}
          </span>
        </div>
        <p className="mb-3 text-xs leading-relaxed text-zinc-400">
          {rootCause.explanation}
        </p>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span>File:</span>
          <code className="text-amber-400">{rootCause.file}</code>
          <span>·</span>
          <span>Line:</span>
          <code className="text-amber-400">{rootCause.line}</code>
        </div>
      </div>
    </StageShell>
  )
}
