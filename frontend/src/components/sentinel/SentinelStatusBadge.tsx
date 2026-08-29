/**
 * src/components/sentinel/SentinelStatusBadge.tsx
 *
 * Coloured badge for a SentinelEventType — mirrors the sentinel pipeline stage
 * colours used in the StageShell design language.
 */
import type { SentinelEventType } from '../../api/sentinel'

const STYLE: Record<SentinelEventType, string> = {
  WATCHER_STARTED:       'border-sky-500/40 bg-sky-500/10 text-sky-400',
  COMPILE_DETECTED:      'border-amber-500/40 bg-amber-500/10 text-amber-400',
  DIFF_READY:            'border-violet-500/40 bg-violet-500/10 text-violet-400',
  TESTS_RUNNING:         'border-sky-500/40 bg-sky-500/10 text-sky-400',
  TESTS_PASSED:          'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  TESTS_FAILED:          'border-red-500/40 bg-red-500/10 text-red-400',
  CLASSIFYING:           'border-amber-500/40 bg-amber-500/10 text-amber-400',
  CLASSIFICATION_READY:  'border-violet-500/40 bg-violet-500/10 text-violet-400',
  SNAPSHOT_UPDATED:      'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  WATCHER_ERROR:         'border-red-500/40 bg-red-500/10 text-red-400',
  WATCHER_STOPPED:       'border-zinc-500/40 bg-zinc-500/10 text-zinc-400',
}

interface Props { type: SentinelEventType }

export default function SentinelStatusBadge({ type }: Props) {
  const cls = STYLE[type] ?? 'border-zinc-500/40 bg-zinc-500/10 text-zinc-400'
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${cls}`}>
      {type.replace(/_/g, ' ')}
    </span>
  )
}
