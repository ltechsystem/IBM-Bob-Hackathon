// Stage 5: Fix Recommender — shows before/after diff
import { StageShell } from './shared'
import type { DiffHunk } from '../../api/types'

interface Props { hunk: DiffHunk }

export default function FixRecommenderStage({ hunk }: Props) {
  return (
    <StageShell
      stageNumber={5}
      label="fix-recommender skill"
      title="Proposed Fix"
      description={`Minimal before/after diff — ${hunk.file}`}
    >
      <div className="overflow-auto rounded-md border border-zinc-800 font-mono text-xs">
        {/* Before */}
        <div className="border-b border-zinc-800 bg-zinc-900/80 px-3 py-1 text-[10px] uppercase tracking-wider text-zinc-600">
          Before — {hunk.file}:{hunk.lineNumber}
        </div>
        <pre className="bg-red-950/20 p-3 leading-relaxed">
          {hunk.before.map((line, i) => (
            <div key={i} className="text-red-400">
              <span className="mr-2 select-none text-zinc-700">{String(hunk.lineNumber + i).padStart(2, ' ')} −</span>
              {line}
            </div>
          ))}
        </pre>
        {/* After */}
        <div className="border-y border-zinc-800 bg-zinc-900/80 px-3 py-1 text-[10px] uppercase tracking-wider text-zinc-600">
          After
        </div>
        <pre className="bg-emerald-950/20 p-3 leading-relaxed">
          {hunk.after.map((line, i) => (
            <div
              key={i}
              className={
                i >= hunk.before.length - 1
                  ? 'text-emerald-400'
                  : 'text-zinc-500'
              }
            >
              <span className="mr-2 select-none text-zinc-700">
                {String(hunk.lineNumber + i).padStart(2, ' ')}{' '}
                {i >= hunk.before.length - 1 ? '+' : ' '}
              </span>
              {line}
            </div>
          ))}
        </pre>
      </div>
    </StageShell>
  )
}
