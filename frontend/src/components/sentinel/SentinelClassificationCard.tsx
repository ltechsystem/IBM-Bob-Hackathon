/**
 * src/components/sentinel/SentinelClassificationCard.tsx
 *
 * Displays a single Bob classification result with Accept / Reject / Flag
 * action buttons that POST back to the API via /api/review-action.
 */
import { useState } from 'react'
import type { ClassificationResult, ReviewAction } from '../../api/sentinel'
import { postReviewAction } from '../../api/sentinel'

const VERDICT_STYLE: Record<string, string> = {
  STALE_TEST: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  REGRESSION: 'border-red-500/40 bg-red-500/10 text-red-300',
  UNCERTAIN:  'border-zinc-500/40 bg-zinc-500/10 text-zinc-300',
}

const ACTION_STYLE: Record<string, string> = {
  UPDATE_TEST: 'text-amber-400',
  FIX_CODE:    'text-red-400',
  ASK_HUMAN:   'text-zinc-400',
  ADD_TEST:    'text-sky-400',
  NO_ACTION:   'text-zinc-600',
}

interface Props {
  result: ClassificationResult
}

export default function SentinelClassificationCard({ result }: Props) {
  const [reviewState, setReviewState] = useState<ReviewAction | null>(null)
  const [error, setError] = useState<string | null>(null)

  const confidence = Math.round(result.confidence * 100)
  const verdictCls = VERDICT_STYLE[result.classification] ?? VERDICT_STYLE.UNCERTAIN
  const actionCls = ACTION_STYLE[result.recommended_action] ?? 'text-zinc-400'

  async function handleReview(action: ReviewAction) {
    setError(null)
    try {
      await postReviewAction(result.test_name, action)
      setReviewState(action)
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 font-mono">
      {/* Header row */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold uppercase ${verdictCls}`}>
          {result.classification.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-zinc-400">
          test: <code className="text-zinc-200">{result.test_name}</code>
        </span>
        <span className="ml-auto text-xs text-zinc-500">
          confidence:{' '}
          <span className={confidence >= 80 ? 'text-emerald-400' : confidence >= 60 ? 'text-amber-400' : 'text-red-400'}>
            {confidence}%
          </span>
        </span>
      </div>

      {/* Reason */}
      <p className="mb-3 text-xs leading-relaxed text-zinc-400">{result.reason}</p>

      {/* Recommended action */}
      <p className="mb-3 text-[11px] text-zinc-600">
        Recommended:{' '}
        <span className={`font-semibold ${actionCls}`}>
          {result.recommended_action.replace(/_/g, ' ')}
        </span>
      </p>

      {/* Proposed diff */}
      {result.proposed_diff && (
        <div className="mb-3 overflow-auto rounded border border-zinc-700 text-xs">
          <div className="bg-zinc-800 px-3 py-1 text-[10px] uppercase tracking-wider text-zinc-500">
            Proposed patch
          </div>
          <pre className="p-3 leading-relaxed text-zinc-300">
            {result.proposed_diff.split('\n').map((line, i) => (
              <div
                key={i}
                className={
                  line.startsWith('+') && !line.startsWith('+++')
                    ? 'text-emerald-400'
                    : line.startsWith('-') && !line.startsWith('---')
                    ? 'text-red-400'
                    : line.startsWith('@@')
                    ? 'text-sky-400'
                    : 'text-zinc-500'
                }
              >
                {line}
              </div>
            ))}
          </pre>
        </div>
      )}

      {/* Review buttons / outcome */}
      {reviewState ? (
        <p className="text-xs text-zinc-500">
          Marked as{' '}
          <span className={reviewState === 'ACCEPT' ? 'text-emerald-400' : reviewState === 'REJECT' ? 'text-red-400' : 'text-amber-400'}>
            {reviewState}
          </span>
        </p>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={() => handleReview('ACCEPT')}
            className="rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20"
          >
            Accept
          </button>
          <button
            onClick={() => handleReview('REJECT')}
            className="rounded border border-red-500/40 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
          >
            Reject
          </button>
          <button
            onClick={() => handleReview('FLAG')}
            className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-400 hover:bg-amber-500/20"
          >
            Flag for review
          </button>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  )
}
