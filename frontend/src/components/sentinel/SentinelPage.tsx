/**
 * src/components/sentinel/SentinelPage.tsx
 *
 * Live Sentinel pipeline view.
 *
 * Layout
 * ------
 *  ┌── Sentinel Watcher ─────────────────────────────────────┐
 *  │  member/lib/srcpf config line                           │
 *  └─────────────────────────────────────────────────────────┘
 *
 *  ┌── Event Feed (SSE / REST) ──────────────────────────────┐
 *  │  Scrolling timeline of WATCHER_STARTED → … events      │
 *  └─────────────────────────────────────────────────────────┘
 *
 *  ┌── Diff Viewer ──────────────────────────────────────────┐
 *  │  Most recent unified diff (shown when DIFF_READY)       │
 *  └─────────────────────────────────────────────────────────┘
 *
 *  ┌── Test Results ─────────────────────────────────────────┐
 *  │  Pass/fail summary from last TESTS_PASSED/TESTS_FAILED  │
 *  └─────────────────────────────────────────────────────────┘
 *
 *  ┌── Classifications ──────────────────────────────────────┐
 *  │  SentinelClassificationCard for each Bob result         │
 *  └─────────────────────────────────────────────────────────┘
 *
 * Data
 * ----
 * On mount:
 *   1. GET /api/sentinel/events   → pre-populate from history (REST fallback)
 *   2. GET /api/results           → pre-populate classifications
 *   3. Open EventSource /api/sentinel/stream → live updates
 *
 * When the API is unreachable (frontend absent / watcher running standalone),
 * sentinel/watcher.py falls back to CLI output — this page simply shows
 * "Waiting for connection…" with a reconnect button.
 */

import { useEffect, useRef, useState } from 'react'
import type { ClassificationResult, SentinelEvent } from '../../api/sentinel'
import {
  fetchClassificationResults,
  fetchSentinelEvents,
  subscribeSentinelStream,
} from '../../api/sentinel'
import SentinelClassificationCard from './SentinelClassificationCard'
import SentinelStatusBadge from './SentinelStatusBadge'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString()
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConnectionStatus({ connected, onRetry }: { connected: boolean; onRetry: () => void }) {
  return (
    <div className={`flex items-center gap-2 rounded border px-3 py-2 text-xs font-mono ${
      connected
        ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
        : 'border-red-500/30 bg-red-500/10 text-red-400'
    }`}>
      <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
      {connected ? 'Connected — live events streaming' : 'API unreachable — CLI mode active'}
      {!connected && (
        <button
          onClick={onRetry}
          className="ml-2 rounded border border-red-500/40 px-2 py-0.5 hover:bg-red-500/20"
        >
          Retry
        </button>
      )}
    </div>
  )
}

interface EventRowProps { event: SentinelEvent }

function EventRow({ event }: EventRowProps) {
  return (
    <li className="flex flex-wrap items-start gap-3 border-b border-zinc-800 py-2 text-xs last:border-none">
      <span className="shrink-0 text-zinc-600">{formatTime(event.timestamp)}</span>
      <SentinelStatusBadge type={event.event_type} />
      <span className="text-zinc-300">
        <code className="text-amber-400">{event.member}</code>
        {event.lib && <span className="text-zinc-600"> · {event.lib}/{event.srcpf}</span>}
        {event.message && <span className="ml-1 text-zinc-500">{event.message}</span>}
      </span>
      {event.tests_run != null && (
        <span className="ml-auto shrink-0 text-zinc-500">
          {event.tests_run - (event.tests_failed ?? 0)}/{event.tests_run} passed
        </span>
      )}
    </li>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function SentinelPage() {
  const [events, setEvents] = useState<SentinelEvent[]>([])
  const [classifications, setClassifications] = useState<ClassificationResult[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const feedRef = useRef<HTMLUListElement>(null)

  // Latest diff from the event feed
  const latestDiff = [...events].reverse().find((e) => e.diff)?.diff ?? null

  // Latest test summary
  const latestTestEvent = [...events].reverse().find(
    (e) => e.event_type === 'TESTS_PASSED' || e.event_type === 'TESTS_FAILED',
  )

  function connect() {
    // Fetch history (REST)
    fetchSentinelEvents()
      .then(setEvents)
      .catch(() => {/* API down — no history */})

    fetchClassificationResults()
      .then(setClassifications)
      .catch(() => {/* API down — no classifications */})

    // Open SSE stream
    if (esRef.current) {
      esRef.current.close()
    }
    const es = subscribeSentinelStream(
      (event) => {
        setConnected(true)
        setEvents((prev) => {
          // De-duplicate by timestamp + member + type
          const key = `${event.timestamp}|${event.member}|${event.event_type}`
          if (prev.some((e) => `${e.timestamp}|${e.member}|${e.event_type}` === key)) return prev
          return [...prev, event]
        })
        // If it's a classification event, refresh the classifications list
        if (event.event_type === 'CLASSIFICATION_READY') {
          fetchClassificationResults()
            .then(setClassifications)
            .catch(() => {})
        }
      },
      () => setConnected(false),
    )
    es.onopen = () => setConnected(true)
    esRef.current = es
  }

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll event feed on new events
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
  }, [events])

  return (
    <div className="flex flex-col gap-6">
      {/* Connection status */}
      <ConnectionStatus connected={connected} onRetry={connect} />

      {/* Event feed */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-950/60">
        <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-3">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600">
              stage 1 · sentinel watcher
            </p>
            <h2 className="mt-1 font-mono text-lg font-bold text-zinc-100">Event Feed</h2>
            <p className="mt-1 text-sm text-zinc-500">
              Compile → diff → test → classify pipeline events from IBM i
            </p>
          </div>
          <span className="font-mono text-xs text-zinc-600">{events.length} event{events.length !== 1 ? 's' : ''}</span>
        </div>
        {events.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-zinc-600">
            Waiting for sentinel events…{' '}
            <span className="text-zinc-700">
              Run <code className="text-zinc-500">python -m sentinel.watcher --lib MYLIB --srcpf QRPGLESRC --mbr ORDCALC</code> to start watching.
            </span>
          </p>
        ) : (
          <ul ref={feedRef} className="max-h-72 overflow-y-auto px-5">
            {events.map((e, i) => (
              <EventRow key={i} event={e} />
            ))}
          </ul>
        )}
      </section>

      {/* Diff viewer */}
      {latestDiff && (
        <section className="rounded-lg border border-zinc-800 bg-zinc-950/60">
          <div className="border-b border-zinc-800 px-5 py-3">
            <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600">
              stage 2 · diff engine
            </p>
            <h2 className="mt-1 font-mono text-lg font-bold text-zinc-100">Latest Source Diff</h2>
          </div>
          <div className="overflow-auto p-4">
            <pre className="text-xs leading-relaxed">
              {latestDiff.split('\n').map((line, i) => (
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
        </section>
      )}

      {/* Test results summary */}
      {latestTestEvent && (
        <section className="rounded-lg border border-zinc-800 bg-zinc-950/60">
          <div className="border-b border-zinc-800 px-5 py-3">
            <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600">
              stage 3 · test runner
            </p>
            <h2 className="mt-1 font-mono text-lg font-bold text-zinc-100">Test Results</h2>
          </div>
          <div className="flex items-center gap-4 px-5 py-4 text-sm font-mono">
            <SentinelStatusBadge type={latestTestEvent.event_type} />
            <span className="text-zinc-300">{latestTestEvent.message}</span>
            {latestTestEvent.tests_run != null && (
              <span className="ml-auto text-zinc-500">
                <span className="text-emerald-400">
                  {latestTestEvent.tests_run - (latestTestEvent.tests_failed ?? 0)} passed
                </span>
                {(latestTestEvent.tests_failed ?? 0) > 0 && (
                  <span className="ml-2 text-red-400">{latestTestEvent.tests_failed} failed</span>
                )}
                <span className="ml-2 text-zinc-600">/ {latestTestEvent.tests_run} total</span>
              </span>
            )}
          </div>
        </section>
      )}

      {/* Classifications from Bob */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-950/60">
        <div className="border-b border-zinc-800 px-5 py-3">
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-600">
            stage 4 · bob classifier
          </p>
          <h2 className="mt-1 font-mono text-lg font-bold text-zinc-100">Bob Classifications</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Accept, reject, or flag each proposed test change
          </p>
        </div>
        {classifications.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-zinc-600">
            No classifications yet — classifications appear here when Bob finishes reasoning about a test failure.
          </p>
        ) : (
          <div className="flex flex-col gap-3 p-5">
            {classifications.map((c) => (
              <SentinelClassificationCard key={c.test_name} result={c} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
