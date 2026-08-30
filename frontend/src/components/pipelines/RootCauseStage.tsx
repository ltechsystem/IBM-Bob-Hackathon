// Stage 4: Root Cause Analyzer
import { StageShell, ConfidenceBadge } from './shared'
import { StatusIcon } from '../icons/StatusIcon'
import type { RootCause } from '../../api/types'

interface Props { rootCause: RootCause }

export default function RootCauseStage({ rootCause }: Props) {
  const isLowConfidence = rootCause.confidence === 'LOW' || rootCause.confidence === 'MEDIUM'

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

      {/* Confidence gate alert — shown when human review is recommended */}
      {isLowConfidence && (
        <div className="flex items-start gap-2.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
          <StatusIcon kind="warning" size="h-4 w-4" />
          <p className="font-mono text-xs text-amber-300">
            Confidence gate — human review recommended before applying this fix.
          </p>
        </div>
      )}
    </StageShell>
  )
}
