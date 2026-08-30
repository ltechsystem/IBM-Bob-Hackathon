// Sentinel Stage — displays IBM i RPG test classification results from Sentinel
import { StageShell } from './shared'
import type { SentinelClassification, SentinelVerdict } from '../../api/types'

interface Props {
  results: SentinelClassification[]
}

// ── Verdict badge ─────────────────────────────────────────────────────────────

const VERDICT_STYLE: Record<SentinelVerdict, string> = {
  STALE:                'border-amber-500/40 bg-amber-500/10 text-amber-400',
  REGRESSION:           'border-red-500/40   bg-red-500/10   text-red-400',
  NEW_COVERAGE_NEEDED:  'border-sky-500/40   bg-sky-500/10   text-sky-400',
  UNCERTAIN:            'border-zinc-500/40  bg-zinc-500/10  text-zinc-400',
}

const VERDICT_LABEL: Record<SentinelVerdict, string> = {
  STALE:                'Stale',
  REGRESSION:           'Regression',
  NEW_COVERAGE_NEEDED:  'New Coverage',
  UNCERTAIN:            'Uncertain',
}

function VerdictBadge({ verdict }: { verdict: SentinelVerdict }) {
  return (
    <span className={`shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase ${VERDICT_STYLE[verdict]}`}>
      {VERDICT_LABEL[verdict]}
    </span>
  )
}

// ── Action badge ──────────────────────────────────────────────────────────────

const ACTION_STYLE: Record<string, string> = {
  accepted:   'text-emerald-400',
  edited:     'text-sky-400',
  rejected:   'text-zinc-500',
  regression: 'text-red-400',
  skipped:    'text-zinc-500',
  no_patch:   'text-zinc-500',
}

function ActionLabel({ action }: { action?: string | null }) {
  if (!action) return null
  const style = ACTION_STYLE[action] ?? 'text-zinc-400'
  return (
    <span className={`font-mono text-[11px] ${style}`}>
      · {action}
    </span>
  )
}

// ── Confidence bar ────────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const colour = value >= 0.8 ? 'bg-emerald-500' : value >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full rounded-full ${colour}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[11px] text-zinc-500">{pct}%</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SentinelStage({ results }: Props) {
  return (
    <StageShell
      stageNumber={10}
      label="sentinel · IBM i RPG"
      title="Sentinel — RPG Test Classifications"
      description="Continuous test maintenance: Bob classifies each RPGUnit failure after a compile event."
    >
      {results.length === 0 ? (
        <p className="font-mono text-sm text-zinc-600 italic">
          No classifications yet — run Sentinel against an IBM i source member to see results here.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {results.map((r, i) => (
            <li
              key={r._db_id ?? i}
              className="flex flex-col gap-1.5 rounded-md border border-zinc-800 bg-zinc-900/40 px-4 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <VerdictBadge verdict={r.verdict} />
                <code className="font-mono text-xs text-zinc-200">
                  {r.lib}/{r.srcpf}/{r.mbr} · {r.test_name}
                </code>
                <ActionLabel action={r.developer_action} />
                <span className="ml-auto font-mono text-[11px] text-zinc-600">
                  {r.received_at ? new Date(r.received_at).toLocaleTimeString() : ''}
                </span>
              </div>
              <ConfidenceBar value={r.confidence} />
              <p className="text-sm text-zinc-400">{r.rationale}</p>
              {r.proposed_patch && (
                <pre className="mt-1 overflow-x-auto rounded border border-zinc-800 bg-zinc-950 p-2 font-mono text-[11px] text-zinc-300">
                  {r.proposed_patch}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </StageShell>
  )
}
