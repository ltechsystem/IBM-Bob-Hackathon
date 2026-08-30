// Stage 6: Fix Implementer — confirms the diff was applied
import { StageShell } from './shared'
import type { DiffHunk } from '../../api/types'

interface Props { hunk: DiffHunk }

export default function FixImplementerStage({ hunk }: Props) {
  // Lines added in "after" that are not present in "before"
  const addedLines = hunk.after.slice(hunk.before.length - 1)

  return (
    <StageShell
      stageNumber={6}
      label="fix-implementer skill"
      title="Fix Applied"
      description="Diff applied safely — change confirmed"
    >
      <div className="flex items-center gap-3 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
        <div>
          <p className="font-mono text-sm font-semibold text-emerald-300">
            Patch applied successfully
          </p>
          <p className="mt-0.5 font-mono text-xs text-zinc-500">
            +{addedLines.length} line{addedLines.length !== 1 ? 's' : ''} added to{' '}
            <code className="text-amber-400">{hunk.file}</code>
          </p>
        </div>
      </div>
      <div className="rounded-md border border-zinc-800 bg-zinc-900/50 p-3 font-mono text-xs">
        <p className="mb-2 text-[10px] uppercase tracking-wider text-zinc-600">Changed lines</p>
        {addedLines.map((line, i) => (
          <div key={i} className="text-emerald-400">
            <span className="mr-2 select-none text-zinc-700">+ </span>{line}
          </div>
        ))}
      </div>
    </StageShell>
  )
}
